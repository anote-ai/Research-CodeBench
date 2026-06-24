"""Tests for codebench.evaluate."""

import pytest
from codebench.core import AgentSubmission, ExecutionResult
from codebench.evaluate import (
    agent_summary,
    cost_adjusted_score,
    leaderboard,
    pass_rate,
    regression_rate,
    reliability_at_k,
    security_score,
    single_rollout_proxy,
    tool_efficiency_score,
)


def _result(passed=8, total=10, reg=1, agent="a", task="t1"):
    return ExecutionResult(
        task_id=task,
        agent_name=agent,
        tests_passed=passed,
        tests_total=total,
        regression_count=reg,
        execution_success=True,
    )


def _sub(agent="a", task="t1", tool_calls=5, latency=500.0, cost=0.01):
    return AgentSubmission(
        task_id=task,
        agent_name=agent,
        generated_code="pass",
        tool_calls_used=tool_calls,
        latency_ms=latency,
        cost_usd=cost,
    )


def test_test_pass_rate():
    r = _result(passed=8, total=10)
    assert pass_rate(r) == pytest.approx(0.8)


def test_regression_rate():
    r = _result(reg=2, total=10)
    assert regression_rate(r) == pytest.approx(0.2)


def test_tool_efficiency_score_at_max():
    s = _sub(tool_calls=20)
    assert tool_efficiency_score(s, max_tool_calls=20) == pytest.approx(0.0)


def test_tool_efficiency_score_over_budget():
    s = _sub(tool_calls=25)
    assert tool_efficiency_score(s, max_tool_calls=20) == pytest.approx(0.0)


def test_cost_adjusted_score():
    val = cost_adjusted_score(1.0, 0.0)
    assert val > 0


def test_agent_summary_structure():
    results = [_result(agent="a"), _result(agent="b")]
    subs = [_sub(agent="a"), _sub(agent="b")]
    summary = agent_summary(results, subs)
    assert "a" in summary
    assert "mean_pass_rate" in summary["a"]
    assert "n_tasks" in summary["a"]


def test_leaderboard_sorted_descending():
    results = [
        _result(passed=10, total=10, agent="best"),
        _result(passed=2, total=10, agent="worst"),
    ]
    subs = [_sub(agent="best"), _sub(agent="worst")]
    board = leaderboard(results, subs)
    assert board[0]["agent"] == "best"
    assert board[0]["mean_pass_rate"] >= board[1]["mean_pass_rate"]


def test_security_score_clean_code():
    code = "def add(a, b):\n    return a + b\n"
    assert security_score(code) == pytest.approx(1.0)


def test_security_score_eval_penalised():
    code = "result = eval(user_input)"
    score = security_score(code)
    assert score < 1.0


def test_security_score_os_system_penalised():
    code = "import os\nos.system('rm -rf /')"
    score = security_score(code)
    assert score < 1.0


def test_security_score_empty_code():
    assert security_score("") == pytest.approx(1.0)


def test_security_score_multiple_issues():
    code = "eval(x); exec(y)"
    score_multi = security_score(code)
    code_single = "eval(x)"
    score_single = security_score(code_single)
    assert score_multi <= score_single


# --- H1: category-error proof ---

def test_h1_current_passk_sensitive_to_tests_total():
    """Regression test proving the category error in _estimate_pass_at_k.

    Two agents have identical true reliability (60% per-attempt success rate)
    but different tests_total. The current formula should yield different pass@5
    values — demonstrating it measures test granularity, not agent reliability.
    """
    from codebench.evaluate import _estimate_pass_at_k

    # Agent A: 4 of 10 unit tests pass — 40% pass rate, tests_total=10
    result_a = _result(passed=4, total=10, agent="agent-a")
    # Agent B: same 40% rate but only 2 of 5 unit tests, tests_total=5
    result_b = _result(passed=2, total=5, agent="agent-b")

    pass_at_5_a = _estimate_pass_at_k([result_a], k=5)
    pass_at_5_b = _estimate_pass_at_k([result_b], k=5)

    # Values differ despite identical true reliability — the category error
    assert pass_at_5_a != pytest.approx(pass_at_5_b), (
        "Current pass@k should differ for same reliability but different tests_total "
        "(category error). If this fails, the bug has been fixed — remove this test."
    )


# --- reliability@k tests ---

def _rollout(passed: int, total: int, success: bool, agent: str = "a", task: str = "t1") -> ExecutionResult:
    return ExecutionResult(
        task_id=task,
        agent_name=agent,
        tests_passed=passed,
        tests_total=total,
        regression_count=0,
        execution_success=success,
    )


def test_reliability_at_k_perfect_agent():
    """Agent that always fully passes should have reliability@k = 1.0."""
    results = [_rollout(10, 10, True, agent="a", task="t1") for _ in range(10)]
    assert reliability_at_k(results, k=5) == pytest.approx(1.0)


def test_reliability_at_k_zero_agent():
    """Agent that never fully passes should have reliability@k = 0.0."""
    results = [_rollout(5, 10, False, agent="a", task="t1") for _ in range(10)]
    assert reliability_at_k(results, k=5) == pytest.approx(0.0)


def test_reliability_at_k_differs_from_current_passk():
    """reliability@k uses rollout-level success, not per-test counts — values must differ."""
    from codebench.evaluate import _estimate_pass_at_k

    # 10 rollouts: 4 fully succeed, 6 partially pass
    results = (
        [_rollout(10, 10, True,  agent="a", task="t1")] * 4
        + [_rollout(3, 10, False, agent="a", task="t1")] * 6
    )
    new = reliability_at_k(results, k=5)
    old = _estimate_pass_at_k(results, k=5)
    assert new != pytest.approx(old), (
        "reliability@k and current pass@k should differ because they use "
        "different quantities as n and c."
    )


def test_reliability_at_k_groups_by_task_and_agent():
    """Results from different tasks/agents should be grouped independently."""
    r_t1 = [_rollout(10, 10, True, agent="a", task="t1")] * 5
    r_t2 = [_rollout(0, 10, False, agent="a", task="t2")] * 5
    score = reliability_at_k(r_t1 + r_t2, k=5)
    # t1 perfect (1.0), t2 zero (0.0) → average ≈ 0.5
    assert 0.4 < score < 0.6


# --- single_rollout_proxy tests ---

def test_single_rollout_proxy_range():
    r = _result(passed=8, total=10, reg=1, agent="a")
    s = _sub(agent="a", tool_calls=10)
    score = single_rollout_proxy(r, s)
    assert 0.0 <= score <= 1.0


def test_single_rollout_proxy_penalises_regressions():
    r_clean = _result(passed=8, total=10, reg=0, agent="a")
    r_regressed = _result(passed=8, total=10, reg=3, agent="a")
    s = _sub(agent="a", tool_calls=5)
    assert single_rollout_proxy(r_clean, s) > single_rollout_proxy(r_regressed, s)
