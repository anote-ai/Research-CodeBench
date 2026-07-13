"""Convert official SWE-bench harness reports into CodeBench metrics.

The harness (``python -m swebench.harness.run_evaluation``) produces, per run:

- a summary JSON ``{model}.{run_id}.json`` in the invocation directory, with
  id lists such as ``resolved_ids``, ``unresolved_ids``, ``error_ids``, and
  ``empty_patch_ids``;
- per-instance reports at
  ``logs/run_evaluation/{run_id}/{model}/{instance_id}/report.json`` with a
  ``tests_status`` breakdown of FAIL_TO_PASS / PASS_TO_PASS outcomes.

Each evaluated (instance, run) becomes one :class:`ExecutionResult` rollout:

- ``tests_total``       = |FAIL_TO_PASS| + |PASS_TO_PASS|
- ``tests_passed``      = successes across both groups
- ``regression_count``  = PASS_TO_PASS failures
- ``execution_success`` = the instance was resolved

With one harness run per attempt index, the pooled results are exactly the
rollout shape :func:`codebench.evaluate.reliability_at_k` consumes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from .core import ExecutionResult
from .evaluate import regression_rate, reliability_at_k

DEFAULT_LOGS_DIR = "logs/run_evaluation"


def load_harness_summary(summary_path: Union[str, Path]) -> Dict[str, Any]:
    """Load a harness summary JSON (``{model}.{run_id}.json``)."""
    return json.loads(Path(summary_path).read_text(encoding="utf-8"))


def _instance_report_path(
    logs_dir: Union[str, Path], run_id: str, model_name: str, instance_id: str
) -> Path:
    # The harness sanitizes "/" in model names when building directories.
    safe_model = model_name.replace("/", "__")
    return Path(logs_dir) / run_id / safe_model / instance_id / "report.json"


def _result_from_instance_report(
    instance_id: str,
    model_name: str,
    report: Dict[str, Any],
) -> ExecutionResult:
    entry = report.get(instance_id, report)
    status = entry.get("tests_status", {})
    f2p = status.get("FAIL_TO_PASS", {})
    p2p = status.get("PASS_TO_PASS", {})
    f2p_pass = len(f2p.get("success", []))
    f2p_fail = len(f2p.get("failure", []))
    p2p_pass = len(p2p.get("success", []))
    p2p_fail = len(p2p.get("failure", []))
    return ExecutionResult(
        task_id=instance_id,
        agent_name=model_name,
        tests_passed=f2p_pass + p2p_pass,
        tests_total=f2p_pass + f2p_fail + p2p_pass + p2p_fail,
        regression_count=p2p_fail,
        execution_success=bool(entry.get("resolved", False)),
    )


def harness_report_to_execution_results(
    summary_path: Union[str, Path],
    run_id: str,
    model_name: str,
    logs_dir: Union[str, Path] = DEFAULT_LOGS_DIR,
) -> List[ExecutionResult]:
    """Convert one harness run into ExecutionResult rollouts.

    Instances without a per-instance report (errored or empty-patch attempts)
    become zero-score rollouts with ``execution_success=False``, so failed
    attempts still count toward reliability@k denominators.
    """
    summary = load_harness_summary(summary_path)
    instance_ids: List[str] = sorted(
        set(summary.get("resolved_ids", []))
        | set(summary.get("unresolved_ids", []))
        | set(summary.get("error_ids", []))
        | set(summary.get("empty_patch_ids", []))
    )

    results: List[ExecutionResult] = []
    resolved = set(summary.get("resolved_ids", []))
    for instance_id in instance_ids:
        report_path = _instance_report_path(logs_dir, run_id, model_name, instance_id)
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            results.append(_result_from_instance_report(instance_id, model_name, report))
        else:
            results.append(
                ExecutionResult(
                    task_id=instance_id,
                    agent_name=model_name,
                    tests_passed=0,
                    tests_total=0,
                    regression_count=0,
                    execution_success=instance_id in resolved,
                )
            )
    return results


def aggregate_swebench_results(
    results: List[ExecutionResult],
    k: int = 5,
) -> Dict[str, Any]:
    """Aggregate pooled rollouts into CodeBench headline metrics."""
    n = len(results)
    tasks = sorted({r.task_id for r in results})
    resolved_rollouts = sum(1 for r in results if r.execution_success)
    return {
        "n_rollouts": n,
        "n_tasks": len(tasks),
        "resolved_rollouts": resolved_rollouts,
        "resolve_rate": resolved_rollouts / max(n, 1),
        "mean_pass_rate": sum(r.pass_rate for r in results) / max(n, 1),
        "mean_regression_rate": sum(regression_rate(r) for r in results) / max(n, 1),
        f"reliability@{k}": reliability_at_k(results, k=k),
        "tasks": tasks,
    }
