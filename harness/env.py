"""The agent-facing side of a task: an episodic environment with a tool budget.

An episode gives the agent the issue text and a working copy of the repo.
The agent acts only through tools; each call costs one unit of budget. On
``submit`` (or when the budget runs out) the working tree is diffed against
the pre-fix baseline and that diff is graded with the hidden tests.

    env = SWETaskEnv(task)
    obs = env.reset()                         # {"issue": ..., "tools": [...], "budget": N}
    env.step("bash", command="pytest -q tests")
    env.step("write_file", path="pkg/mod.py", content="...")
    result = env.submit()                     # GradeResult with reward 0 or 1
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from harness import gitutil
from harness.grader import GradeResult, grade
from harness.task import Task

TOOLS = {
    "bash": "Run a shell command in the repository root. Args: command.",
    "read_file": "Return a file's contents. Args: path.",
    "write_file": "Create or overwrite a file. Args: path, content.",
    "replace": "Replace one exact occurrence of a string in a file. Args: path, old, new.",
}

_MAX_OUTPUT = 10_000


@dataclass
class StepResult:
    output: str
    budget_left: int
    done: bool


class SWETaskEnv:
    def __init__(self, task: Task, sandbox=None, command_timeout_s: int = 60):
        self.task = task
        self.sandbox = sandbox
        self.command_timeout_s = command_timeout_s
        self._tmp: tempfile.TemporaryDirectory | None = None
        self.workspace: Path | None = None
        self.budget_left = 0
        self.result: GradeResult | None = None

    def reset(self) -> dict:
        self.close()
        self._tmp = tempfile.TemporaryDirectory(prefix=f"episode-{self.task.task_id}-")
        self.workspace = Path(self._tmp.name) / "repo"
        shutil.copytree(self.task.repo_dir, self.workspace)
        gitutil.init_baseline(self.workspace)
        self.budget_left = self.task.tool_call_budget
        self.result = None
        return {"issue": self.task.issue(), "tools": TOOLS, "budget": self.budget_left}

    def step(self, tool: str, **args) -> StepResult:
        if self.workspace is None or self.result is not None:
            raise RuntimeError("call reset() before step()")
        if tool not in TOOLS:
            return StepResult(f"unknown tool {tool!r}; available: {sorted(TOOLS)}", self.budget_left, False)
        self.budget_left -= 1
        try:
            output = getattr(self, f"_tool_{tool}")(**args)
        except (OSError, TypeError, ValueError) as exc:
            output = f"error: {exc}"
        done = self.budget_left <= 0
        if done:
            self.submit()
        return StepResult(output[-_MAX_OUTPUT:], self.budget_left, done)

    def diff(self) -> str:
        gitutil.git(self.workspace, "add", "-A")
        return gitutil.git(self.workspace, "diff", "--cached", "--binary", "HEAD").stdout

    def submit(self) -> GradeResult:
        if self.result is None:
            self.result = grade(self.task, self.diff(), self.sandbox)
        return self.result

    def close(self) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()
        self._tmp = None
        self.workspace = None

    def _resolve(self, path: str) -> Path:
        target = (self.workspace / path).resolve()
        if not target.is_relative_to(self.workspace.resolve()):
            raise ValueError(f"path escapes the repository: {path}")
        return target

    def _tool_bash(self, command: str) -> str:
        try:
            proc = subprocess.run(
                command, shell=True, cwd=self.workspace, capture_output=True, text=True,
                timeout=self.command_timeout_s,
            )
        except subprocess.TimeoutExpired:
            return f"error: command timed out after {self.command_timeout_s}s"
        return f"exit code {proc.returncode}\n{proc.stdout}{proc.stderr}"

    def _tool_read_file(self, path: str) -> str:
        return self._resolve(path).read_text()

    def _tool_write_file(self, path: str, content: str) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"wrote {len(content)} bytes to {path}"

    def _tool_replace(self, path: str, old: str, new: str) -> str:
        target = self._resolve(path)
        text = target.read_text()
        count = text.count(old)
        if count != 1:
            raise ValueError(f"expected exactly one match in {path}, found {count}")
        target.write_text(text.replace(old, new))
        return f"edited {path}"
