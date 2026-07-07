#!/usr/bin/env python3
"""
H4: Security-Adjusted Reliability — real agent code generation and evaluation.

Calls anote-code and claude-code (Anthropic) and codex (OpenAI GPT-4o) on all
10 SAMPLE_TASKS for N_ROLLOUTS each. Evaluates generated code for functional
correctness and security, then tests whether security-adjusted reliability
produces a different agent ranking (Kendall τ < 0.6).

Results are saved to data/h4_results.json so the figure can be regenerated
without re-calling the APIs.

Usage:
    python scripts/run_security_exp.py           # full run (240 API calls)
    python scripts/run_security_exp.py --plot    # regenerate figure from saved JSON
"""

import sys
import os
import re
import time
import json
import argparse
import unittest.mock as mock
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import kendalltau

import anthropic
import openai

from codebench.core import AgentSubmission, ExecutionResult
from codebench.data import SAMPLE_TASKS
from codebench.evaluate import (
    reliability_at_k,
    security_adjusted_reliability_at_k,
    security_score,
)

# ── Constants ──────────────────────────────────────────────────────────────────

AGENTS = ["anote-code", "claude-code", "codex"]
N_ROLLOUTS = 8
K = 5
SECURITY_THRESHOLD = 0.80
N_TESTS_PER_TASK = 5

_ROOT = os.path.join(os.path.dirname(__file__), "..")
RESULTS_PATH = os.path.join(_ROOT, "data", "h4_results.json")
OUT_DIR = os.path.join(_ROOT, "figures")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(os.path.join(_ROOT, "data"), exist_ok=True)

COLORS = {"reliability": "#55A868", "security_adj": "#C44E52"}
plt.rcParams.update({"font.size": 12, "axes.spines.top": False, "axes.spines.right": False})

# ── Agent configuration ────────────────────────────────────────────────────────

AGENT_CONFIGS = {
    "anote-code": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "system": (
            "You are Anote Code, a Python code generation assistant built by Anote AI. "
            "Return ONLY raw Python code — no markdown fences, no explanations. "
            "The code must be complete and immediately executable."
        ),
    },
    "claude-code": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "system": (
            "You are Claude Code, a Python coding assistant by Anthropic. "
            "Return ONLY raw Python code — no markdown fences, no explanations. "
            "The code must be complete and immediately executable."
        ),
    },
    "codex": {
        "provider": "openai",
        "model": "gpt-4o",
        "system": (
            "You are a Python coding assistant. "
            "Return ONLY raw Python code — no markdown fences, no explanations. "
            "The code must be complete and immediately executable."
        ),
    },
}

_anthropic_client = None
_openai_client = None


def get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _anthropic_client


def get_openai():
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _openai_client


# ── Code extraction ────────────────────────────────────────────────────────────

def extract_code(text: str) -> str:
    for pattern in [r"```python\n(.*?)```", r"```\n(.*?)```", r"```(.*?)```"]:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            return m.group(1).strip()
    return text.strip()


# ── Agent API calls ────────────────────────────────────────────────────────────

def call_agent(agent_name: str, description: str) -> Tuple[str, float, float]:
    """Returns (generated_code, latency_ms, cost_usd)."""
    cfg = AGENT_CONFIGS[agent_name]
    prompt = f"Implement the following in Python:\n\n{description}"
    t0 = time.time()

    if cfg["provider"] == "anthropic":
        resp = get_anthropic().messages.create(
            model=cfg["model"],
            max_tokens=1024,
            system=cfg["system"],
            messages=[{"role": "user", "content": prompt}],
        )
        code = extract_code(resp.content[0].text)
        # claude-sonnet-4-6: $3/M input tokens, $15/M output tokens
        cost = (resp.usage.input_tokens * 3 + resp.usage.output_tokens * 15) / 1_000_000
    else:
        resp = get_openai().chat.completions.create(
            model=cfg["model"],
            max_tokens=1024,
            messages=[
                {"role": "system", "content": cfg["system"]},
                {"role": "user", "content": prompt},
            ],
        )
        code = extract_code(resp.choices[0].message.content)
        # gpt-4o: $2.50/M input tokens, $10/M output tokens
        cost = (resp.usage.prompt_tokens * 2.5 + resp.usage.completion_tokens * 10) / 1_000_000

    return code, (time.time() - t0) * 1000, cost


