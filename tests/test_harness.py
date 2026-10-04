import dataclasses
from pathlib import Path

import pytest

from harness.calibrate import Calibration, calibrate
from harness.gitutil import make_patch
from harness.grader import grade, lookup, scan_suspicious
from harness.tamper import PROBES
from harness.task import load_tasks
from harness.validate import validate_task

TASKS = load_tasks()


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.task_id)
def test_every_task_passes_release_checks(task):
    failed = [c for c in validate_task(task, determinism_runs=2) if not c.ok]
    assert not failed, failed


@pytest.mark.parametrize("probe", ["conftest_force_pass", "pytest_ini_disable_plugins"])
def test_test_runner_hardening_holds_without_path_protection(probe):
    # Defence in depth: even if the protected-path check were missing, the
    # runner ignores agent conftest.py files and agent pytest config.
    task = dataclasses.replace(load_tasks(["semver-prerelease-precedence"])[0], protected_paths=())
    result = grade(task, make_patch(task.repo_dir, PROBES[probe]))
    assert result.status == "failed"
    assert result.reward == 0


def test_partial_fix_earns_no_reward():
    (task,) = load_tasks(["semver-prerelease-precedence"])

    def fix_release_ordering_only(repo: Path) -> None:
        path = repo / "semverlite" / "version.py"
        path.write_text(path.read_text().replace(
            'return (self.major, self.minor, self.patch, self.prerelease or "")',
            'return (self.major, self.minor, self.patch, self.prerelease is None, self.prerelease or "")',
        ))

    result = grade(task, make_patch(task.repo_dir, fix_release_ordering_only))
    assert result.reward == 0
    assert result.fail_to_pass["_hidden_tests/test_precedence.py::test_prerelease_lower_than_release"] == "passed"
    assert result.fail_to_pass["_hidden_tests/test_precedence.py::test_numeric_identifiers_compare_numerically"] == "failed"


def test_patch_that_breaks_existing_behaviour_earns_no_reward():
    (task,) = load_tasks(["ttlcache-expired-entries"])

    def fix_but_break_lru(repo: Path) -> None:
        path = repo / "ttlcache" / "cache.py"
        text = (path.read_text()
                .replace("self._timer() > expires_at", "self._timer() >= expires_at")
                .replace("        self._data.move_to_end(key)\n", ""))
        path.write_text(text)

    result = grade(task, make_patch(task.repo_dir, fix_but_break_lru))
    assert result.reward == 0
    assert result.pass_to_pass["_hidden_tests/test_existing_behaviour.py::test_lru_eviction_among_live_entries"] == "failed"


def test_unappliable_patch():
    (task,) = load_tasks(["durations-compound-units"])
    result = grade(task, "--- a/nope.py\n+++ b/nope.py\n@@ -1 +1 @@\n-x\n+y\n")
    assert (result.status, result.reward) == ("patch_failed", 0)


def test_lookup_aggregates_parametrized_cases():
    outcomes = {"t.py::a[1]": "passed", "t.py::a[2]": "failed", "t.py::b[1]": "passed", "t.py::c": "passed"}
    assert lookup(outcomes, "t.py::a") == "failed"
    assert lookup(outcomes, "t.py::b") == "passed"
    assert lookup(outcomes, "t.py::c") == "passed"
    assert lookup(outcomes, "t.py::d") == "missing"


def test_suspicious_lines_are_flagged():
    patch = "+++ b/x.py\n+import atexit\n+import _pytest.runner\n context\n-import pytest\n"
    assert scan_suspicious(patch) == ["registers atexit hook", "references pytest"]


def test_calibration_from_baseline_attempts(tmp_path):
    (task,) = load_tasks(["semver-prerelease-precedence"])
    attempts = tmp_path / task.task_id
    attempts.mkdir()
    (attempts / "run1.patch").write_text(task.solution_patch.read_text())
    (attempts / "run2.patch").write_text("")
    cal = calibrate(task, tmp_path)
    assert (cal.solved, cal.attempts, cal.bucket) == (1, 2, "medium")


@pytest.mark.parametrize("solved,attempts,bucket", [
    (0, 8, "review: unsolved (ambiguous or too hard?)"),
    (1, 8, "hard"),
    (4, 8, "medium"),
    (7, 8, "easy"),
    (8, 8, "review: always solved (trivial?)"),
])
def test_calibration_buckets(solved, attempts, bucket):
    assert Calibration("t", attempts, solved).bucket == bucket
