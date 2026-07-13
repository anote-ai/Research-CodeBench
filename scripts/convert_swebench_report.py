#!/usr/bin/env python3
"""Convert official SWE-bench harness reports into CodeBench metrics.

Pools one or more harness runs (one per attempt index) into ExecutionResult
rollouts, computes reliability@k / pass-rate / regression aggregates, and
writes a versioned results JSON.

Usage:
    python scripts/convert_swebench_report.py \\
        --run-ids v1-attempt1 v1-attempt2 v1-attempt3 \\
        --model-name anote-code -k 3 \\
        --output data/swebench_results_anote-code_v1.json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codebench.swebench_results import (
    DEFAULT_LOGS_DIR,
    aggregate_swebench_results,
    harness_report_to_execution_results,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-ids", nargs="+", required=True,
        help="Harness run ids to pool (one per attempt index)",
    )
    parser.add_argument("--model-name", required=True, help="model_name_or_path used in the runs")
    parser.add_argument("-k", type=int, default=5, help="k for reliability@k (default: 5)")
    parser.add_argument(
        "--summary-dir", default=".",
        help="Directory holding {model}.{run_id}.json summaries (default: cwd)",
    )
    parser.add_argument(
        "--logs-dir", default=DEFAULT_LOGS_DIR,
        help=f"Harness evaluation logs dir (default: {DEFAULT_LOGS_DIR})",
    )
    parser.add_argument("--output", default=None, help="Results JSON output path")
    args = parser.parse_args()

    safe_model = args.model_name.replace("/", "__")
    all_results = []
    per_run = {}
    for run_id in args.run_ids:
        summary_path = os.path.join(args.summary_dir, f"{safe_model}.{run_id}.json")
        if not os.path.exists(summary_path):
            sys.exit(f"error: harness summary not found: {summary_path}")
        results = harness_report_to_execution_results(
            summary_path=summary_path,
            run_id=run_id,
            model_name=args.model_name,
            logs_dir=args.logs_dir,
        )
        per_run[run_id] = {
            "n_instances": len(results),
            "resolved": sum(1 for r in results if r.execution_success),
        }
        all_results.extend(results)

    aggregates = aggregate_swebench_results(all_results, k=args.k)

    print(f"Model: {args.model_name}   runs: {', '.join(args.run_ids)}")
    for run_id, stats in per_run.items():
        print(f"  {run_id}: {stats['resolved']}/{stats['n_instances']} resolved")
    print(f"reliability@{args.k}:     {aggregates[f'reliability@{args.k}']:.4f}")
    print(f"resolve rate:         {aggregates['resolve_rate']:.4f}")
    print(f"mean pass rate:       {aggregates['mean_pass_rate']:.4f}")
    print(f"mean regression rate: {aggregates['mean_regression_rate']:.4f}")

    if args.output:
        payload = {
            "model": args.model_name,
            "run_ids": args.run_ids,
            "k": args.k,
            "per_run": per_run,
            "aggregates": aggregates,
            "rollouts": [r.model_dump(mode="json") for r in all_results],
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"\nWrote results to {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()
