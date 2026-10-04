"""Execution-based grading: apply a candidate patch, run hidden tests, emit a reward.

Reward is binary. It is 1 only when the patch applies cleanly, touches no
protected path, every FAIL_TO_PASS test passes (the issue is fixed) and every
PASS_TO_PASS test passes (nothing regressed). Otherwise it is 0.
"""

from __future__ import annotations

import json
import re
import secrets
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from harness import gitutil
from harness.sandbox import LocalSandbox
from harness.task import HIDDEN_TESTS_MOUNT, Task

# Added lines matching these are not rejected, but are flagged for human
# review: legitimate fixes for these tasks never need them.
SUSPICIOUS_PATTERNS = {
    "references pytest": re.compile(r"\b_?pytest\b"),
    "registers atexit hook": re.compile(r"\batexit\b"),
    "hard process exit": re.compile(r"\bos\._exit\b|\bsys\.exit\b"),
    "mutates sys.modules": re.compile(r"\bsys\.modules\b"),
    "mentions grader internals": re.compile(r"harness|_hidden_tests|fail_to_pass|pass_to_pass", re.I),
}

_HARNESS_INI = "[pytest]\naddopts =\n"


@dataclass
class GradeResult:
    task_id: str
    reward: int
    status: str
    fail_to_pass: dict[str, str] = field(default_factory=dict)
    pass_to_pass: dict[str, str] = field(default_factory=dict)
    changed_files: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    log: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def outcomes(self) -> dict[str, str]:
        return {**self.fail_to_pass, **self.pass_to_pass}


def grade(task: Task, patch_text: str, sandbox=None) -> GradeResult:
    run = run_hidden_tests(task, patch_text, list(task.fail_to_pass + task.pass_to_pass), sandbox)
    if run.status != "ran":
        return GradeResult(
            task.task_id, 0, run.status, changed_files=run.changed_files,
            violations=run.violations, warnings=run.warnings, log=run.log,
        )
    f2p = {t: lookup(run.outcomes, t) for t in task.fail_to_pass}
    p2p = {t: lookup(run.outcomes, t) for t in task.pass_to_pass}
    solved = all(v == "passed" for v in (*f2p.values(), *p2p.values()))
    return GradeResult(
        task.task_id, int(solved), "passed" if solved else "failed",
        fail_to_pass=f2p, pass_to_pass=p2p, changed_files=run.changed_files,
        warnings=run.warnings, log=run.log,
    )


@dataclass
class TestRun:
    status: str
    outcomes: dict[str, str] = field(default_factory=dict)
    changed_files: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    log: str = ""


def run_hidden_tests(task: Task, patch_text: str, selectors: list[str], sandbox=None) -> TestRun:
    """Apply ``patch_text`` to a fresh copy of the repo and run hidden tests.

    ``status`` is "ran" when pytest produced results, otherwise the reason
    it did not (patch_failed, protected_path_modified, timeout, error).
    """
    sandbox = sandbox or LocalSandbox()
    with tempfile.TemporaryDirectory(prefix=f"grade-{task.task_id}-") as tmp:
        ws = Path(tmp) / "workspace"
        shutil.copytree(task.repo_dir, ws)
        gitutil.init_baseline(ws)

        if patch_text.strip():
            ok, err = gitutil.apply_patch(ws, patch_text)
            if not ok:
                return TestRun("patch_failed", log=err)

        changed = gitutil.changed_files(ws)
        violations = [p for p in changed if task.is_protected(p)]
        warnings = scan_suspicious(patch_text)
        if violations:
            return TestRun("protected_path_modified", changed_files=changed,
                           violations=violations, warnings=warnings)

        # Hidden tests are copied in only now, after the agent's patch, so the
        # agent could never have read or edited them.
        hidden = ws / HIDDEN_TESTS_MOUNT
        shutil.copytree(task.hidden_tests_dir, hidden)
        (hidden / ".harness_pytest.ini").write_text(_HARNESS_INI)
        results_rel = f"{HIDDEN_TESTS_MOUNT}/.results-{secrets.token_hex(8)}.json"

        argv = [
            sandbox.python, "-m", "pytest",
            "-c", f"{HIDDEN_TESTS_MOUNT}/.harness_pytest.ini",
            "--rootdir", ".",
            "--noconftest",
            "-p", "no:cacheprovider",
            "-p", "harness_results",
            f"--harness-results={results_rel}",
            "-q", "--tb=short",
            *selectors,
        ]
        proc = sandbox.run(argv, ws, task.timeout_s)
        log = proc.stdout + proc.stderr
        if proc.timed_out:
            return TestRun("timeout", changed_files=changed, warnings=warnings, log=log)
        results_file = ws / results_rel
        if not results_file.is_file():
            return TestRun("error", changed_files=changed, warnings=warnings, log=log)
        outcomes = json.loads(results_file.read_text())
        return TestRun("ran", outcomes, changed, [], warnings, log)


def lookup(outcomes: dict[str, str], test_id: str) -> str:
    """Outcome for a test id; a parametrized id passes only if every case passes."""
    if test_id in outcomes:
        return outcomes[test_id]
    cases = [o for nodeid, o in outcomes.items() if nodeid.startswith(test_id + "[")]
    if not cases:
        return "missing"
    return "passed" if all(o == "passed" for o in cases) else "failed"


def scan_suspicious(patch_text: str) -> list[str]:
    found = []
    for line in patch_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for label, pattern in SUSPICIOUS_PATTERNS.items():
            if pattern.search(line) and label not in found:
                found.append(label)
    return found
