"""Task specification and loading.

A task lives in ``tasks/<task_id>/`` and contains:

    task.json         metadata, test ids and grading settings
    issue.md          the only instructions the agent sees
    repo/             the repository at the pre-fix commit (visible to the agent)
    hidden_tests/     grading tests, never copied into the agent's environment
    solution.patch    reference fix, used only for validation
    alt_solutions/    other correct fixes; prove the tests are not overfit
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"

HIDDEN_TESTS_MOUNT = "_hidden_tests"

# Paths an agent's patch may never touch. Anything that can change how tests
# are collected or executed is locked, not only the test files themselves.
DEFAULT_PROTECTED_PATHS = (
    "tests/*",
    f"{HIDDEN_TESTS_MOUNT}/*",
    "*conftest.py",
    "pytest.ini",
    "tox.ini",
    "setup.cfg",
    "pyproject.toml",
    "*sitecustomize.py",
    "*usercustomize.py",
    "*.pth",
)

_REQUIRED_KEYS = ("task_id", "fail_to_pass", "pass_to_pass")


@dataclass(frozen=True)
class Task:
    task_id: str
    root: Path
    category: str
    difficulty: str
    fail_to_pass: tuple[str, ...]
    pass_to_pass: tuple[str, ...]
    protected_paths: tuple[str, ...]
    timeout_s: int
    tool_call_budget: int

    @property
    def repo_dir(self) -> Path:
        return self.root / "repo"

    @property
    def hidden_tests_dir(self) -> Path:
        return self.root / "hidden_tests"

    @property
    def issue_path(self) -> Path:
        return self.root / "issue.md"

    @property
    def solution_patch(self) -> Path:
        return self.root / "solution.patch"

    @property
    def alt_solutions(self) -> list[Path]:
        return sorted((self.root / "alt_solutions").glob("*.patch"))

    def issue(self) -> str:
        return self.issue_path.read_text()

    def is_protected(self, path: str) -> bool:
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.protected_paths)

    @classmethod
    def load(cls, root: Path) -> Task:
        spec = json.loads((root / "task.json").read_text())
        missing = [k for k in _REQUIRED_KEYS if k not in spec]
        if missing:
            raise ValueError(f"{root}/task.json is missing keys: {missing}")
        if spec["task_id"] != root.name:
            raise ValueError(f"task_id {spec['task_id']!r} does not match directory {root.name!r}")
        return cls(
            task_id=spec["task_id"],
            root=root,
            category=spec.get("category", "bugfix"),
            difficulty=spec.get("difficulty", "unrated"),
            fail_to_pass=tuple(spec["fail_to_pass"]),
            pass_to_pass=tuple(spec["pass_to_pass"]),
            protected_paths=tuple(spec.get("protected_paths", DEFAULT_PROTECTED_PATHS)),
            timeout_s=int(spec.get("timeout_s", 120)),
            tool_call_budget=int(spec.get("tool_call_budget", 50)),
        )


def load_tasks(task_ids: list[str] | None = None, tasks_dir: Path = TASKS_DIR) -> list[Task]:
    roots = sorted(p for p in tasks_dir.iterdir() if (p / "task.json").is_file())
    tasks = [Task.load(p) for p in roots]
    if task_ids:
        by_id = {t.task_id: t for t in tasks}
        unknown = [t for t in task_ids if t not in by_id]
        if unknown:
            raise KeyError(f"unknown task ids: {unknown}")
        tasks = [by_id[t] for t in task_ids]
    return tasks
