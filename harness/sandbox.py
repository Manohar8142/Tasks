"""Execution backends for running grading commands against a workspace."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent / "pytest_plugin"


@dataclass
class ExecResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


class LocalSandbox:
    """Runs commands as a host subprocess with a scrubbed environment.

    Used for authoring and CI. It does not isolate the network or filesystem;
    use DockerSandbox when grading untrusted agent patches.
    """

    name = "local"
    python = sys.executable

    def run(self, argv: list[str], workspace: Path, timeout_s: int) -> ExecResult:
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(workspace),
            "PYTHONPATH": os.pathsep.join([str(workspace), str(PLUGIN_DIR)]),
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "LC_ALL": "C.UTF-8",
        }
        try:
            proc = subprocess.run(
                argv, cwd=workspace, env=env, capture_output=True, text=True, timeout=timeout_s
            )
        except subprocess.TimeoutExpired as exc:
            return ExecResult(-1, _text(exc.stdout), _text(exc.stderr), timed_out=True)
        return ExecResult(proc.returncode, proc.stdout, proc.stderr)


class DockerSandbox:
    """Runs commands in a throwaway container with no network access.

    The workspace is bind-mounted read-write and the results plugin read-only.
    Build the image with ``docker build -f docker/grader.Dockerfile -t swe-tasks-grader .``.
    """

    name = "docker"
    python = "python"

    def __init__(self, image: str = "swe-tasks-grader:latest", memory: str = "2g", cpus: str = "1"):
        self.image = image
        self.memory = memory
        self.cpus = cpus

    def run(self, argv: list[str], workspace: Path, timeout_s: int) -> ExecResult:
        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", self.memory,
            "--cpus", self.cpus,
            "--pids-limit", "256",
            "--read-only", "--tmpfs", "/tmp",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "-e", "PYTHONHASHSEED=0",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-e", "HOME=/tmp",
            "-e", "PYTHONPATH=/workspace:/harness_plugin",
            "-v", f"{workspace}:/workspace",
            "-v", f"{PLUGIN_DIR}:/harness_plugin:ro",
            "-w", "/workspace",
            self.image, *argv,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s + 30)
        except subprocess.TimeoutExpired as exc:
            return ExecResult(-1, _text(exc.stdout), _text(exc.stderr), timed_out=True)
        return ExecResult(proc.returncode, proc.stdout, proc.stderr)


def get_sandbox(name: str):
    if name == "local":
        return LocalSandbox()
    if name == "docker":
        return DockerSandbox()
    raise ValueError(f"unknown sandbox: {name!r}")


def _text(value) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value
