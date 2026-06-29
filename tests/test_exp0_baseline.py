"""Tests for experiments/exp0_baseline.py.

These tests exercise the real-execution baseline experiment (as opposed to
the synthetic-data generators in codebench.data) to make sure it keeps
actually running the reference solutions rather than silently degrading
into another random-number generator.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experiments"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from exp0_baseline import _SMOKE_TESTS, run  # noqa: E402


def test_smoke_tests_cover_at_least_five_tasks():
    assert len(_SMOKE_TESTS) >= 5


def test_run_returns_report_structure():
    report = run()
    assert report["experiment"] == "exp0_baseline"
    assert "leaderboard" in report
    assert "security_score_by_task" in report
    assert report["n_tasks_evaluated"] == len(_SMOKE_TESTS)


def test_reference_solutions_pass_their_own_smoke_tests():
    # Reference solutions are presumed correct; if a smoke test fails here,
    # either the reference solution or the smoke test itself has a bug.
    report = run()
    board = report["leaderboard"]
    assert len(board) == 1  # single agent: "reference-solution"
    assert board[0]["mean_pass_rate"] == 1.0


def test_security_score_present_for_evaluated_tasks():
    report = run()
    assert set(report["security_score_by_task"].keys()) == set(_SMOKE_TESTS.keys())
    for score in report["security_score_by_task"].values():
        assert 0.0 <= score <= 1.0