# ── Test runner ────────────────────────────────────────────────────────────────

def _exec_code(code: str) -> dict:
    ns: dict = {"__builtins__": __builtins__}
    exec(compile(code, "<generated>", "exec"), ns)
    return ns


def run_tests(code: str, task_index: int) -> Tuple[int, int]:
    """Run task-specific tests against generated code. Returns (passed, total)."""
    tests = TASK_TESTS.get(task_index, [])
    if not tests:
        return 0, N_TESTS_PER_TASK

    # Patch time.sleep globally to prevent real sleeping in retry tests
    with mock.patch("time.sleep"):
        try:
            ns = _exec_code(code)
        except Exception:
            return 0, len(tests)

        passed = 0
        for fn in tests:
            try:
                if fn(ns):
                    passed += 1
            except Exception:
                pass

    return passed, len(tests)


# ── Test cases (5 per task, indexed 0–9 matching SAMPLE_TASKS) ────────────────

# Task 0: parse_imports
def _t0_1(ns): return sorted(ns["parse_imports"]("import os")) == ["os"]
def _t0_2(ns): return sorted(ns["parse_imports"]("import os\nimport sys")) == ["os", "sys"]
def _t0_3(ns): return sorted(ns["parse_imports"]("from collections import Counter")) == ["collections"]
def _t0_4(ns): return sorted(ns["parse_imports"]("import re\nfrom os.path import join")) == ["os.path", "re"]
def _t0_5(ns): return ns["parse_imports"]("x = 1 + 2") == []

# Task 1: DataPipeline
def _t1_1(ns): return "DataPipeline" in ns
def _t1_2(ns):
    dp = ns["DataPipeline"]()
    return hasattr(dp, "load") and hasattr(dp, "transform") and hasattr(dp, "save")
def _t1_3(ns):
    import pandas as pd, tempfile
    dp = ns["DataPipeline"]()
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        pd.DataFrame({"a": [1, 2]}).to_csv(f, index=False)
        name = f.name
    dp.load(name)
    return dp.df is not None
def _t1_4(ns):
    import pandas as pd, tempfile
    dp = ns["DataPipeline"]()
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        pd.DataFrame({"a": [1, 2, 3]}).to_csv(f, index=False)
        name = f.name
    return len(dp.load(name).transform(lambda df: df[df["a"] > 1]).df) == 2
def _t1_5(ns):
    import pandas as pd, tempfile
    dp = ns["DataPipeline"]()
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as fin:
        pd.DataFrame({"x": [1, 2]}).to_csv(fin, index=False)
        fin_name = fin.name
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as fout:
        out_name = fout.name
    dp.load(fin_name).save(out_name)
    return pd.read_csv(out_name).shape == (2, 1)

# Task 2: dijkstra
def _t2_1(ns):
    g = {"A": [("B", 1), ("C", 4)], "B": [("C", 2), ("D", 5)], "C": [("D", 1)], "D": []}
    return ns["dijkstra"](g, "A") == {"A": 0, "B": 1, "C": 3, "D": 4}
def _t2_2(ns): return ns["dijkstra"]({"A": [("B", 2)], "B": []}, "A") == {"A": 0, "B": 2}
def _t2_3(ns): return ns["dijkstra"]({"A": []}, "A").get("A") == 0
def _t2_4(ns):
    g = {"X": [("Y", 5)], "Y": [("Z", 3)], "Z": []}
    return ns["dijkstra"](g, "X") == {"X": 0, "Y": 5, "Z": 8}
def _t2_5(ns):
    g = {"A": [("B", 1), ("C", 10)], "B": [("C", 2)], "C": []}
    return ns["dijkstra"](g, "A")["C"] == 3

# Task 3: bm25
def _t3_1(ns):
    s = ns["bm25"]([["dog", "cat"], ["cat", "fish"]], ["cat"])
    return isinstance(s, list) and len(s) == 2
def _t3_2(ns):
    s = ns["bm25"]([["dog", "cat"], ["cat", "fish"]], ["cat"])
    return all(isinstance(x, float) for x in s)
