"""Focused tests for the autonomous loop's cross-run lease."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "skills" / "linear-delivery-loop" / "scripts" / "loop_lock.py"


def load_lock_module():
    spec = importlib.util.spec_from_file_location("linear_loop_lock", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load loop_lock.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


loop_lock = load_lock_module()


def write_config(repository: Path, *, repository_key: str = "saas") -> None:
    path = repository / ".ai" / "loop.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "enabled": True,
                "repositoryKey": repository_key,
                "linear": {"team": "SAAS", "project": "SaaS Boilerplate"},
                "limits": {"maxRunMinutes": 45},
            }
        ),
        encoding="utf-8",
    )


class LinearLoopLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.state = self.root / "state"
        self.repository = self.root / "repo"
        self.repository.mkdir()
        write_config(self.repository)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def invoke(self, *arguments: str, repository: Path | None = None) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["LUCHDOM_AI_STATE_HOME"] = os.fspath(self.state)
        return subprocess.run(
            [
                sys.executable,
                os.fspath(SCRIPT),
                *arguments,
                "--repo-root",
                os.fspath(repository or self.repository),
            ],
            cwd=ROOT,
            env=environment,
            check=False,
            text=True,
            capture_output=True,
        )

    @unittest.skipUnless(os.name == "nt", "Windows state-root default")
    def test_windows_default_state_root_uses_ai_toolkit_directory(self) -> None:
        local_app_data = self.root / "local-app-data"
        with mock.patch.dict(
            os.environ,
            {"LOCALAPPDATA": os.fspath(local_app_data), "LUCHDOM_AI_STATE_HOME": ""},
        ):
            self.assertEqual(
                (local_app_data / "Luchdom" / "ai-toolkit").resolve(),
                loop_lock.state_root(),
            )

    @staticmethod
    def result(process: subprocess.CompletedProcess[str]) -> dict[str, object]:
        return json.loads(process.stdout)

    def test_second_run_is_busy_until_exact_owner_releases(self) -> None:
        first = self.invoke("acquire")
        self.assertEqual(0, first.returncode, first.stderr)
        first_result = self.result(first)

        second = self.invoke("acquire")
        self.assertEqual(loop_lock.BUSY_EXIT, second.returncode)
        self.assertEqual("busy", self.result(second)["status"])

        wrong_release = self.invoke("release", "--token", "not-the-owner")
        self.assertEqual(loop_lock.ERROR_EXIT, wrong_release.returncode)

        released = self.invoke("release", "--token", str(first_result["token"]))
        self.assertEqual(0, released.returncode, released.stdout)
        self.assertEqual("released", self.result(released)["status"])

        next_run = self.invoke("acquire")
        self.assertEqual(0, next_run.returncode, next_run.stdout)
        self.invoke("release", "--token", str(self.result(next_run)["token"]))

    def test_same_linear_queue_contends_across_different_worktrees(self) -> None:
        other_repository = self.root / "other-worktree"
        other_repository.mkdir()
        write_config(other_repository)

        first = self.invoke("acquire")
        self.assertEqual(0, first.returncode)
        second = self.invoke("acquire", repository=other_repository)
        self.assertEqual(loop_lock.BUSY_EXIT, second.returncode)
        self.assertEqual(self.result(first)["lockKey"], self.result(second)["lockKey"])
        self.invoke("release", "--token", str(self.result(first)["token"]))

    def test_only_one_concurrent_process_acquires(self) -> None:
        environment = os.environ.copy()
        environment["LUCHDOM_AI_STATE_HOME"] = os.fspath(self.state)
        command = [
            sys.executable,
            os.fspath(SCRIPT),
            "acquire",
            "--repo-root",
            os.fspath(self.repository),
        ]
        processes = [
            subprocess.Popen(command, cwd=ROOT, env=environment, text=True, stdout=subprocess.PIPE)
            for _ in range(8)
        ]
        results = []
        for process in processes:
            stdout, _ = process.communicate()
            results.append((process.returncode, json.loads(stdout)))

        acquired = [result for code, result in results if code == 0]
        busy = [result for code, result in results if code == loop_lock.BUSY_EXIT]
        self.assertEqual(1, len(acquired), results)
        self.assertEqual(7, len(busy), results)
        self.invoke("release", "--token", str(acquired[0]["token"]))

    def test_expired_owner_is_replaced_and_cannot_release_successor(self) -> None:
        with mock.patch.dict(os.environ, {"LUCHDOM_AI_STATE_HOME": os.fspath(self.state)}):
            first_code, first = loop_lock.acquire(self.repository)
            self.assertEqual(0, first_code)
            identity = loop_lock.load_identity(self.repository)
            path = loop_lock.lock_path(identity)
            state = json.loads(path.read_text(encoding="utf-8"))

            with mock.patch.object(loop_lock.time, "time", return_value=state["expiresAtEpoch"] + 1):
                second_code, second = loop_lock.acquire(self.repository)
            self.assertEqual(0, second_code)
            self.assertNotEqual(first["token"], second["token"])

            with self.assertRaisesRegex(loop_lock.LockError, "ownership changed"):
                loop_lock.release(self.repository, str(first["token"]))
            self.assertEqual((0, {"status": "released", "lockKey": identity.lock_key}), loop_lock.release(self.repository, str(second["token"])))

    def test_malformed_existing_lock_fails_closed(self) -> None:
        with mock.patch.dict(os.environ, {"LUCHDOM_AI_STATE_HOME": os.fspath(self.state)}):
            identity = loop_lock.load_identity(self.repository)
            path = loop_lock.lock_path(identity)
            path.write_text("not-json", encoding="utf-8")

            with self.assertRaisesRegex(loop_lock.LockError, "unreadable"):
                loop_lock.acquire(self.repository)
            self.assertEqual("not-json", path.read_text(encoding="utf-8"))

    def test_disabled_configuration_cannot_acquire(self) -> None:
        config_path = self.repository / ".ai" / "loop.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["enabled"] = False
        config_path.write_text(json.dumps(config), encoding="utf-8")

        result = self.invoke("acquire")

        self.assertEqual(loop_lock.ERROR_EXIT, result.returncode)
        self.assertIn("enabled to true", str(self.result(result)["message"]))
        self.assertFalse((self.state / "linear-delivery-loop" / "locks").exists())


if __name__ == "__main__":
    unittest.main()
