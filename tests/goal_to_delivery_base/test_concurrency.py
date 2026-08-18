from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import sys
import time
import uuid

from tests.goal_to_delivery_base.support import (
    RepositoryTestCase,
    SKILL_ROOT,
    create_windows_junction,
)
from scripts.errors import UnsafePathError, ValidationError
from scripts.mutex import AllocationMutex


class ConcurrencyTests(RepositoryTestCase):
    def test_dead_allocation_mutex_is_quarantined_before_retry(self) -> None:
        lock = self.state_base / "dead.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text(
            json.dumps(
                {
                    "token": str(uuid.uuid4()),
                    "pid": 2147483647,
                    "createdNs": 1,
                    "released": False,
                }
            ),
            encoding="utf-8",
        )
        with AllocationMutex(lock, timeout_seconds=1):
            self.assertTrue(lock.exists())
        stale = list((lock.parent / "stale-locks").glob("*.json"))
        self.assertEqual(len(stale), 1)

    def test_untrusted_mutex_token_cannot_control_evidence_path(self) -> None:
        outside = self.state_base / "outside-sentinel.txt"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_text("unchanged", encoding="utf-8")
        malicious_tokens = ("../../outside-sentinel", "..\\..\\outside-sentinel", ".", "..")
        for index, token in enumerate(malicious_tokens):
            with self.subTest(token=token):
                lock = self.state_base / f"malicious-{index}.lock"
                lock.write_text(
                    json.dumps(
                        {
                            "token": token,
                            "pid": 2147483647,
                            "createdNs": 1,
                            "released": False,
                        }
                    ),
                    encoding="utf-8",
                )
                with self.assertRaises(ValidationError):
                    AllocationMutex(lock, timeout_seconds=1).acquire()
                self.assertEqual(outside.read_text(encoding="utf-8"), "unchanged")
                self.assertFalse((lock.parent / "stale-locks").exists())

    def test_stale_lock_evidence_junction_fails_closed_without_outside_write(self) -> None:
        lock_root = self.state_base / "mutex-root"
        lock_root.mkdir(parents=True)
        lock = lock_root / "allocation.lock"
        dead = {
            "token": str(uuid.uuid4()),
            "pid": 2147483647,
            "createdNs": 1,
            "released": False,
        }
        lock.write_text(json.dumps(dead), encoding="utf-8")
        outside = self.root / "outside-stale-locks"
        outside.mkdir()
        sentinel = outside / "sentinel.txt"
        sentinel.write_text("outside-unchanged", encoding="utf-8")
        create_windows_junction(self, lock_root / "stale-locks", outside)

        with self.assertRaises(UnsafePathError):
            AllocationMutex(lock, timeout_seconds=1).acquire()
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "outside-unchanged")
        self.assertEqual(json.loads(lock.read_text(encoding="utf-8")), dead)

    def test_mutex_hardlink_leaf_is_rejected_before_lock_sentinel_write(self) -> None:
        lock_root = self.state_base / "hardlink-root"
        lock_root.mkdir(parents=True)
        outside = self.root / "outside-hardlink-sentinel.txt"
        outside.write_text("outside-unchanged", encoding="utf-8")
        lock = lock_root / "allocation.lock"
        os.link(outside, lock)

        with self.assertRaises(UnsafePathError):
            AllocationMutex(lock, timeout_seconds=1).acquire()
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside-unchanged")

    def test_simultaneous_identical_goals_allocate_distinct_keys_folders_and_uuids(self) -> None:
        def allocate(_: int):
            return self.manager().initialize_local(
                workflow="manual",
                goal="Same exact goal",
                display_title="Same exact goal",
            )

        with ThreadPoolExecutor(max_workers=6) as executor:
            descriptors = list(executor.map(allocate, range(6)))

        self.assertEqual({item["workKey"] for item in descriptors}, {f"{value:03d}" for value in range(1, 7)})
        self.assertEqual(len({item["artifactFolder"] for item in descriptors}), 6)
        self.assertEqual(len({item["workflowId"] for item in descriptors}), 6)

        manager = self.manager()
        for descriptor in descriptors:
            self.assertEqual(
                manager.resume(workflow_id=descriptor["workflowId"])["artifactFolder"],
                descriptor["artifactFolder"],
            )

    def test_separate_processes_allocate_distinct_workflows(self) -> None:
        code = r'''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[3])
from scripts.workflow_init import WorkflowManager
descriptor = WorkflowManager(
    Path(sys.argv[1]),
    repository_key="test-repository",
    state_home_override=Path(sys.argv[2]),
).initialize_local(workflow="manual", goal="Cross-process identical goal")
print(json.dumps(descriptor), flush=True)
'''
        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    code,
                    str(self.repository),
                    str(self.state_base),
                    str(SKILL_ROOT),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            for _ in range(4)
        ]
        descriptors = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=90)
            self.assertEqual(process.returncode, 0, stderr)
            descriptors.append(json.loads(stdout))
        self.assertEqual({item["workKey"] for item in descriptors}, {"001", "002", "003", "004"})
        self.assertEqual(len({item["workflowId"] for item in descriptors}), 4)
        self.assertEqual(len({item["artifactFolder"] for item in descriptors}), 4)

    def test_killed_process_releases_advisory_mutex_for_immediate_recovery(self) -> None:
        lock = self.state_base / "killed-process.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        ready = self.root / "lock-ready"
        code = r'''
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[3])
from scripts.mutex import AllocationMutex
mutex = AllocationMutex(Path(sys.argv[1]), timeout_seconds=30).acquire()
Path(sys.argv[2]).write_text("ready", encoding="utf-8")
time.sleep(120)
mutex.release()
'''
        process = subprocess.Popen(
            [sys.executable, "-c", code, str(lock), str(ready), str(SKILL_ROOT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        deadline = time.monotonic() + 30
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if not ready.exists():
            process.kill()
            _, stderr = process.communicate(timeout=10)
            self.fail(f"Killed-process mutex fixture did not become ready: {stderr}")
        process.kill()
        process.communicate(timeout=10)

        with AllocationMutex(lock, timeout_seconds=5):
            pass
        released = json.loads(lock.read_text(encoding="utf-8"))
        self.assertTrue(released["released"])
        self.assertEqual(released["pid"], os.getpid())

    def test_killed_pre_descriptor_process_recovers_journal_and_quarantines_orphan(self) -> None:
        ready = self.root / "allocation-ready"
        code = r'''
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[4])
import scripts.workflow_init as workflow_init
real_write = workflow_init.atomic_write_json
def blocking_write(path, value, **kwargs):
    if Path(path).name == "workflow.json":
        Path(sys.argv[3]).write_text("ready", encoding="utf-8")
        time.sleep(120)
    return real_write(path, value, **kwargs)
workflow_init.atomic_write_json = blocking_write
workflow_init.WorkflowManager(
    Path(sys.argv[1]),
    repository_key="test-repository",
    state_home_override=Path(sys.argv[2]),
).initialize_local(workflow="manual", goal="Killed allocation")
'''
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                code,
                str(self.repository),
                str(self.state_base),
                str(ready),
                str(SKILL_ROOT),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        deadline = time.monotonic() + 30
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if not ready.exists():
            process.kill()
            _, stderr = process.communicate(timeout=10)
            self.fail(f"Killed allocation fixture did not become ready: {stderr}")
        process.kill()
        process.communicate(timeout=10)

        recovered = self.manager()
        registry = recovered.registry.load_unlocked()
        self.assertEqual(registry["workflows"], {})
        transactions = recovered.home.repository / "transactions"
        self.assertFalse(any(transactions.glob("*.json")))
        artifacts_root = self.repository / ".ai" / "work"
        normal = [
            path for path in artifacts_root.iterdir()
            if not path.name.startswith(".quarantine-")
        ]
        self.assertEqual(normal, [])
        self.assertEqual(len(list(artifacts_root.glob(".quarantine-*"))), 1)
