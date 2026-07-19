from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "src" / "skills" / "linear-delivery-loop" / "scripts"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "preflight" / "passing-probe.template.json"
PACKAGE = "_linear_delivery_loop_preflight_tests"
if PACKAGE not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        PACKAGE,
        SCRIPTS / "__init__.py",
        submodule_search_locations=[os.fspath(SCRIPTS)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE] = module
    spec.loader.exec_module(module)

preflight = __import__(f"{PACKAGE}.preflight", fromlist=["PreflightValidator"])
cli = __import__(f"{PACKAGE}.cli", fromlist=["run_request"])
PreflightValidator = preflight.PreflightValidator
PreflightError = preflight.PreflightError


def git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "--no-optional-locks", "-C", os.fspath(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=False,
    )


def state_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


class PreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="supervisor-preflight-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()
        git(self.repository, "init", "--initial-branch=main")
        git(self.repository, "config", "user.name", "Test User")
        git(self.repository, "config", "user.email", "test@example.invalid")
        (self.repository / "README.md").write_text("base\n", encoding="utf-8")
        (self.repository / "scripts").mkdir()
        (self.repository / "scripts" / "validate.py").write_text(
            "raise SystemExit(0)\n", encoding="utf-8"
        )
        git(self.repository, "add", "README.md", "scripts/validate.py")
        git(self.repository, "commit", "-m", "initial")
        self.state = self.root / "state"
        self.now = dt.datetime(2026, 7, 18, 12, 0, tzinfo=dt.timezone.utc)
        self.environment = {
            "PATH": os.environ.get("PATH", os.fspath(Path(sys.executable).parent)),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "LOCALAPPDATA": os.fspath(self.root / "local-app-data"),
            "LINEAR_API_KEY": "linear-fixture-value",
            "NTFY_TOKEN": "ntfy-fixture-value",
            "USERNAME": "fixture-user",
        }
        self.validator = PreflightValidator(
            self.repository,
            repository_key="test-repository",
            state_home_override=self.state,
            environment=self.environment,
            now=lambda: self.now,
        )
        executable = os.path.normpath(os.path.abspath(sys.executable))
        wrapper = os.path.normpath(os.path.abspath(SCRIPTS / "agent-worker-engine.ps1"))
        self.config = {
            "schemaVersion": "1.0",
            "engineVersion": "1.0",
            "baseVersions": {
                "basePackage": "1.0",
                "identity": "1.0",
                "stateHome": "2.0",
                "registry": "1.0",
                "workDescriptor": "2.0",
            },
            "repositoryKey": "test-repository",
            "baseBranch": "main",
            "aggregateCommand": [executable, "scripts/validate.py"],
            "writableRoots": [
                os.path.normpath(os.path.abspath(self.validator.state_root)),
                os.path.normpath(os.path.abspath(self.validator.issue_root)),
                os.path.normpath(os.path.abspath(self.validator.gate_root)),
            ],
            "commandPolicy": {
                "pythonExecutable": executable,
                "powerShellExecutable": os.path.normpath(
                    os.path.abspath(shutil.which("powershell") or shutil.which("pwsh"))
                ),
                "gitExecutable": os.path.normpath(os.path.abspath(shutil.which("git"))),
                "ghExecutable": os.path.normpath(os.path.abspath(shutil.which("gh"))),
                "workerWrapper": wrapper,
                "allowedGitArgv": [["rev-parse", "--show-toplevel"]],
                "allowedGhArgv": [["repo", "view", "--json", "nameWithOwner"]],
            },
            "scheduledPolicy": {
                "sandboxMode": "workspace-write",
                "networkAccess": True,
                "approvalPolicy": "never",
                "profileComposition": "none",
            },
            "networkPolicy": {
                "allowedHosts": ["github.com", "api.linear.app", "ntfy.sh"],
                "loopbackHost": "127.0.0.1",
                "loopbackPorts": [8765],
            },
            "environmentPolicy": {
                "requiredVariableNames": ["LINEAR_API_KEY", "NTFY_TOKEN"],
                "allowedInheritedVariableNames": ["PATH", "SYSTEMROOT", "LOCALAPPDATA"],
                "forbiddenSecretNamePatterns": [
                    "^(AWS|AZURE|GCP|GOOGLE|VERCEL|POSTHOG|STRIPE|PRODUCTION)_"
                ],
            },
            "probeAdapter": {
                "adapterId": "luchdom.supervisor.read-only",
                "adapterVersion": "1.0",
                "executable": executable,
                "fixedArgv": [
                    os.fspath(SCRIPTS / "preflight.py"),
                    "--engine-read-only-probe",
                ],
            },
            "clockPolicy": {
                "leaseSeconds": 300,
                "reservationSeconds": 600,
                "maxForwardStepSeconds": 60,
            },
        }

    def passing_probe(self) -> dict:
        template = FIXTURE.read_text(encoding="utf-8")
        template = template.replace("{{OBSERVED_AT_UTC}}", "2026-07-18T12:00:00Z")
        template = template.replace("{{REQUEST_HASH}}", preflight.probe_request_hash(self.config))
        template = template.replace("{{ADAPTER_SHA256}}", preflight.engine_probe_script_sha256())
        return json.loads(template)

    def validate_with_pending_wrapper(self, validator, config: dict, probe: dict) -> dict:
        """S46-07 owns the wrapper; virtualize only that file during this isolated slice."""

        original = Path.is_file
        expected = os.path.normcase(
            os.path.realpath(os.path.abspath(SCRIPTS / "agent-worker-engine.ps1"))
        )

        def is_file(path: Path) -> bool:
            observed = os.path.normcase(os.path.realpath(os.path.abspath(path)))
            return observed == expected or original(path)

        with mock.patch.object(Path, "is_file", is_file):
            return validator.validate(config, probe)

    def assert_denied_without_secret(self, config: dict, probe: dict, secret: str = "") -> str:
        with self.assertRaises(PreflightError) as raised:
            self.validate_with_pending_wrapper(self.validator, config, probe)
        message = str(raised.exception)
        if secret:
            self.assertNotIn(secret, message)
        return message

    def test_exact_profile_passes_and_child_environment_is_minimized(self) -> None:
        result = self.validate_with_pending_wrapper(
            self.validator, self.config, self.passing_probe()
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["sentinels"], ["base-mutex", "state-root", "worktree-root"])
        self.assertNotIn("USERNAME", result["childEnvironmentNames"])
        child = self.validator.build_child_environment(self.config)
        self.assertNotIn("LINEAR_API_KEY", child)
        self.assertNotIn("NTFY_TOKEN", child)
        self.assertNotIn("USERNAME", child)
        self.assertFalse(any(self.validator.state_root.glob("preflight-*.tmp")))
        self.assertFalse(any(self.validator.issue_root.glob("preflight-*.tmp")))

    def test_policy_command_and_executable_drift_are_denied_before_sentinel(self) -> None:
        cases: list[tuple[str, callable]] = [
            (
                "full-access",
                lambda value: value["scheduledPolicy"].update(sandboxMode="danger-full-access"),
            ),
            (
                "profile-composition",
                lambda value: value["scheduledPolicy"].update(profileComposition="beta-profile"),
            ),
            (
                "git-force",
                lambda value: value["commandPolicy"].update(allowedGitArgv=[["push", "--force"]]),
            ),
            (
                "hosted-checks",
                lambda value: value["commandPolicy"].update(allowedGhArgv=[["pr", "checks"]]),
            ),
            (
                "aggregate-extra",
                lambda value: value.update(aggregateCommand=[sys.executable, "scripts/validate.py", "--extra"]),
            ),
            (
                "missing-executable",
                lambda value: value["commandPolicy"].update(
                    gitExecutable=os.path.normpath(os.path.abspath(self.root / "missing.exe"))
                ),
            ),
            (
                "repository-selected-executable",
                lambda value: value["commandPolicy"].update(
                    gitExecutable=os.path.normpath(
                        os.path.abspath(self.repository / "scripts" / "validate.py")
                    )
                ),
            ),
            (
                "wrong-wrapper",
                lambda value: value["commandPolicy"].update(workerWrapper=sys.executable),
            ),
        ]
        for name, mutate in cases:
            with self.subTest(name=name):
                config = copy.deepcopy(self.config)
                mutate(config)
                probe = self.passing_probe()
                before = state_snapshot(self.validator.state_root)
                self.assert_denied_without_secret(config, probe)
                self.assertEqual(state_snapshot(self.validator.state_root), before)

    def test_network_redirect_dns_and_loopback_are_independently_denied(self) -> None:
        cases = []
        redirect = self.passing_probe()
        redirect["checks"][2]["redirectHosts"] = ["evil.example"]
        cases.append(("redirect", redirect))
        private_dns = self.passing_probe()
        private_dns["checks"][3]["resolvedAddresses"] = ["192.168.1.10"]
        cases.append(("private-dns", private_dns))
        broad_loopback = self.passing_probe()
        broad_loopback["checks"][5]["host"] = "localhost"
        cases.append(("loopback-host", broad_loopback))
        wrong_port = self.passing_probe()
        wrong_port["checks"][5]["port"] = 8766
        cases.append(("loopback-port", wrong_port))
        for name, probe in cases:
            with self.subTest(name=name):
                self.assert_denied_without_secret(self.config, probe)

    def test_probe_must_be_fresh_bound_read_only_complete_and_secret_free(self) -> None:
        cases = []
        wrong_version = self.passing_probe()
        wrong_version["adapterVersion"] = "2.0"
        cases.append(("version", wrong_version, ""))
        wrong_hash = self.passing_probe()
        wrong_hash["requestHash"] = "sha256:" + "0" * 64
        cases.append(("hash", wrong_hash, ""))
        stale = self.passing_probe()
        stale["observedAtUtc"] = "2026-07-18T11:00:00Z"
        cases.append(("stale", stale, ""))
        failed = self.passing_probe()
        failed["checks"][0]["status"] = "ambiguous"
        cases.append(("ambiguous", failed, ""))
        mutating = self.passing_probe()
        mutating["checks"][1]["readOnly"] = False
        cases.append(("mutating", mutating, ""))
        incomplete = self.passing_probe()
        incomplete["checks"].pop()
        cases.append(("incomplete", incomplete, ""))
        drift = self.passing_probe()
        drift["checks"][0]["argv"] = ["status", "--short"]
        cases.append(("argv", drift, ""))
        secret = self.passing_probe()
        secret["diagnostic"] = "token=do-not-echo-this"
        cases.append(("secret", secret, "do-not-echo-this"))
        for name, probe, sentinel in cases:
            with self.subTest(name=name):
                self.assert_denied_without_secret(self.config, probe, sentinel)

    def test_missing_required_and_unrelated_provider_secrets_fail(self) -> None:
        missing_environment = dict(self.environment)
        missing_environment.pop("LINEAR_API_KEY")
        missing = PreflightValidator(
            self.repository,
            repository_key="test-repository",
            state_home_override=self.state,
            environment=missing_environment,
            now=lambda: self.now,
        )
        with self.assertRaisesRegex(PreflightError, "required-environment-missing"):
            self.validate_with_pending_wrapper(missing, self.config, self.passing_probe())

        polluted_environment = dict(self.environment, AWS_SECRET_ACCESS_KEY="aws-do-not-echo")
        polluted = PreflightValidator(
            self.repository,
            repository_key="test-repository",
            state_home_override=self.state,
            environment=polluted_environment,
            now=lambda: self.now,
        )
        with self.assertRaises(PreflightError) as raised:
            self.validate_with_pending_wrapper(polluted, self.config, self.passing_probe())
        self.assertIn("forbidden-inherited-secret", str(raised.exception))
        self.assertNotIn("aws-do-not-echo", str(raised.exception))

    def test_config_cannot_select_adapter_or_allow_unrelated_secret(self) -> None:
        secret = "aws-must-never-reach-child"
        malicious = copy.deepcopy(self.config)
        malicious["probeAdapter"]["executable"] = os.fspath(
            self.repository / "scripts" / "validate.py"
        )
        malicious["environmentPolicy"]["allowedInheritedVariableNames"].append(
            "AWS_SECRET_ACCESS_KEY"
        )
        validator = PreflightValidator(
            self.repository,
            repository_key="test-repository",
            state_home_override=self.state,
            environment=dict(self.environment, AWS_SECRET_ACCESS_KEY=secret),
            now=lambda: self.now,
        )
        with self.assertRaises(PreflightError) as raised, mock.patch.object(
            preflight.subprocess, "run"
        ) as launched:
            validator.validate_probe_request(malicious)
        launched.assert_not_called()
        self.assertNotIn(secret, str(raised.exception))

    def test_public_preflight_denies_malicious_adapter_before_launch(self) -> None:
        malicious = copy.deepcopy(self.config)
        malicious["probeAdapter"]["executable"] = os.fspath(
            self.repository / "scripts" / "validate.py"
        )
        malicious["environmentPolicy"]["allowedInheritedVariableNames"].append(
            "AWS_SECRET_ACCESS_KEY"
        )
        config_path = self.repository / "malicious-project-config.json"
        config_path.write_text(json.dumps(malicious), encoding="utf-8")
        request = {
            "schemaVersion": "1.0",
            "operation": "Preflight",
            "requestId": str(uuid.uuid4()),
            "repositoryKey": "test-repository",
            "repositoryRoot": os.fspath(self.repository),
            "stateHome": os.fspath(self.validator.state_root),
            "requestedAt": "2026-07-18T12:00:00Z",
            "configPath": os.fspath(config_path),
        }
        request_path = self.repository / "malicious-preflight.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        with self.assertRaises(PreflightError), mock.patch.object(
            cli, "_execute_probe"
        ) as launched:
            cli.run_request(request_path)
        launched.assert_not_called()

    def test_public_preflight_accepts_engine_owned_probe_result(self) -> None:
        config_path = self.repository / "project-config.json"
        config_path.write_text(json.dumps(self.config), encoding="utf-8")
        request = {
            "schemaVersion": "1.0",
            "operation": "Preflight",
            "requestId": str(uuid.uuid4()),
            "repositoryKey": "test-repository",
            "repositoryRoot": os.fspath(self.repository),
            "stateHome": os.fspath(self.validator.state_root),
            "requestedAt": "2026-07-18T12:00:00Z",
            "configPath": os.fspath(config_path),
        }
        request_path = self.repository / "preflight.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        probe = self.passing_probe()
        probe["observedAtUtc"] = (
            dt.datetime.now(tz=dt.timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        with mock.patch.dict(os.environ, self.environment, clear=True), mock.patch.object(
            cli, "_execute_probe", return_value=probe
        ) as launched:
            result = cli.run_request(request_path)
        self.assertEqual("pass", result["status"])
        launched.assert_called_once()

    def test_sentinel_cleanup_failure_is_redacted_and_fails_closed(self) -> None:
        secret = "sentinel-cleanup-secret"
        original = self.validator.manager.state_paths.unlink

        def fail_preflight(path: Path, *args, **kwargs):
            if Path(path).name.startswith("preflight-"):
                raise OSError(f"token={secret}")
            return original(path, *args, **kwargs)

        with mock.patch.object(self.validator.manager.state_paths, "unlink", side_effect=fail_preflight):
            message = self.assert_denied_without_secret(
                self.config, self.passing_probe(), secret
            )
        self.assertIn("sentinel-cleanup-failed", message)


if __name__ == "__main__":
    unittest.main()
