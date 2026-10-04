"""Command line entry point: ``python -m harness <command>``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness.calibrate import calibrate
from harness.gitutil import make_patch, sync_tree
from harness.grader import grade, run_hidden_tests
from harness.task import HIDDEN_TESTS_MOUNT
from harness.sandbox import get_sandbox
from harness.task import load_tasks
from harness.validate import validate_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m harness")
    parser.add_argument("--sandbox", choices=["local", "docker"], default="local")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list tasks")

    p_grade = sub.add_parser("grade", help="grade a candidate patch")
    p_grade.add_argument("task")
    p_grade.add_argument("patch", type=Path, help="unified diff produced by the agent ('-' for stdin)")

    p_val = sub.add_parser("validate", help="run the release checks")
    p_val.add_argument("tasks", nargs="*", help="task ids (default: all)")
    p_val.add_argument("--runs", type=int, default=3, help="repeat count for the determinism check")

    p_cal = sub.add_parser("calibrate", help="solve rates from baseline agent patches")
    p_cal.add_argument("runs_dir", type=Path)
    p_cal.add_argument("tasks", nargs="*")

    p_make = sub.add_parser("make-patch", help="diff a task's repo against an edited copy")
    p_make.add_argument("task")
    p_make.add_argument("edited_dir", type=Path)

    p_derive = sub.add_parser(
        "derive-ids", help="classify hidden tests into FAIL_TO_PASS / PASS_TO_PASS using the reference fix")
    p_derive.add_argument("task")

    args = parser.parse_args(argv)
    sandbox = get_sandbox(args.sandbox)

    if args.command == "list":
        for t in load_tasks():
            print(f"{t.task_id:32} {t.category:10} {t.difficulty:8} "
                  f"F2P={len(t.fail_to_pass)} P2P={len(t.pass_to_pass)}")
        return 0

    if args.command == "grade":
        (task,) = load_tasks([args.task])
        text = sys.stdin.read() if str(args.patch) == "-" else args.patch.read_text()
        result = grade(task, text, sandbox)
        out = result.to_dict()
        out["log"] = out["log"][-2000:]
        print(json.dumps(out, indent=2))
        return 0 if result.reward else 1

    if args.command == "validate":
        failed = 0
        for task in load_tasks(args.tasks or None):
            checks = validate_task(task, sandbox, args.runs)
            ok = all(c.ok for c in checks)
            failed += not ok
            print(f"\n{'PASS' if ok else 'FAIL'}  {task.task_id}")
            for c in checks:
                detail = f"  ({c.detail})" if c.detail and not c.ok else ""
                print(f"  [{'x' if c.ok else ' '}] {c.name}{detail}")
        return 1 if failed else 0

    if args.command == "calibrate":
        for task in load_tasks(args.tasks or None):
            cal = calibrate(task, args.runs_dir, sandbox)
            print(f"{cal.task_id:32} {cal.solved}/{cal.attempts}  {cal.solve_rate:.0%}  {cal.bucket}")
        return 0

    if args.command == "derive-ids":
        (task,) = load_tasks([args.task])
        before = run_hidden_tests(task, "", [HIDDEN_TESTS_MOUNT], sandbox)
        after = run_hidden_tests(task, task.solution_patch.read_text(), [HIDDEN_TESTS_MOUNT], sandbox)
        if before.status != "ran" or after.status != "ran":
            print(before.log, after.log, file=sys.stderr)
            return 1
        ids = sorted(after.outcomes)
        print(json.dumps({
            "fail_to_pass": [t for t in ids if after.outcomes[t] == "passed" and before.outcomes.get(t) != "passed"],
            "pass_to_pass": [t for t in ids if after.outcomes[t] == "passed" and before.outcomes.get(t) == "passed"],
            "fail_with_fix": [t for t in ids if after.outcomes[t] != "passed"],
        }, indent=2))
        return 0

    if args.command == "make-patch":
        (task,) = load_tasks([args.task])
        sys.stdout.write(make_patch(task.repo_dir, sync_tree(args.edited_dir)))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
