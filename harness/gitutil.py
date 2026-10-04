"""Small git helpers used to apply and produce patches in scratch workspaces."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

# Byproducts of running code, never part of a submitted change.
_IGNORED_ARTIFACTS = "__pycache__/\n*.pyc\n.pytest_cache/\n*.egg-info/\n"

_GIT_ENV_ARGS = ["-c", "user.name=harness", "-c", "user.email=harness@localhost", "-c", "commit.gpgsign=false"]


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *_GIT_ENV_ARGS, *args], cwd=cwd, capture_output=True, text=True, check=check)


def init_baseline(workspace: Path) -> None:
    """Turn a plain directory into a repo whose HEAD is the pre-fix state."""
    git(workspace, "init", "-q")
    (workspace / ".git" / "info").mkdir(parents=True, exist_ok=True)
    (workspace / ".git" / "info" / "exclude").write_text(_IGNORED_ARTIFACTS)
    git(workspace, "add", "-A")
    git(workspace, "commit", "-q", "--allow-empty", "-m", "baseline")


def apply_patch(workspace: Path, patch_text: str) -> tuple[bool, str]:
    patch_file = workspace.parent / "candidate.patch"
    patch_file.write_text(patch_text if patch_text.endswith("\n") else patch_text + "\n")
    proc = git(workspace, "apply", "--whitespace=nowarn", str(patch_file), check=False)
    return proc.returncode == 0, proc.stderr


def changed_files(workspace: Path) -> list[str]:
    """Every path added, modified, deleted or renamed relative to the baseline."""
    git(workspace, "add", "-A")
    proc = git(workspace, "diff", "--cached", "--name-only", "--no-renames", "HEAD")
    return sorted(line for line in proc.stdout.splitlines() if line)


def make_patch(repo_dir: Path, mutate: Callable[[Path], None]) -> str:
    """Return the diff produced by running ``mutate`` on a copy of ``repo_dir``."""
    with tempfile.TemporaryDirectory(prefix="make-patch-") as tmp:
        work = Path(tmp) / "repo"
        shutil.copytree(repo_dir, work)
        init_baseline(work)
        mutate(work)
        git(work, "add", "-A")
        return git(work, "diff", "--cached", "--binary", "HEAD").stdout


def sync_tree(src: Path):
    """A ``make_patch`` mutation that makes the repo identical to ``src``."""
    def mutate(repo: Path) -> None:
        for child in repo.iterdir():
            if child.name == ".git":
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
        shutil.copytree(src, repo, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".git"))
    return mutate
