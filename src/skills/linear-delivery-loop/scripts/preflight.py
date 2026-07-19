"""Mutation-free, least-privilege preflight with strict read-only probe evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.base_runtime import load_base_runtime
    from scripts.contracts import CONTRACT_VERSION, validate_contract
else:
    from .base_runtime import load_base_runtime
    from .contracts import CONTRACT_VERSION, validate_contract


PREFLIGHT_VERSION = "1.0"
PROBE_RESULT_VERSION = "1.0"
ENGINE_PROBE_ADAPTER_ID = "luchdom.supervisor.read-only"
ENGINE_PROBE_FIXED_ARG = "--engine-read-only-probe"
ENGINE_EXTERNAL_HOSTS = {
    "remote": "github.com",
    "linear": "api.linear.app",
    "ntfy": "ntfy.sh",
}
CORE_ENVIRONMENT_NAMES = frozenset(
    {
        "COMSPEC",
        "LOCALAPPDATA",
        "PATH",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "WINDIR",
        "LUCHDOM_DELIVERY_STATE_HOME",
    }
)
READ_ONLY_GIT_ARGV = frozenset(
    {
        ("rev-parse", "--show-toplevel"),
        ("rev-parse", "--git-common-dir"),
        ("rev-parse", "HEAD"),
        ("branch", "--show-current"),
        ("status", "--porcelain=v1", "--untracked-files=all"),
        ("remote", "get-url", "origin"),
    }
)
READ_ONLY_GH_ARGV = frozenset(
    {
        ("auth", "status"),
        ("repo", "view", "--json", "nameWithOwner"),
        ("pr", "view", "--json", "number,state,headRefOid"),
    }
)
FORBIDDEN_COMMAND_TOKENS = frozenset(
    {
        "--admin",
        "--force",
        "--hard",
        "--mirror",
        "--no-verify",
        "--set-upstream",
        "--update-refs",
        "-c",
        "-command",
        "-e",
        "-encodedcommand",
        "--eval",
        "branch-protection",
        "checks",
        "merge",
        "push",
        "reset",
        "ruleset",
        "settings",
    }
)
PROBE_KINDS = frozenset({"git", "gh", "remote", "linear", "ntfy", "loopback"})
EXTERNAL_PROBE_KINDS = frozenset({"remote", "linear", "ntfy"})
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
ENVIRONMENT_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,126}$")
BASELINE_SECRET_NAME_PATTERN = re.compile(
    r"(?:^|_)(?:API_?KEY|AUTH|BEARER|CREDENTIAL|KEY|NONCE|PASSWORD|PRIVATE|SECRET|TOKEN)(?:_|$)",
    re.IGNORECASE,
)
ENGINE_ALLOWED_SECRET_NAMES = frozenset({"LINEAR_API_KEY", "NTFY_TOKEN"})


class PreflightError(RuntimeError):
    """A redaction-safe preflight denial."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"preflight-denied:{code}")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def probe_request_hash(config: Mapping[str, Any]) -> str:
    """Bind fixture/live read-only evidence to the exact permission request."""

    request = {
        "schemaVersion": config.get("schemaVersion"),
        "repositoryKey": config.get("repositoryKey"),
        "baseBranch": config.get("baseBranch"),
        "commandPolicy": config.get("commandPolicy"),
        "networkPolicy": config.get("networkPolicy"),
        "probeAdapter": config.get("probeAdapter"),
        "scheduledPolicy": config.get("scheduledPolicy"),
    }
    return "sha256:" + hashlib.sha256(_canonical_json(request)).hexdigest()


def engine_probe_script_sha256() -> str:
    """Identify the installed engine-owned adapter bytes used for this launch."""

    return "sha256:" + hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()


def _normalized(path: str | Path) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path)))).replace("\\", "/")


def _parse_timestamp(value: Any) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PreflightError("probe-timestamp-invalid")
    try:
        observed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PreflightError("probe-timestamp-invalid") from exc
    if observed.tzinfo is None:
        raise PreflightError("probe-timestamp-invalid")
    return observed.astimezone(dt.timezone.utc)


