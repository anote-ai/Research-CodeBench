"""Core data models and utilities for codebench."""

from __future__ import annotations

import math
from enum import Enum
from typing import List

from pydantic import BaseModel, Field, model_validator


class TaskDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


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

    def add_task(self, task: CodeTask) -> None:
        self.tasks.append(task)

    def add_submission(self, submission: AgentSubmission) -> None:
        self.submissions.append(submission)

    def add_result(self, result: ExecutionResult) -> None:
        self.results.append(result)

    def get_results_for_agent(self, agent_name: str) -> List[ExecutionResult]:
        return [r for r in self.results if r.agent_name == agent_name]

    def get_results_for_task(self, task_id: str) -> List[ExecutionResult]:
        return [r for r in self.results if r.task_id == task_id]
