# Authoring a task

1. **Pick a real behavioural bug or a well-scoped feature.** It should need
   code reading and reasoning, with a fix that can be checked by tests rather
   than by inspection. Avoid tasks whose only correct answer is one specific
   implementation.
2. **Create `tasks/<task_id>/repo/`** at the pre-fix state, including the
   project's own visible tests. Those tests must pass. The agent can run them,
   but they are not used for grading.
3. **Write `issue.md`** as a user would: symptoms, a minimal reproduction and
   the expected behaviour. Specify every behaviour the hidden tests check, but
   never describe the fix.
4. **Write the hidden tests** in `hidden_tests/`:
   * tests that reproduce the issue (future FAIL_TO_PASS)
   * tests for existing behaviour the fix could plausibly break, for example
     ordering, hashing, LRU order, error types (future PASS_TO_PASS)
   * edge cases that a shallow fix would miss
   * no timing, randomness, network or ordering dependence
5. **Write the reference fix** in a copy of the repo, then run
   `python -m harness make-patch <task_id> <edited_copy> > tasks/<task_id>/solution.patch`.
6. **Write at least one alternative fix with a different design** and save it
   under `alt_solutions/`. If the alternative fails, the tests are overfit to
   your implementation.
7. **Derive the test ids** with `python -m harness derive-ids <task_id>` and
   copy them into `task.json`.
8. **Run the release gate** with `python -m harness validate <task_id>`. Fix
   the task until every check passes.
9. **Calibrate** with baseline agent attempts (`python -m harness calibrate`).
   Revise or discard tasks that nothing solves because they are ambiguous, or
   that everything solves because they are trivial.
