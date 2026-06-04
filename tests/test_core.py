"""Tests for codebench.core."""

import pytest

from codebench.core import (
    AGENT_NAMES,
    AgentSubmission,
    CodeTask,
    ExecutionResult,
    TaskDifficulty,
    pass_at_k,
)


def test_task_difficulty_values():
    assert TaskDifficulty.EASY == "easy"
    assert TaskDifficulty.MEDIUM == "medium"
    assert TaskDifficulty.HARD == "hard"


def test_code_task_construction():
    task = CodeTask(
        task_id="t001",
        repo="my-org/my-repo",
        description="Implement a sort function.",
        difficulty=TaskDifficulty.MEDIUM,
        test_file="tests/test_sort.py",
        reference_solution="def sort(lst): return sorted(lst)",
    )
    assert task.task_id == "t001"
    assert task.difficulty == TaskDifficulty.MEDIUM


def test_agent_submission_construction():
    sub = AgentSubmission(
        task_id="t001",
        agent_name="anote-code",
        generated_code="def sort(lst): return sorted(lst)",
        tool_calls_used=3,
        latency_ms=500.0,
        cost_usd=0.05,
    )
    assert sub.agent_name == "anote-code"
    assert sub.tool_calls_used == 3


def test_execution_result_construction():
    result = ExecutionResult(
        task_id="t001",
        agent_name="claude-code",
        tests_passed=8,
        tests_total=10,
        regression_count=1,
        execution_success=True,
    )
    assert result.tests_passed == 8
    assert result.execution_success is True


def test_agent_names_contains_expected():
    assert "anote-code" in AGENT_NAMES
    assert "claude-code" in AGENT_NAMES
    assert "codex" in AGENT_NAMES
    assert len(AGENT_NAMES) == 5


def test_pass_at_k_between_zero_and_one():
    value = pass_at_k(n=10, c=5, k=3)
    assert 0.0 < value < 1.0


def test_pass_at_k_all_correct():
    # All correct => pass@k == 1.0
    value = pass_at_k(n=10, c=10, k=3)
    assert value == pytest.approx(1.0)


def test_pass_at_k_none_correct():
    # None correct => pass@k == 0.0
    value = pass_at_k(n=10, c=0, k=3)
    assert value == pytest.approx(0.0)


def test_pass_at_k_zero_samples():
    assert pass_at_k(n=0, c=0, k=1) == 0.0