def _t3_3(ns):
    s = ns["bm25"]([["the", "cat", "sat"], ["a", "dog", "ran"]], ["cat"])
    return s[0] > s[1]
def _t3_4(ns):
    s = ns["bm25"]([["apple", "apple"], ["banana"]], ["apple"])
    return s[0] > s[1]
def _t3_5(ns): return ns["bm25"]([["x"]], ["z"])[0] == 0.0

# Task 4: LRUCache
def _t4_1(ns): c = ns["LRUCache"](2); c.put(1, 1); return c.get(1) == 1
def _t4_2(ns): return ns["LRUCache"](1).get(99) == -1
def _t4_3(ns):
    c = ns["LRUCache"](2); c.put(1, 1); c.put(2, 2); c.put(3, 3); return c.get(1) == -1
def _t4_4(ns):
    c = ns["LRUCache"](2); c.put(1, 1); c.put(2, 2); c.get(1); c.put(3, 3); return c.get(2) == -1
def _t4_5(ns):
    c = ns["LRUCache"](2); c.put(1, 10); c.put(1, 20); return c.get(1) == 20

# Task 5: merge_sort
def _t5_1(ns): return ns["merge_sort"]([3, 1, 2]) == [1, 2, 3]
def _t5_2(ns): return ns["merge_sort"]([]) == []
def _t5_3(ns): return ns["merge_sort"]([1]) == [1]
def _t5_4(ns): return ns["merge_sort"]([5, 4, 3, 2, 1]) == [1, 2, 3, 4, 5]
def _t5_5(ns): return ns["merge_sort"]([2, 2, 1]) == [1, 2, 2]

# Task 6: Trie
def _t6_1(ns): t = ns["Trie"](); t.insert("apple"); return t.search("apple") is True
def _t6_2(ns): t = ns["Trie"](); t.insert("apple"); return t.search("app") is False
def _t6_3(ns): t = ns["Trie"](); t.insert("apple"); return t.starts_with("app") is True
def _t6_4(ns): return ns["Trie"]().search("x") is False
def _t6_5(ns):
    t = ns["Trie"](); t.insert("a"); t.insert("ab")
    return t.starts_with("a") and t.search("a")

# Task 7: retry decorator
def _t7_1(ns):
    calls = [0]
    @ns["retry"](max_attempts=3)
    def fn(): calls[0] += 1; return "ok"
    return fn() == "ok" and calls[0] == 1
def _t7_2(ns):
    calls = [0]
    @ns["retry"](max_attempts=3)
    def fn():
        calls[0] += 1
        if calls[0] < 3: raise ValueError()
        return "ok"
    return fn() == "ok" and calls[0] == 3
def _t7_3(ns):
    @ns["retry"](max_attempts=2)
    def fn(): raise RuntimeError("always")
    try: fn(); return False
    except RuntimeError: return True
def _t7_4(ns):
    @ns["retry"](max_attempts=3)
    def fn(): return 42
    return fn() == 42
def _t7_5(ns):
    @ns["retry"](max_attempts=1)
    def fn(): return "hello"
    return fn() == "hello"

# Task 8: knapsack
def _t8_1(ns): return ns["knapsack"]([1, 2, 3], [10, 20, 30], 5) == 50
def _t8_2(ns): return ns["knapsack"]([1, 2, 3], [10, 20, 30], 0) == 0
def _t8_3(ns): return ns["knapsack"]([5], [10], 4) == 0
def _t8_4(ns): return ns["knapsack"]([2, 3, 4, 5], [3, 4, 5, 6], 5) == 7
def _t8_5(ns): return ns["knapsack"]([1, 1, 1], [1, 2, 3], 2) == 5

# Task 9: MedianFinder
def _t9_1(ns): m = ns["MedianFinder"](); m.add(1); m.add(2); return m.get_median() == 1.5
def _t9_2(ns): m = ns["MedianFinder"](); [m.add(x) for x in [1, 2, 3]]; return m.get_median() == 2.0
def _t9_3(ns): m = ns["MedianFinder"](); m.add(5); return m.get_median() == 5.0
def _t9_4(ns): m = ns["MedianFinder"](); [m.add(x) for x in [3, 1, 2]]; return m.get_median() == 2.0
def _t9_5(ns): m = ns["MedianFinder"](); [m.add(x) for x in [1, 7, 3, 9]]; return m.get_median() == 5.0

