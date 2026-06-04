"""Core data models and utilities for codebench."""

from __future__ import annotations

import math
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class TaskDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TestCategory(str, Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    EDGE_CASE = "edge_case"


class CodeTask(BaseModel):
    task_id: str
    repo: str
    description: str
    difficulty: TaskDifficulty
    test_file: str
    reference_solution: str
    tags: List[str] = Field(default_factory=list)


class AgentSubmission(BaseModel):
    task_id: str
    agent_name: str
    generated_code: str
    tool_calls_used: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    cost_usd: float = Field(ge=0)


class TestResult(BaseModel):
    """Result for a single test case within a suite."""

    test_name: str
    category: TestCategory
    passed: bool
    execution_time_ms: float = Field(ge=0, default=0.0)
    error_message: Optional[str] = None


class TestSuite(BaseModel):
    """A collection of test results grouped by category."""

    task_id: str
    agent_name: str
    test_results: List[TestResult] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_test_results(self) -> "TestSuite":
        return self

    def results_by_category(self) -> Dict[str, List[TestResult]]:
        """Group test results by their category."""
        grouped: Dict[str, List[TestResult]] = {}
        for tr in self.test_results:
            grouped.setdefault(tr.category.value, []).append(tr)
        return grouped

    def pass_rate_by_category(self) -> Dict[str, float]:
        """Pass rate (0-1) for each test category."""
        grouped = self.results_by_category()
        return {
            cat: sum(1 for t in tests if t.passed) / max(len(tests), 1)
            for cat, tests in grouped.items()
        }

    def overall_pass_rate(self) -> float:
        """Overall fraction of tests passed."""
        if not self.test_results:
            return 0.0
        return sum(1 for t in self.test_results if t.passed) / len(self.test_results)

    def edge_case_pass_rate(self) -> float:
        """Pass rate restricted to edge_case tests."""
        ec = [t for t in self.test_results if t.category == TestCategory.EDGE_CASE]
        if not ec:
            return 0.0
        return sum(1 for t in ec if t.passed) / len(ec)

    def total_tests(self) -> int:
        return len(self.test_results)

    def tests_passed(self) -> int:
        return sum(1 for t in self.test_results if t.passed)


class ExecutionResult(BaseModel):
    task_id: str
    agent_name: str
    tests_passed: int
    tests_total: int
    regression_count: int = Field(default=0, ge=0)
    execution_success: bool

    @property
    def pass_rate(self) -> float:
        return self.tests_passed / max(self.tests_total, 1)


class ComplexityScore(BaseModel):
    """Cyclomatic-complexity-inspired scoring for a submitted solution."""

    task_id: str
    agent_name: str
    cyclomatic_complexity: int = Field(ge=1)
    lines_of_code: int = Field(ge=0)
    n_functions: int = Field(ge=0)

    @property
    def average_function_length(self) -> float:
        return self.lines_of_code / max(self.n_functions, 1)

    @property
    def complexity_rating(self) -> str:
        """Human-readable complexity band."""
        if self.cyclomatic_complexity <= 5:
            return "low"
        if self.cyclomatic_complexity <= 10:
            return "moderate"
        if self.cyclomatic_complexity <= 20:
            return "high"
        return "very_high"


AGENT_NAMES: List[str] = [
    "anote-code",
    "claude-code",
    "codex",
    "gemini-code",
    "copilot",
]


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased estimator of pass@k.

    Args:
        n: total number of samples
        c: number of correct samples
        k: k in pass@k

    Returns:
        Probability of at least one correct sample in k draws.
    """
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


class BenchmarkHarness:
    """Holds tasks, submissions, and results for a benchmark run."""

    def __init__(self) -> None:
        self.tasks: List[CodeTask] = []
        self.submissions: List[AgentSubmission] = []
        self.results: List[ExecutionResult] = []
        self.test_suites: List[TestSuite] = []
        self.complexity_scores: List[ComplexityScore] = []

    def add_task(self, task: CodeTask) -> None:
        self.tasks.append(task)

    def add_submission(self, submission: AgentSubmission) -> None:
        self.submissions.append(submission)

    def add_result(self, result: ExecutionResult) -> None:
        self.results.append(result)

    def add_test_suite(self, suite: TestSuite) -> None:
        self.test_suites.append(suite)

    def add_complexity_score(self, score: ComplexityScore) -> None:
        self.complexity_scores.append(score)

    def get_results_for_agent(self, agent_name: str) -> List[ExecutionResult]:
        return [r for r in self.results if r.agent_name == agent_name]

    def get_results_for_task(self, task_id: str) -> List[ExecutionResult]:
        return [r for r in self.results if r.task_id == task_id]

    def get_suites_for_agent(self, agent_name: str) -> List[TestSuite]:
        return [s for s in self.test_suites if s.agent_name == agent_name]
