#!/usr/bin/env python3
"""Experiment 0: Baseline pipeline validation.

This is the first "real" experiment script in the repository, in the sense
that it actually executes code and measures real outcomes rather than
drawing from a seeded random number generator.

What it does
------------
For each of the 10 hand-written tasks in ``codebench.data.SAMPLE_TASKS``, it

1. Loads the task's ``reference_solution`` source.
2. Executes that source in a fresh namespace (i.e. actually runs the code).
3. Runs a small set of smoke-test assertions appropriate to that task
   (defined in ``_SMOKE_TESTS`` below) against the executed namespace.
4. Builds a real ``ExecutionResult`` from the smoke-test outcomes (not a
   synthetic/random one).
5. Computes ``security_score`` on the actual reference solution source.
6. Aggregates pass@1 / pass@5 via the existing ``codebench.evaluate``
   metrics and writes ``results/exp0_baseline.json``.

What it intentionally does NOT do
----------------------------------
It does not call any external LLM API, and it does not produce SSR / SGR /
CIR numbers as defined in DESIGN_DOC.md — those require a security-scanner
integration, a semantic oracle, and a repo-context harness that do not exist
yet. Treat this script's output as a pipeline-validation artifact, not as a
research result about any coding assistant's quality. See
``results/README.md`` and ``PAPER_DRAFT.md`` for the explicit status of
every number derived from this script.

Usage
-----
    python experiments/exp0_baseline.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Callable, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codebench.core import AgentSubmission, ExecutionResult  # noqa: E402
from codebench.data import SAMPLE_TASKS, make_task  # noqa: E402
from codebench.evaluate import leaderboard, security_score  # noqa: E402


def _smoke_test_task_001(ns: dict) -> int:
    fn = ns["parse_imports"]
    total = 2
    passed = 0
    if fn("import os\nimport sys") == ["os", "sys"]:
        passed += 1
    if fn("from collections import OrderedDict") == ["collections"]:
        passed += 1
    return passed, total


def _smoke_test_task_003(ns: dict) -> int:
    fn = ns["dijkstra"]
    graph = {"a": [("b", 1), ("c", 4)], "b": [("c", 2)], "c": []}
    total = 1
    passed = 1 if fn(graph, "a") == {"a": 0, "b": 1, "c": 3} else 0
    return passed, total


def _smoke_test_task_005(ns: dict) -> int:
    cls = ns["LRUCache"]
    c = cls(2)
    c.put(1, "a")
    c.put(2, "b")
    total = 3
    passed = 0
    if c.get(1) == "a":
        passed += 1
    c.put(3, "c")  # evicts key 2
    if c.get(2) == -1:
        passed += 1
    if c.get(3) == "c":
        passed += 1
    return passed, total


def _smoke_test_task_006(ns: dict) -> int:
    fn = ns["merge_sort"]
    total = 2
    passed = 0
    if fn([3, 1, 2]) == [1, 2, 3]:
        passed += 1
    if fn([]) == []:
        passed += 1
    return passed, total


def _smoke_test_task_009(ns: dict) -> int:
    fn = ns["knapsack"]
    total = 1
    passed = 1 if fn([1, 3, 4, 5], [1, 4, 5, 7], 7) == 9 else 0
    return passed, total


# Only tasks with a registered smoke test are included in this experiment.
# Tasks without an entry here are skipped (and reported as skipped), rather
# than silently scored with a fabricated pass rate.
_SMOKE_TESTS: Dict[str, Callable[[dict], tuple]] = {
    "task-001": _smoke_test_task_001,
    "task-003": _smoke_test_task_003,
    "task-005": _smoke_test_task_005,
    "task-006": _smoke_test_task_006,
    "task-009": _smoke_test_task_009,
}


def run() -> dict:
    agent_name = "reference-solution"
    results = []
    submissions = []
    skipped = []

    for i, raw in enumerate(SAMPLE_TASKS):
        task = make_task(i)
        test_fn = _SMOKE_TESTS.get(task.task_id)
        if test_fn is None:
            skipped.append(task.task_id)
            continue

        ns: dict = {}
        try:
            exec(task.reference_solution, ns)  # noqa: S102 - intentional, controlled execution of repo-local reference code
            passed, total = test_fn(ns)
            success = True
        except Exception as exc:  # pragma: no cover - defensive
            passed, total = 0, 1
            success = False
            print(f"[exp0] {task.task_id} raised {exc!r}", file=sys.stderr)

        result = ExecutionResult(
            task_id=task.task_id,
            agent_name=agent_name,
            tests_passed=passed,
            tests_total=total,
            regression_count=0,
            execution_success=success and passed == total,
        )
        results.append(result)
        submissions.append(AgentSubmission(
            task_id=task.task_id,
            agent_name=agent_name,
            generated_code=task.reference_solution,
            tool_calls_used=0,
            latency_ms=0.0,
            cost_usd=0.0,
        ))

    board = leaderboard(results, submissions)
    sec_scores = {
        t["task_id"]: security_score(t["reference_solution"])
        for t in SAMPLE_TASKS
        if t["task_id"] in _SMOKE_TESTS
    }

    report = {
        "experiment": "exp0_baseline",
        "description": (
            "Pipeline validation: executes real reference-solution code "
            "through the codebench harness. NOT a measurement of any "
            "LLM's coding ability — see results/README.md."
        ),
        "agent": agent_name,
        "n_tasks_evaluated": len(results),
        "n_tasks_skipped_no_smoke_test": len(skipped),
        "skipped_task_ids": skipped,
        "leaderboard": board,
        "security_score_by_task": sec_scores,
    }
    return report


def main() -> None:
    report = run()
    out_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "exp0_baseline.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    print(f"\nWrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
