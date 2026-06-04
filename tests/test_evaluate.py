"""Tests for codebench.evaluate."""

import math

import pytest

from codebench.core import AgentSubmission, ExecutionResult
from codebench.evaluate import (
    cost_adjusted_score,
    leaderboard,
    regression_rate,
    test_pass_rate,
    tool_efficiency_score,
)


def _make_result(passed: int, total: int, regressions: int = 0, agent: str = "anote-code") -> ExecutionResult:
    return ExecutionResult(
        task_id="t001",
        agent_name=agent,
        tests_passed=passed,
        tests_total=total,
        regression_count=regressions,
        execution_success=True,
    )


def _make_sub(tool_calls: int = 5, cost: float = 0.10, agent: str = "anote-code") -> AgentSubmission:
    return AgentSubmission(
        task_id="t001",
        agent_name=agent,
        generated_code="pass",
        tool_calls_used=tool_calls,
        latency_ms=100.0,
        cost_usd=cost,
    )


def test_test_pass_rate_normal():
    result = _make_result(7, 10)
    assert test_pass_rate(result) == pytest.approx(0.7)


def test_test_pass_rate_zero_total():
    result = _make_result(0, 0)
    assert test_pass_rate(result) == 0.0


def test_regression_rate():
    result = _make_result(8, 10, regressions=2)
    assert regression_rate(result) == pytest.approx(0.2)


def test_tool_efficiency_score_zero_calls():
    sub = _make_sub(tool_calls=0)
    assert tool_efficiency_score(sub) == pytest.approx(1.0)


def test_tool_efficiency_score_max_calls():
    sub = _make_sub(tool_calls=20)
    assert tool_efficiency_score(sub, max_tool_calls=20) == pytest.approx(0.0)


def test_cost_adjusted_score():
    score = cost_adjusted_score(1.0, math.e - 1)  # log1p(e-1) == 1.0
    assert score == pytest.approx(1.0)


def test_leaderboard_sorted():
    results = [
        _make_result(5, 10, agent="anote-code"),
        _make_result(9, 10, agent="claude-code"),
    ]
    subs = [
        _make_sub(agent="anote-code"),
        _make_sub(agent="claude-code"),
    ]
    board = leaderboard(results, subs)
    assert board[0]["agent"] == "claude-code"
    assert board[1]["agent"] == "anote-code"
