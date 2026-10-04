# SWE-agent task suite: authoring, sandboxing and execution-based reward

This is a public sample of how I build coding tasks for training and
evaluating software-engineering agents in agentic, RL-style environments. It
contains the full pipeline at small scale:

* **Tasks.** Each is a repository at a pre-fix state plus a natural-language
  issue. There are three tasks: two bug fixes and one feature.
* **An episodic agent environment.** Tool calls are budgeted, and on submit the
  agent's diff is graded.
* **A grader.** Hidden tests produce a binary reward.
* **A release gate.** Every task must pass it before it ships. It covers
  baseline reproduction, solvability, determinism, alternative solutions,
  reward-hacking probes and leakage checks.
* **Difficulty calibration** from baseline agent attempts.

The task repositories here are small self-contained libraries written for
this sample, so the whole suite runs in seconds. The same format applies
unchanged to a real open-source repo checked out at a pre-fix commit.

```
python -m harness list                 # tasks and test counts
python -m harness validate             # release gate for every task
python -m harness grade <task> fix.patch
python -m pytest -q                    # tests for the harness itself
```

## Tasks

| Task | Type | What the agent must do | F2P | P2P |
|---|---|---|---|---|
| `semver-prerelease-precedence` | bug fix | Make `Version` ordering follow SemVer 2.0.0 §11 (pre-release < release, numeric identifiers compared numerically, numeric < alphanumeric) without breaking hashing or build-metadata equality | 5 | 19 |
| `ttlcache-expired-entries` | bug fix | Fix three ways expired entries leak from an LRU+TTL cache: off-by-one at the expiry instant, `len()` counting expired entries, and expired entries forcing eviction of live ones | 5 | 12 |
| `durations-compound-units` | feature | Extend `parse_duration` to accept compound (`1h30m`), fractional (`1.5h`) and `ms` inputs with strict ordering and validation, exact to the microsecond | 17 | 38 |

## Task format

```
tasks/<task_id>/
  task.json          metadata, FAIL_TO_PASS / PASS_TO_PASS ids, timeout, tool budget
  issue.md           the only instructions the agent sees
  repo/              repository at the pre-fix state (copied into the agent's environment)
  hidden_tests/      grading tests; never enter the agent's environment
  solution.patch     reference fix, used only for validation
  alt_solutions/     independently written fixes with a different design
```

Each issue is written like a real bug report or feature request. It describes
the symptoms, a minimal reproduction and the expected behaviour precisely
enough to be solvable, and never describes the fix. The validator enforces
the "never describes the fix" part mechanically: it checks that no line of
the reference patch appears in the issue.

## Environment

`harness/env.py` is the agent-facing side of a task:

```python
env = SWETaskEnv(task)
obs = env.reset()            # issue text, tool specs, tool-call budget
env.step("bash", command="python -m pytest -q tests")
env.step("replace", path="ttlcache/cache.py", old="...", new="...")
result = env.submit()        # diff vs. baseline -> grader -> reward 0/1
```

* The agent gets a fresh copy of the pre-fix repo committed as a git
  baseline. Its submission is the diff against that baseline.
* Tools: `bash`, `read_file`, `write_file`, `replace`. Each call costs one
  unit of the per-task `tool_call_budget`. When the budget runs out, the
  episode ends and whatever is on disk is graded.
* File tools cannot escape the repository root.
* In the containerised setup (`docker/agent.Dockerfile`), the agent runs as a
  non-root user with `--network none`, and only the pre-fix repo and issue are
  copied into the image. CI asserts that the hidden tests are absent from the
  image.

## Correctness and reward

`harness/grader.py` scores a candidate patch:

1. Copy the pre-fix repo to a fresh workspace and apply the patch with
   `git apply`. A patch that doesn't apply gets reward 0.
2. **Protected paths.** If the patch adds, edits or deletes anything that can
   affect testing (`tests/`, any `conftest.py`, `pytest.ini`, `tox.ini`,
   `setup.cfg`, `pyproject.toml`, `sitecustomize.py`, `*.pth`, the hidden-test
   mount), it gets reward 0.
3. Copy the hidden tests in after the patch, so the agent could never have
   seen or changed them.
4. Run pytest in the sandbox under a hardened config. The harness supplies its
   own `-c` ini, so agent config is ignored. It also passes `--noconftest`,
   disables the cache, and fixes `PYTHONHASHSEED`. A small plugin records one
   outcome per test node id. In Docker mode the run has no network and has
   memory, CPU and PID limits.
5. **Reward = 1 only if every FAIL_TO_PASS test passes** (the issue is fixed)
   **and every PASS_TO_PASS test passes** (nothing regressed). Otherwise it is
   0. A failure in setup, call or teardown counts as a failure. A test that is
   missing or errors during collection counts as a failure. A parametrized id
   passes only if all of its cases pass.
6. Added lines that reference pytest internals, `atexit`, `sys.modules`, hard
   exits or grader internals are flagged for human review.

FAIL_TO_PASS and PASS_TO_PASS are **measured, not hand-labelled**.
`python -m harness derive-ids <task>` runs every hidden test on the original
code and on the reference fix. Tests that fail before and pass after become
FAIL_TO_PASS. Tests that pass both times become PASS_TO_PASS. Any test that
fails with the fix blocks the task.

## Release gate

`python -m harness validate` runs these checks on each task. A task ships only
if all of them pass:

| Check | Why |
|---|---|
| FAIL_TO_PASS tests fail on the original code | The tests reproduce the issue |
| PASS_TO_PASS tests pass on the original code | The regression guard is valid |
| Reference solution earns reward 1 | The task is solvable as specified |
| Identical outcomes across repeated runs | No flaky reward signal |
| Every alternative solution earns reward 1 | Tests check behaviour, not one implementation |
| Every reward-hack probe earns reward 0 | The reward can't be gamed |
| No line of the fix appears in the issue | No solution leakage |

The reward-hack probes in `harness/tamper.py` are adversarial patches that
model real agent exploits. They include a `conftest.py` hook that rewrites
every report to "passed" (at the root and nested), a `pytest.ini` that
disables the results plugin, `sitecustomize.py` and `.pth` injection,
shadowing the hidden-test directory, and deleting or hollowing out the
visible tests. The harness tests also turn off path protection and confirm
the runner hardening still defeats the conftest and ini attacks on its own.
They also show that a partial fix and a fix that breaks LRU behaviour both
earn 0.

## Difficulty calibration

Put independent baseline-agent attempts in `runs/<task_id>/*.patch` and run
`python -m harness calibrate runs/`. Each task gets a solve rate and a bucket.
A task no baseline solves is sent back for review as possibly ambiguous or
unsolvable. A task every baseline solves is reviewed as possibly trivial.

## Threat model and limits

* Path protection and runner hardening stop config- and file-level attacks.
  Code that the patch adds runs inside the same Python process as the tests.
  So a deliberately adversarial patch could, in principle, patch pytest at
  import time. That is why suspicious-pattern flags go to human review, and
  why untrusted patches should be graded with `--sandbox docker`.
* `LocalSandbox` does not isolate the network or filesystem. It exists for
  authoring and CI. Network isolation comes from the Docker sandbox, which the
  `docker` CI job exercises.

See [docs/TASK_AUTHORING.md](docs/TASK_AUTHORING.md) for the step-by-step
authoring workflow.
