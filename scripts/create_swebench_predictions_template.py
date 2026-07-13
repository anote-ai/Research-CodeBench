#!/usr/bin/env python3
"""Create an empty SWE-bench predictions JSONL template from a task sample.

Reads the sampled tasks (see prepare_swebench_sample.py) and writes one
prediction stub per task in the official SWE-bench harness format:
instance_id, model_name_or_path, model_patch (empty by default).

Usage:
    python scripts/create_swebench_predictions_template.py
    python scripts/create_swebench_predictions_template.py --model-name my-agent
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codebench.swebench_adapter import read_swebench_sample, write_predictions_jsonl

DEFAULT_INPUT = os.path.join(
    os.path.dirname(__file__), "..", "data", "swebench_verified_sample.jsonl"
)
DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(__file__), "..", "predictions", "swebench_predictions_template.jsonl"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help="Sampled task JSONL (default: data/swebench_verified_sample.jsonl)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Template JSONL path (default: predictions/swebench_predictions_template.jsonl)",
    )
    parser.add_argument(
        "--model-name",
        default="anote-code",
        help="Value for model_name_or_path in each stub (default: anote-code)",
    )
    args = parser.parse_args()

    records = read_swebench_sample(args.input)
    predictions = [
        {
            "instance_id": record["task"]["task_id"],
            "model_name_or_path": args.model_name,
            "model_patch": "",
        }
        for record in records
    ]
    path = write_predictions_jsonl(predictions, args.output)
    print(f"Wrote {len(predictions)} prediction stubs to {os.path.abspath(path)}")


if __name__ == "__main__":
    main()
