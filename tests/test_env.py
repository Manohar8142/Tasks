import dataclasses

from harness.env import SWETaskEnv
from harness.task import load_tasks


def _semver():
    (task,) = load_tasks(["semver-prerelease-precedence"])
    return task


def test_scripted_episode_that_fixes_the_bug_earns_reward():
    env = SWETaskEnv(_semver())
    obs = env.reset()
    assert "Pre-release versions sort in the wrong order" in obs["issue"]
    assert "hidden_tests" not in env.step("bash", command="ls -a").output

    source = env.step("read_file", path="semverlite/version.py").output
    assert "def _key" in source
    env.step(
        "replace", path="semverlite/version.py",
        old='        return (self.major, self.minor, self.patch, self.prerelease or "")\n',
        new=(
            "        if self.prerelease is None:\n"
            "            return (self.major, self.minor, self.patch, (1,))\n"
            "        parts = tuple((0, int(p), '') if p.isdigit() else (1, 0, p)"
            " for p in self.prerelease.split('.'))\n"
            "        return (self.major, self.minor, self.patch, (0, parts))\n"
        ),
    )
    assert "exit code 0" in env.step("bash", command="python -m pytest -q tests").output
    result = env.submit()
    env.close()
    assert result.reward == 1, result.to_dict()


def test_no_changes_earns_zero():
    env = SWETaskEnv(_semver())
    env.reset()
    assert env.submit().reward == 0
    env.close()


def test_budget_exhaustion_ends_episode_and_grades():
    task = dataclasses.replace(_semver(), tool_call_budget=2)
    env = SWETaskEnv(task)
    env.reset()
    assert not env.step("bash", command="true").done
    last = env.step("bash", command="true")
    assert last.done and last.budget_left == 0
    assert env.result is not None and env.result.reward == 0
    env.close()


def test_file_tools_cannot_escape_the_repo():
    env = SWETaskEnv(_semver())
    env.reset()
    assert env.step("read_file", path="../../etc/passwd").output.startswith("error:")
    env.close()