TASK_TESTS: Dict[int, list] = {
    0: [_t0_1, _t0_2, _t0_3, _t0_4, _t0_5],
    1: [_t1_1, _t1_2, _t1_3, _t1_4, _t1_5],
    2: [_t2_1, _t2_2, _t2_3, _t2_4, _t2_5],
    3: [_t3_1, _t3_2, _t3_3, _t3_4, _t3_5],
    4: [_t4_1, _t4_2, _t4_3, _t4_4, _t4_5],
    5: [_t5_1, _t5_2, _t5_3, _t5_4, _t5_5],
    6: [_t6_1, _t6_2, _t6_3, _t6_4, _t6_5],
    7: [_t7_1, _t7_2, _t7_3, _t7_4, _t7_5],
    8: [_t8_1, _t8_2, _t8_3, _t8_4, _t8_5],
    9: [_t9_1, _t9_2, _t9_3, _t9_4, _t9_5],
}


# ── Data collection ────────────────────────────────────────────────────────────

def collect_rollouts() -> List[dict]:
    """Call all agents on all tasks for N_ROLLOUTS each. Returns list of records."""
    records = []
    total = len(SAMPLE_TASKS) * len(AGENTS) * N_ROLLOUTS
    done = 0

    for task_idx, task in enumerate(SAMPLE_TASKS):
        task_id = f"task-{task_idx:03d}"
        for agent in AGENTS:
            print(f"\n  [{agent}] {task_id}: {task['description'][:55]}...")
            for rollout in range(N_ROLLOUTS):
                done += 1
                print(f"    rollout {rollout + 1}/{N_ROLLOUTS} ({done}/{total})", end=" ", flush=True)
                try:
                    code, latency_ms, cost_usd = call_agent(agent, task["description"])
                    passed, total_tests = run_tests(code, task_idx)
                    sec = security_score(code)
                    execution_success = (passed == total_tests) and total_tests > 0
                    print(f"✓  tests={passed}/{total_tests}  sec={sec:.2f}  {latency_ms:.0f}ms")
                except Exception as e:
                    print(f"✗  ERROR: {e}")
                    code, latency_ms, cost_usd = "", 0.0, 0.0
                    passed, total_tests = 0, N_TESTS_PER_TASK
                    sec = 1.0
                    execution_success = False

                records.append({
                    "task_id": task_id,
                    "agent_name": agent,
                    "rollout": rollout,
                    "generated_code": code,
                    "tests_passed": passed,
                    "tests_total": total_tests,
                    "execution_success": execution_success,
                    "security_score": sec,
                    "latency_ms": latency_ms,
                    "cost_usd": cost_usd,
                })
                time.sleep(0.3)  # gentle rate limiting

    return records


# ── Metrics ────────────────────────────────────────────────────────────────────

def compute_metrics(records: List[dict]) -> dict:
    results = [
        ExecutionResult(
            task_id=r["task_id"],
            agent_name=r["agent_name"],
            tests_passed=r["tests_passed"],
            tests_total=max(r["tests_total"], 1),
            regression_count=0,
            execution_success=r["execution_success"],
        )
        for r in records
    ]
    submissions = [
        AgentSubmission(
            task_id=r["task_id"],
            agent_name=r["agent_name"],
            generated_code=r["generated_code"],
            tool_calls_used=1,
            latency_ms=r["latency_ms"],
            cost_usd=max(r["cost_usd"], 0.0),
        )
        for r in records
    ]

    metrics = {}
    for agent in AGENTS:
        agent_results = [r for r in results if r.agent_name == agent]
        agent_subs = [s for s in submissions if s.agent_name == agent]
        agent_records = [r for r in records if r["agent_name"] == agent]
        metrics[agent] = {
            "reliability": reliability_at_k(agent_results, k=K),
            "security_adj_reliability": security_adjusted_reliability_at_k(
                agent_results, agent_subs, k=K, security_threshold=SECURITY_THRESHOLD
            ),
            "mean_security_score": sum(r["security_score"] for r in agent_records) / max(len(agent_records), 1),
            "total_cost": sum(r["cost_usd"] for r in agent_records),
        }
    return metrics