def _validate_executable(value: Any, *, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\x00" in value
        or "\r" in value
        or "\n" in value
        or value.strip() != value
    ):
        raise PreflightError(code)
    return value


def _validate_argv_matrix(
    values: Any,
    allowed: frozenset[tuple[str, ...]],
    *,
    code: str,
) -> set[tuple[str, ...]]:
    if not isinstance(values, list) or not values:
        raise PreflightError(code)
    observed: set[tuple[str, ...]] = set()
    for argv in values:
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            raise PreflightError(code)
        command = tuple(argv)
        if command not in allowed or command in observed:
            raise PreflightError(code)
        if any(item.casefold() in FORBIDDEN_COMMAND_TOKENS for item in command):
            raise PreflightError(code)
        observed.add(command)
    return observed


def _validate_host(value: Any, allowed: set[str], *, code: str) -> str:
    if (
        not isinstance(value, str)
        or value != value.casefold()
        or value not in allowed
        or "://" in value
        or "/" in value
        or "*" in value
    ):
        raise PreflightError(code)
    return value


def _validate_external_address(value: Any) -> None:
    if not isinstance(value, str):
        raise PreflightError("probe-address-invalid")
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise PreflightError("probe-address-invalid") from exc
    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise PreflightError("probe-address-not-public")


