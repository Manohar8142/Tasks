"""Pytest plugin that records one outcome per test node id as JSON.

Loaded by the grader with ``-p harness_results``. A failure in any phase
(setup, call, teardown) makes the test count as failed.
"""

import json

_results: dict[str, str] = {}


def pytest_addoption(parser):
    parser.addoption("--harness-results", action="store", default=None)


def pytest_collectreport(report):
    if report.failed:
        _results[report.nodeid] = "error"


def pytest_runtest_logreport(report):
    if _results.get(report.nodeid) == "failed":
        return
    if report.failed:
        _results[report.nodeid] = "failed"
    elif report.skipped:
        _results[report.nodeid] = "skipped"
    elif report.when == "call":
        _results[report.nodeid] = "passed"


def pytest_sessionfinish(session, exitstatus):
    path = session.config.getoption("--harness-results")
    if path:
        with open(path, "w") as fh:
            json.dump(_results, fh, indent=2, sort_keys=True)