# ── Figure 5 ───────────────────────────────────────────────────────────────────

def plot_fig5(metrics: dict, tau: float, p_value: float) -> None:
    rel = [metrics[a]["reliability"] for a in AGENTS]
    sec_adj = [metrics[a]["security_adj_reliability"] for a in AGENTS]

    x = np.arange(len(AGENTS))
    width = 0.35
    y_max = max(max(rel + sec_adj), 0.05) * 1.3

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar(x - width / 2, rel,     width, label=f"reliability@{K}",              color=COLORS["reliability"])
    bars2 = ax.bar(x + width / 2, sec_adj, width, label=f"security_adj_reliability@{K}", color=COLORS["security_adj"])

    ax.set_xticks(x)
    ax.set_xticklabels(AGENTS)
    ax.set_ylim(0, y_max)
    ax.set_ylabel("Score")
    ax.set_title(
        f"Figure 5 — H4: reliability@{K} vs security_adjusted_reliability@{K}\n"
        f"Kendall τ = {tau:.3f}  (p = {p_value:.3f})  |  security threshold ≥ {SECURITY_THRESHOLD}"
    )
    ax.legend()

    for bar in list(bars1) + list(bars2):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + y_max * 0.01,
                f"{h:.3f}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig5_h4_security_leaderboard.png")
    fig.savefig(path, dpi=150)
    print(f"\nSaved {path}")
    plt.close(fig)


# ── Results summary ────────────────────────────────────────────────────────────

def print_results(metrics: dict, tau: float, p_value: float) -> None:
    print("\n" + "=" * 70)
    print("  Experiment 4 — H4: Security-Adjusted Reliability")
    print("=" * 70)
    print(f"\n{'Agent':<16} {'reliability@5':>14} {'mean_sec_score':>15} {'sec_adj_rel@5':>14} {'cost_usd':>10}")
    print("-" * 70)
    for agent in AGENTS:
        m = metrics[agent]
        print(
            f"{agent:<16} {m['reliability']:>14.3f} {m['mean_security_score']:>15.3f} "
            f"{m['security_adj_reliability']:>14.3f} {m['total_cost']:>10.4f}"
        )

    rel_rank = sorted(AGENTS, key=lambda a: metrics[a]["reliability"], reverse=True)
    sec_rank = sorted(AGENTS, key=lambda a: metrics[a]["security_adj_reliability"], reverse=True)

    print(f"\nreliability@5 ranking:             {rel_rank}")
    print(f"security_adj_reliability ranking:  {sec_rank}")
    print(f"Rank flip observed:                {rel_rank != sec_rank}")
    print(f"\nKendall τ = {tau:.3f}  (p = {p_value:.3f})")
    print(f"H4 threshold:  τ < 0.6")
    print(f"H4 confirmed:  {tau < 0.6}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot", action="store_true",
                        help="Regenerate figure from saved JSON without re-running APIs")
    args = parser.parse_args()

    if args.plot:
        if not os.path.exists(RESULTS_PATH):
            print(f"No saved results at {RESULTS_PATH}. Run without --plot first.")
            sys.exit(1)
        print(f"Loading saved results from {RESULTS_PATH}")
        with open(RESULTS_PATH) as f:
            records = json.load(f)
    else:
        print(f"H4 experiment: {len(SAMPLE_TASKS)} tasks × {len(AGENTS)} agents × {N_ROLLOUTS} rollouts")
        print(f"Total API calls: {len(SAMPLE_TASKS) * len(AGENTS) * N_ROLLOUTS}")
        records = collect_rollouts()
        with open(RESULTS_PATH, "w") as f:
            json.dump(records, f, indent=2)
        print(f"\nResults saved to {RESULTS_PATH}")

    metrics = compute_metrics(records)

    rel_scores = [metrics[a]["reliability"] for a in AGENTS]
    sec_scores = [metrics[a]["security_adj_reliability"] for a in AGENTS]
    tau, p_value = kendalltau(rel_scores, sec_scores)

    print_results(metrics, tau, p_value)
    plot_fig5(metrics, tau, p_value)

    total_cost = sum(r["cost_usd"] for r in records)
    print(f"\nTotal API cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
