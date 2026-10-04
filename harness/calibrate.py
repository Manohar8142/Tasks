"""Difficulty calibration from baseline agent attempts.

Expects ``<runs_dir>/<task_id>/*.patch``, one file per independent attempt.
Tasks that no baseline solves are reviewed for ambiguity or unsolvability;
tasks every baseline solves are reviewed as possibly trivial.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness.grader import grade
from harness.task import Task


@dataclass
class Calibration:
    task_id: str
    attempts: int
    solved: int

    @property
    def solve_rate(self) -> float:
        return self.solved / self.attempts if self.attempts else 0.0

    @property
    def bucket(self) -> str:
        if not self.attempts:
            return "no attempts"
        rate = self.solve_rate
        if rate == 0:
            return "review: unsolved (ambiguous or too hard?)"
        if rate == 1:
            return "review: always solved (trivial?)"
        if rate < 0.25:
            return "hard"
        if rate < 0.6:
            return "medium"
        return "easy"


def calibrate(task: Task, runs_dir: Path, sandbox=None) -> Calibration:
    attempts = sorted((runs_dir / task.task_id).glob("*.patch"))
    solved = sum(grade(task, p.read_text(), sandbox).reward for p in attempts)
    return Calibration(task.task_id, len(attempts), solved)
