from __future__ import annotations

import json
import os
import subprocess
import sys

from tests.goal_to_delivery_base.support import RepositoryTestCase, SKILL_ROOT


CLI_PATH = SKILL_ROOT / "scripts" / "cli.py"


class CliErrorBoundaryTests(RepositoryTestCase):
    def _run(self, *arguments: str, environment: dict[str, str] | None = None):
        return subprocess.run(
            [sys.executable, str(CLI_PATH), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
            shell=False,
        )

    def test_missing_git_emits_one_redacted_json_error_without_traceback(self) -> None:
        environment = os.environ.copy()
        environment["PATH"] = ""
        secret = "missing-git-secret-sentinel"
        completed = self._run(
            "init",
            "--repository-root",
            str(self.repository),
            "--repository-key",
            "test-repository",
            "--state-home",
            str(self.state_base),
            "--workflow",
            "manual",
            "--goal",
            f"api_key={secret}",
            environment=environment,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        lines = completed.stderr.splitlines()
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["status"], "failed")
        self.assertNotIn("Traceback", completed.stderr)
        self.assertNotIn(secret, completed.stderr)
        self.assertNotIn(str(self.repository), completed.stderr)

    def test_invalid_state_base_io_emits_one_generic_json_error(self) -> None:
        sensitive_state = self.root / "api-key-secret-state"
        sensitive_state.write_text("not-a-directory", encoding="utf-8")
        completed = self._run(
            "init",
            "--repository-root",
            str(self.repository),
            "--repository-key",
            "test-repository",
            "--state-home",
            str(sensitive_state),
            "--workflow",
            "manual",
            "--goal",
            "Safe goal",
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        lines = completed.stderr.splitlines()
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["status"], "failed")
        self.assertNotIn("Traceback", completed.stderr)
        self.assertNotIn("api-key-secret-state", completed.stderr)
