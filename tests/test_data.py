"""Tests for codebench.data."""

import pytest
from codebench.data import SAMPLE_TASKS, make_benchmark, make_submission, make_task
from codebench.core import BenchmarkHarness, CodeTask


def test_sample_tasks_length():
    assert len(SAMPLE_TASKS) == 5


def test_make_task_returns_code_task():
    t = make_task(0)
    assert isinstance(t, CodeTask)
    assert t.task_id == "task-001"


def test_make_submission_structure():
    sub, res = make_submission("t1", pass_rate=0.9)
    assert sub.task_id == "t1"
    assert res.task_id == "t1"
    assert res.tests_passed == 9


def test_make_benchmark_returns_harness():
    h = make_benchmark(n_tasks=5, agents=["a", "b"])
    assert isinstance(h, BenchmarkHarness)
    assert len(h.tasks) == 5
    assert len(h.results) == 10  # 5 tasks * 2 agents
