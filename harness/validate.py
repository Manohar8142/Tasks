"""Release gate for tasks. A task ships only if every check passes."""

from __future__ import annotations

from dataclasses import dataclass

from harness.grader import grade
from harness.tamper import probe_patches
from harness.task import HIDDEN_TESTS_MOUNT, Task

_MIN_LEAK_LEN = 25


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


def validate_task(task: Task, sandbox=None, determinism_runs: int = 3) -> list[Check]:
    checks = _structure_checks(task)
    if not all(c.ok for c in checks):
        return checks

    # The unpatched repo must reproduce the issue without breaking anything else.
    base = grade(task, "", sandbox)
    not_failing = [t for t, o in base.fail_to_pass.items() if o == "passed"]
    checks.append(Check(
        "baseline: FAIL_TO_PASS tests fail on the original code",
        not not_failing and base.status != "error",
        f"passing before the fix: {not_failing}" if not_failing else base.status,
    ))
    broken = [t for t, o in base.pass_to_pass.items() if o != "passed"]
    checks.append(Check(
        "baseline: PASS_TO_PASS tests pass on the original code",
        not broken, f"not passing: {broken}" if broken else "",
    ))

    # The reference fix must be solvable and the outcome reproducible.
    gold_text = task.solution_patch.read_text()
    runs = [grade(task, gold_text, sandbox) for _ in range(max(1, determinism_runs))]
    checks.append(Check(
        "reference solution earns reward 1",
        runs[0].reward == 1, _failures(runs[0]),
    ))
    distinct = {tuple(sorted(r.outcomes().items())) for r in runs}
    checks.append(Check(
        f"tests are deterministic across {len(runs)} runs",
        len(distinct) == 1, f"{len(distinct)} distinct outcome sets",
    ))
    checks.append(Check(
        "reference solution trips no suspicious-pattern warnings",
        not runs[0].warnings, ", ".join(runs[0].warnings),
    ))

    # Independently written fixes must also pass: the tests check behaviour,
    # not one particular implementation.
    for alt in task.alt_solutions:
        result = grade(task, alt.read_text(), sandbox)
        checks.append(Check(f"alternative solution {alt.name} earns reward 1", result.reward == 1, _failures(result)))

    for name, patch in probe_patches(task).items():
        result = grade(task, patch, sandbox)
        checks.append(Check(f"reward-hack probe '{name}' earns reward 0", result.reward == 0, result.status))

    leaked = _leaked_lines(task.issue(), gold_text)
    checks.append(Check(
        "issue does not leak lines of the reference fix",
        not leaked, f"leaked: {leaked[:3]}" if leaked else "",
    ))
    return checks


def _structure_checks(task: Task) -> list[Check]:
    hidden_names = {p.name for p in task.hidden_tests_dir.rglob("test_*.py")}
    visible_names = {p.name for p in task.repo_dir.rglob("test_*.py")}
    ids = (*task.fail_to_pass, *task.pass_to_pass)
    return [
        Check("issue.md is present and non-empty", task.issue_path.is_file() and bool(task.issue().strip())),
        Check("solution.patch is present", task.solution_patch.is_file()),
        Check("hidden tests are present", bool(hidden_names)),
        Check("hidden test files are not shipped in the agent's repo",
              not hidden_names & visible_names, str(sorted(hidden_names & visible_names))),
        Check("has at least one FAIL_TO_PASS and one PASS_TO_PASS test",
              bool(task.fail_to_pass) and bool(task.pass_to_pass)),
        Check("FAIL_TO_PASS and PASS_TO_PASS are disjoint",
              not set(task.fail_to_pass) & set(task.pass_to_pass)),
        Check("all test ids point at the hidden test mount",
              all(t.startswith(f"{HIDDEN_TESTS_MOUNT}/") for t in ids)),
    ]


def _failures(result) -> str:
    bad = {t: o for t, o in result.outcomes().items() if o != "passed"}
    if result.status in ("patch_failed", "error", "timeout", "protected_path_modified"):
        return f"{result.status}: {result.log[-500:]}"
    return f"not passing: {bad}" if bad else ""


def _leaked_lines(issue: str, patch_text: str) -> list[str]:
    added = [
        line[1:].strip() for line in patch_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    return [line for line in added if len(line) >= _MIN_LEAK_LEN and line in issue]