class PreflightValidator:
    """Validate the exact local permission profile before authority is claimed."""

    def __init__(
        self,
        repository: str | Path,
        *,
        repository_key: str,
        state_home_override: str | Path | None = None,
        environment: Mapping[str, str] | None = None,
        now: Callable[[], dt.datetime] | None = None,
    ) -> None:
        self.runtime = load_base_runtime()
        self.environment = dict(os.environ if environment is None else environment)
        self.manager = self.runtime.WorkflowManager(
            repository,
            repository_key=repository_key,
            state_home_override=state_home_override,
            environment=self.environment,
        )
        self.repository = Path(self.manager.identity.repository_root)
        self.state_root = self.manager.home.repository
        self.issue_root = self.manager.state_paths.directory(
            self.state_root / "worktrees", create=True
        )
        self.gate_root = self.manager.state_paths.directory(
            self.state_root / "validation-worktrees", create=True
        )
        self.now = now or (lambda: dt.datetime.now(dt.timezone.utc))

    def validate(self, config: Mapping[str, Any], probe_result: Mapping[str, Any]) -> dict[str, Any]:
        git_argv, gh_argv = self.validate_probe_request(config)
        self._validate_probe(config, probe_result, git_argv=git_argv, gh_argv=gh_argv)

        # All semantic denials happen before the only permitted write probes.
        sentinel_evidence = self._probe_authoritative_writes(config)
        return {
            "schemaVersion": PREFLIGHT_VERSION,
            "status": "pass",
            "repositoryId": self.manager.identity.repository_id,
            "repositoryKey": self.manager.repository_key,
            "probeRequestHash": probe_request_hash(config),
            "childEnvironmentNames": sorted(self.build_child_environment(config)),
            "sentinels": sentinel_evidence,
        }

    def validate_probe_request(
        self, config: Mapping[str, Any]
    ) -> tuple[set[tuple[str, ...]], set[tuple[str, ...]]]:
        """Validate every config-controlled launch input before executing an adapter."""

        try:
            validate_contract("project-config", dict(config))
        except Exception as exc:
            raise PreflightError("project-config-invalid") from exc
        # The contract walker validates values without treating the policy field
        # `forbiddenSecretNamePatterns` itself as secret-bearing evidence.
        self._validate_versions(config)
        self._validate_repository(config)
        git_argv, gh_argv = self._validate_commands(config)
        self._validate_network(config)
        self._validate_environment(config)
        return git_argv, gh_argv

    def build_child_environment(self, config: Mapping[str, Any]) -> dict[str, str]:
        """Return engine runtime names only; provider credentials never reach probes."""

        self._validate_environment(config)
        return {
            name: self.environment[name]
            for name in sorted(CORE_ENVIRONMENT_NAMES)
            if name in self.environment
        }

    def _validate_versions(self, config: Mapping[str, Any]) -> None:
        expected = {
            "schemaVersion": CONTRACT_VERSION,
            "engineVersion": CONTRACT_VERSION,
        }
        if any(config.get(name) != value for name, value in expected.items()):
            raise PreflightError("engine-or-config-version-mismatch")
        base = config.get("baseVersions")
        expected_base = {
            "basePackage": self.runtime.package_version,
            "identity": self.runtime.identity_version,
            "stateHome": self.runtime.state_home_version,
            "registry": self.runtime.registry_version,
            "workDescriptor": self.runtime.work_descriptor_version,
        }
        if base != expected_base:
            raise PreflightError("base-version-mismatch")
        adapter = config.get("probeAdapter", {})
        if adapter.get("adapterVersion") != PROBE_RESULT_VERSION:
            raise PreflightError("probe-adapter-version-mismatch")

    def _validate_repository(self, config: Mapping[str, Any]) -> None:
        if config.get("repositoryKey") != self.manager.repository_key:
            raise PreflightError("repository-key-mismatch")
        base_branch = config.get("baseBranch")
        if (
            not isinstance(base_branch, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", base_branch)
            or base_branch.startswith("-")
            or ".." in base_branch
            or "@{" in base_branch
        ):
            raise PreflightError("base-branch-invalid")
        roots = config.get("writableRoots")
        if not isinstance(roots, list):
            raise PreflightError("writable-roots-invalid")
        normalized = [_normalized(item) for item in roots]
        expected = {
            _normalized(self.state_root),
            _normalized(self.issue_root),
            _normalized(self.gate_root),
        }
        if len(normalized) != len(set(normalized)) or set(normalized) != expected:
            raise PreflightError("writable-roots-not-exact")

    def _validate_commands(
        self, config: Mapping[str, Any]
    ) -> tuple[set[tuple[str, ...]], set[tuple[str, ...]]]:
        policy = config.get("commandPolicy", {})
        expected_commands = {
            "pythonExecutable": [os.fspath(Path(sys.executable).resolve())],
            "powerShellExecutable": [
                path
                for path in (shutil.which("powershell"), shutil.which("pwsh"))
                if path
            ],
            "gitExecutable": [shutil.which("git")],
            "ghExecutable": [shutil.which("gh")],
        }
        for field in (
            "pythonExecutable",
            "powerShellExecutable",
            "gitExecutable",
            "ghExecutable",
        ):
            executable = Path(
                _validate_executable(policy.get(field), code="command-executable-invalid")
            )
            trusted = {
                _normalized(path)
                for path in expected_commands[field]
                if isinstance(path, str)
            }
            if (
                not executable.is_absolute()
                or not executable.is_file()
                or _normalized(executable) not in trusted
            ):
                raise PreflightError("command-executable-missing")
        wrapper = Path(_validate_executable(policy.get("workerWrapper"), code="wrapper-invalid"))
        expected_wrapper = Path(__file__).resolve().with_name("agent-worker-engine.ps1")
        if _normalized(wrapper) != _normalized(expected_wrapper) or not wrapper.is_file():
            raise PreflightError("wrapper-missing-or-drifted")
        git_argv = _validate_argv_matrix(
            policy.get("allowedGitArgv"), READ_ONLY_GIT_ARGV, code="git-argv-not-read-only"
        )
        gh_argv = _validate_argv_matrix(
            policy.get("allowedGhArgv"), READ_ONLY_GH_ARGV, code="gh-argv-not-read-only"
        )
        adapter = config.get("probeAdapter", {})
        probe_executable = Path(
            _validate_executable(adapter.get("executable"), code="probe-executable-invalid")
        )
        expected_executable = Path(sys.executable).resolve()
        expected_argv = [os.fspath(Path(__file__).resolve()), ENGINE_PROBE_FIXED_ARG]
        if (
            adapter.get("adapterId") != ENGINE_PROBE_ADAPTER_ID
            or adapter.get("adapterVersion") != PROBE_RESULT_VERSION
            or not probe_executable.is_absolute()
            or not probe_executable.is_file()
            or _normalized(probe_executable) != _normalized(expected_executable)
            or adapter.get("fixedArgv") != expected_argv
        ):
            raise PreflightError("probe-adapter-not-engine-owned")
        aggregate = config.get("aggregateCommand")
        expected_aggregate = self.repository / "scripts" / "validate.py"
        if (
            not isinstance(aggregate, list)
            or len(aggregate) != 2
            or aggregate[0] != policy.get("pythonExecutable")
            or _normalized(self.repository / aggregate[1]) != _normalized(expected_aggregate)
            or not expected_aggregate.is_file()
        ):
            raise PreflightError("aggregate-command-invalid")
        scheduled = config.get("scheduledPolicy", {})
        if scheduled != {
            "sandboxMode": "workspace-write",
            "networkAccess": True,
            "approvalPolicy": "never",
            "profileComposition": "none",
        }:
            raise PreflightError("scheduled-policy-not-least-privilege")
        forbidden_profile_text = json.dumps(scheduled, sort_keys=True).casefold()
        if any(token in forbidden_profile_text for token in ("danger", "full-access", "beta")):
            raise PreflightError("scheduled-policy-forbidden-profile")
        return git_argv, gh_argv

    def _validate_network(self, config: Mapping[str, Any]) -> None:
        policy = config.get("networkPolicy", {})
        hosts = policy.get("allowedHosts")
        if (
            not isinstance(hosts, list)
            or not hosts
            or len(hosts) != len(set(hosts))
            or any(
                not isinstance(host, str)
                or host != host.casefold()
                or not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", host)
                or "://" in host
                or "*" in host
                or ".." in host
                or host == "localhost"
                or host.endswith(".local")
                for host in hosts
            )
        ):
            raise PreflightError("host-allowlist-invalid")
        for host in hosts:
            try:
                ipaddress.ip_address(host)
            except ValueError:
                continue
            raise PreflightError("host-allowlist-must-use-dns-names")
        if set(hosts) != set(ENGINE_EXTERNAL_HOSTS.values()):
            raise PreflightError("host-allowlist-not-engine-exact")
        loopback_host = policy.get("loopbackHost")
        try:
            loopback = ipaddress.ip_address(loopback_host)
        except (TypeError, ValueError) as exc:
            raise PreflightError("loopback-host-invalid") from exc
        if not loopback.is_loopback or loopback_host not in {"127.0.0.1", "::1"}:
            raise PreflightError("loopback-host-invalid")
        ports = policy.get("loopbackPorts")
        if (
            not isinstance(ports, list)
            or not ports
            or len(ports) != len(set(ports))
            or any(not isinstance(port, int) or isinstance(port, bool) or port < 1024 or port > 65535 for port in ports)
        ):
            raise PreflightError("loopback-ports-invalid")

    def _validate_environment(self, config: Mapping[str, Any]) -> set[str]:
        policy = config.get("environmentPolicy", {})
        required = policy.get("requiredVariableNames")
        allowed = policy.get("allowedInheritedVariableNames")
        patterns = policy.get("forbiddenSecretNamePatterns")
        if not all(isinstance(values, list) for values in (required, allowed, patterns)):
            raise PreflightError("environment-policy-invalid")
        configured = set(required) | set(allowed)
        if any(
            BASELINE_SECRET_NAME_PATTERN.search(name)
            and name not in ENGINE_ALLOWED_SECRET_NAMES
            for name in configured
            if isinstance(name, str)
        ):
            raise PreflightError("forbidden-configured-secret")
        declared = configured | set(CORE_ENVIRONMENT_NAMES)
        if any(not ENVIRONMENT_NAME_PATTERN.fullmatch(name) for name in declared):
            raise PreflightError("environment-name-invalid")
        if any(name not in self.environment or not self.environment[name] for name in required):
            raise PreflightError("required-environment-missing")
        try:
            compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        except (TypeError, re.error) as exc:
            raise PreflightError("forbidden-environment-pattern-invalid") from exc
        for name in self.environment:
            if name not in declared and any(pattern.search(name) for pattern in compiled):
                raise PreflightError("forbidden-inherited-secret")
        return {name for name in declared if name in self.environment}

    def _validate_probe(
        self,
        config: Mapping[str, Any],
        probe: Mapping[str, Any],
        *,
        git_argv: set[tuple[str, ...]],
        gh_argv: set[tuple[str, ...]],
    ) -> None:
        if not isinstance(probe, Mapping) or self.runtime.redact_value(dict(probe)) != dict(probe):
            raise PreflightError("probe-secret-bearing")
        if set(probe) != {
            "schemaVersion",
            "adapterId",
            "adapterVersion",
            "adapterSha256",
            "requestHash",
            "observedAtUtc",
            "checks",
        }:
            raise PreflightError("probe-shape-invalid")
        adapter = config["probeAdapter"]
        if (
            probe.get("schemaVersion") != PROBE_RESULT_VERSION
            or probe.get("adapterId") != adapter.get("adapterId")
            or probe.get("adapterVersion") != adapter.get("adapterVersion")
            or probe.get("adapterSha256") != engine_probe_script_sha256()
            or probe.get("requestHash") != probe_request_hash(config)
            or not SHA256_PATTERN.fullmatch(str(probe.get("requestHash")))
        ):
            raise PreflightError("probe-binding-invalid")
        observed = _parse_timestamp(probe.get("observedAtUtc"))
        now = self.now().astimezone(dt.timezone.utc)
        age = (now - observed).total_seconds()
        if age < -5 or age > 300:
            raise PreflightError("probe-stale-or-future")
        checks = probe.get("checks")
        if not isinstance(checks, list) or len(checks) != len(PROBE_KINDS):
            raise PreflightError("probe-checks-incomplete")
        by_kind: dict[str, Mapping[str, Any]] = {}
        for check in checks:
            if not isinstance(check, Mapping) or check.get("kind") in by_kind:
                raise PreflightError("probe-check-duplicate-or-invalid")
            by_kind[str(check.get("kind"))] = check
        if set(by_kind) != set(PROBE_KINDS):
            raise PreflightError("probe-checks-incomplete")
        allowed_hosts = set(config["networkPolicy"]["allowedHosts"])
        used_external_hosts: set[str] = set()
        for kind, check in by_kind.items():
            if check.get("status") != "pass" or check.get("readOnly") is not True:
                raise PreflightError("probe-check-failed-or-mutating")
            if kind in {"git", "gh"}:
                if set(check) != {"kind", "status", "readOnly", "argv"}:
                    raise PreflightError("command-probe-shape-invalid")
                argv = check.get("argv")
                allowed = git_argv if kind == "git" else gh_argv
                if not isinstance(argv, list) or tuple(argv) not in allowed:
                    raise PreflightError("command-probe-argv-drift")
            elif kind in EXTERNAL_PROBE_KINDS:
                if set(check) != {
                    "kind",
                    "status",
                    "readOnly",
                    "host",
                    "resolvedAddresses",
                    "redirectHosts",
                }:
                    raise PreflightError("external-probe-shape-invalid")
                used_external_hosts.add(
                    _validate_host(check.get("host"), allowed_hosts, code="probe-host-not-allowed")
                )
                redirects = check.get("redirectHosts")
                addresses = check.get("resolvedAddresses")
                if (
                    not isinstance(redirects, list)
                    or len(redirects) != len(set(redirects))
                    or not isinstance(addresses, list)
                    or len(addresses) != len(set(addresses))
                    or not addresses
                ):
                    raise PreflightError("probe-network-evidence-invalid")
                for host in redirects:
                    used_external_hosts.add(
                        _validate_host(host, allowed_hosts, code="probe-redirect-not-allowed")
                    )
                for address in addresses:
                    _validate_external_address(address)
            else:
                if set(check) != {
                    "kind",
                    "status",
                    "readOnly",
                    "host",
                    "port",
                    "resolvedAddress",
                }:
                    raise PreflightError("loopback-probe-shape-invalid")
                policy = config["networkPolicy"]
                if (
                    check.get("host") != policy["loopbackHost"]
                    or check.get("port") not in policy["loopbackPorts"]
                    or check.get("resolvedAddress") != policy["loopbackHost"]
                ):
                    raise PreflightError("loopback-probe-not-exact")
        if used_external_hosts != allowed_hosts:
            raise PreflightError("probe-host-allowlist-not-exact")

    def _probe_authoritative_writes(self, config: Mapping[str, Any]) -> list[str]:
        evidence: list[str] = []
        try:
            with self.manager.registry.mutex():
                evidence.append("base-mutex")
            for label, directory in (("state-root", self.state_root), ("worktree-root", self.issue_root)):
                token = f"preflight-{uuid.uuid4()}.tmp"
                path = directory / token
                wrote = False
                try:
                    self.manager.state_paths.write_bytes(path, token.encode("ascii"))
                    wrote = True
                    if self.manager.state_paths.read_bytes(path) != token.encode("ascii"):
                        raise PreflightError("sentinel-readback-failed")
                finally:
                    if wrote or os.path.lexists(path):
                        try:
                            self.manager.state_paths.unlink(path)
                        except Exception as exc:
                            raise PreflightError("sentinel-cleanup-failed") from exc
                if os.path.lexists(path):
                    raise PreflightError("sentinel-cleanup-failed")
                evidence.append(label)
        except PreflightError:
            raise
        except Exception as exc:
            raise PreflightError("authoritative-write-probe-failed") from exc
        return evidence


def _probe_command(executable: str, argv: list[str], *, cwd: str) -> bool:
    try:
        return subprocess.run(
            [executable, *argv],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            shell=False,
            timeout=30,
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _resolved_public_addresses(host: str) -> list[str]:
    try:
        return sorted(
            {
                item[4][0]
                for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            }
        )
    except OSError:
        return []


def run_engine_probe(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Run the one installed, fixed-shape, read-only connectivity adapter."""

    config = payload.get("config")
    repository = payload.get("repositoryRoot")
    if not isinstance(config, Mapping) or not isinstance(repository, str):
        raise PreflightError("engine-probe-input-invalid")
    policy = config["commandPolicy"]
    git_argv = list(config["commandPolicy"]["allowedGitArgv"][0])
    gh_argv = list(config["commandPolicy"]["allowedGhArgv"][0])
    checks: list[dict[str, Any]] = [
        {
            "kind": "git",
            "status": "pass"
            if _probe_command(policy["gitExecutable"], git_argv, cwd=repository)
            else "failed",
            "readOnly": True,
            "argv": git_argv,
        },
        {
            "kind": "gh",
            "status": "pass"
            if _probe_command(policy["ghExecutable"], gh_argv, cwd=repository)
            else "failed",
            "readOnly": True,
            "argv": gh_argv,
        },
    ]
    for kind, host in ENGINE_EXTERNAL_HOSTS.items():
        addresses = _resolved_public_addresses(host)
        checks.append(
            {
                "kind": kind,
                "status": "pass" if addresses else "failed",
                "readOnly": True,
                "host": host,
                "resolvedAddresses": addresses,
                "redirectHosts": [],
            }
        )
    loopback_host = config["networkPolicy"]["loopbackHost"]
    loopback_port = config["networkPolicy"]["loopbackPorts"][0]
    try:
        connection = socket.create_connection((loopback_host, loopback_port), timeout=3)
        connection.close()
        loopback_status = "pass"
    except OSError:
        loopback_status = "failed"
    checks.append(
        {
            "kind": "loopback",
            "status": loopback_status,
            "readOnly": True,
            "host": loopback_host,
            "port": loopback_port,
            "resolvedAddress": loopback_host,
        }
    )
    return {
        "schemaVersion": PROBE_RESULT_VERSION,
        "adapterId": ENGINE_PROBE_ADAPTER_ID,
        "adapterVersion": PROBE_RESULT_VERSION,
        "adapterSha256": engine_probe_script_sha256(),
        "requestHash": probe_request_hash(config),
        "observedAtUtc": dt.datetime.now(dt.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "checks": checks,
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="linear-delivery-preflight")
    parser.add_argument(ENGINE_PROBE_FIXED_ARG, action="store_true")
    args = parser.parse_args(argv)
    if not args.engine_read_only_probe:
        return 2
    try:
        payload = json.loads(sys.stdin.read())
        print(json.dumps(run_engine_probe(payload), sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({"status": "failed", "error": "engine probe failed closed"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
