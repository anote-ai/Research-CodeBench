#!/usr/bin/env python3
"""Demo script: create a benchmark and print the leaderboard."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codebench.data import make_benchmark
from codebench.evaluate import leaderboard

try:
    from rich.table import Table
    from rich.console import Console
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def main() -> None:
    agents = ["anote-code", "claude-code", "codex"]
    harness = make_benchmark(n_tasks=10, agents=agents, seed=42)

    board = leaderboard(harness.results, harness.submissions)

    if HAS_RICH:
        console = Console()
        table = Table(title="CodeBench Leaderboard")
        table.add_column("Rank", justify="right")
        table.add_column("Agent")
        table.add_column("Pass@1", justify="right")
        table.add_column("Pass@5", justify="right")
        table.add_column("Latency (ms)", justify="right")
        table.add_column("Cost (USD)", justify="right")
        table.add_column("Tasks", justify="right")
        for rank, row in enumerate(board, 1):
            table.add_row(
                str(rank),
                row["agent"],
                f"{row['pass@1']:.3f}",
                f"{row['pass@5']:.3f}",
                f"{row['mean_latency_ms']:.0f}",
                f"{row['mean_cost_usd']:.4f}",
                str(row["n_tasks"]),
            )
        console.print(table)
    else:
        print("Rank | Agent | Pass@1 | Pass@5 | Latency(ms) | Cost(USD) | Tasks")
        for rank, row in enumerate(board, 1):
            print(
                f"{rank} | {row['agent']} | {row['pass@1']:.3f} | "
                f"{row['pass@5']:.3f} | {row['mean_latency_ms']:.0f} | "
                f"{row['mean_cost_usd']:.4f} | {row['n_tasks']}"
            )


if __name__ == "__main__":
    main()
