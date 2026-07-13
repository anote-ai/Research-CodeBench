"""Tests for codebench.swebench_results (fixture harness reports, offline)."""

import json

import pytest

from codebench.core import ExecutionResult
from codebench.swebench_results import (
    aggregate_swebench_results,
    harness_report_to_execution_results,
)

MODEL = "anote-code"
RUN_ID = "v1-attempt1"


def write_fixture_run(tmp_path, model=MODEL, run_id=RUN_ID):
    """Build a fake harness output tree: summary + per-instance reports."""
    summary = {
        "resolved_ids": ["acme__widget-1"],
        "unresolved_ids": ["acme__widget-2"],
        "error_ids": ["acme__widget-3"],
        "empty_patch_ids": [],
    }
    summary_path = tmp_path / f"{model}.{run_id}.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    logs_dir = tmp_path / "logs" / "run_evaluation"
    reports = {
        "acme__widget-1": {
            "resolved": True,
            "tests_status": {
                "FAIL_TO_PASS": {"success": ["t1", "t2"], "failure": []},
                "PASS_TO_PASS": {"success": ["t3", "t4", "t5"], "failure": ["t6"]},
            },
        },
        "acme__widget-2": {
            "resolved": False,
            "tests_status": {
                "FAIL_TO_PASS": {"success": [], "failure": ["t1", "t2"]},
                "PASS_TO_PASS": {"success": ["t3", "t4", "t5", "t6"], "failure": []},
            },
        },
        # acme__widget-3 errored: no report.json on purpose
    }
    for instance_id, report in reports.items():
        report_dir = logs_dir / run_id / model / instance_id
        report_dir.mkdir(parents=True)
        (report_dir / "report.json").write_text(
            json.dumps({instance_id: report}), encoding="utf-8"
        )
    return summary_path, logs_dir


def test_field_mapping_from_instance_report(tmp_path):
    summary_path, logs_dir = write_fixture_run(tmp_path)
    results = harness_report_to_execution_results(
        summary_path, run_id=RUN_ID, model_name=MODEL, logs_dir=logs_dir
    )
    by_id = {r.task_id: r for r in results}
    assert set(by_id) == {"acme__widget-1", "acme__widget-2", "acme__widget-3"}

    resolved = by_id["acme__widget-1"]
    assert resolved.agent_name == MODEL
    assert resolved.tests_total == 6          # 2 F2P + 4 P2P
    assert resolved.tests_passed == 5         # 2 F2P + 3 P2P successes
    assert resolved.regression_count == 1     # 1 P2P failure
    assert resolved.execution_success is True

    unresolved = by_id["acme__widget-2"]
    assert unresolved.tests_total == 6
    assert unresolved.tests_passed == 4
    assert unresolved.regression_count == 0
    assert unresolved.execution_success is False


def test_missing_report_becomes_zero_rollout(tmp_path):
    summary_path, logs_dir = write_fixture_run(tmp_path)
    results = harness_report_to_execution_results(
        summary_path, run_id=RUN_ID, model_name=MODEL, logs_dir=logs_dir
    )
    errored = {r.task_id: r for r in results}["acme__widget-3"]
    assert errored.tests_total == 0
    assert errored.tests_passed == 0
    assert errored.execution_success is False
    assert errored.pass_rate == 0.0


def test_model_name_with_slash_is_sanitized(tmp_path):
    model = "org/model"
    summary_path, logs_dir = write_fixture_run(tmp_path, model="org__model")
    results = harness_report_to_execution_results(
        summary_path, run_id=RUN_ID, model_name=model, logs_dir=logs_dir
    )
    # reports live under the sanitized dir but agent_name keeps the real name
    assert all(r.agent_name == model for r in results)
    assert any(r.tests_total > 0 for r in results)


def make_rollout(task_id, success):
    return ExecutionResult(
        task_id=task_id,
        agent_name=MODEL,
        tests_passed=6 if success else 3,
        tests_total=6,
        regression_count=0 if success else 1,
        execution_success=success,
    )


def test_aggregate_reliability_over_pooled_attempts():
    # one task, 3 attempts (harness runs), 2 resolved
    rollouts = [
        make_rollout("acme__widget-1", True),
        make_rollout("acme__widget-1", True),
        make_rollout("acme__widget-1", False),
    ]
    agg = aggregate_swebench_results(rollouts, k=1)
    assert agg["n_rollouts"] == 3
    assert agg["n_tasks"] == 1
    assert agg["resolved_rollouts"] == 2
    assert agg["reliability@1"] == pytest.approx(2 / 3)   # pass_at_k(3, 2, 1)
    agg3 = aggregate_swebench_results(rollouts, k=3)
    assert agg3["reliability@3"] == 1.0            # pass_at_k(3, 2, 3)


def test_aggregate_empty_results():
    agg = aggregate_swebench_results([], k=5)
    assert agg["n_rollouts"] == 0
    assert agg["reliability@5"] == 0.0
