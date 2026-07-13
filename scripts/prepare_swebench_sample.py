#!/usr/bin/env python3
"""Sample SWE-bench Verified into a CodeBench task file.

Loads SWE-bench/SWE-bench_Verified from Hugging Face and writes a small
JSONL sample (default 5 tasks) to data/swebench_verified_sample.jsonl.

Usage:
    python scripts/prepare_swebench_sample.py
    python scripts/prepare_swebench_sample.py --limit 30 --difficulty easy
    python scripts/prepare_swebench_sample.py --limit 50 --output data/my_sample.jsonl
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codebench.swebench_adapter import write_swebench_sample

DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(__file__), "..", "data", "swebench_verified_sample.jsonl"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of tasks to sample (default: 5; try 30 or 50 for larger runs)",
    )
    parser.add_argument(
        "--difficulty",
        default=None,
        help="Filter by difficulty: easy/medium/hard or a raw SWE-bench label",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Output JSONL path (default: data/swebench_verified_sample.jsonl)",
    )
    parser.add_argument(
        "--split",
        default="test",
        help="Dataset split (default: test)",
    )
    args = parser.parse_args()

    records = write_swebench_sample(
        output_path=args.output,
        limit=args.limit,
        difficulty=args.difficulty,
        split=args.split,
    )
    print(f"Wrote {len(records)} SWE-bench Verified tasks to {os.path.abspath(args.output)}")
    for record in records:
        task = record["task"]
        print(f"  - {task['task_id']} ({task['difficulty']}) {task['repo']}")


if __name__ == "__main__":
    main()
