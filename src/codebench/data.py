"""Sample tasks and factory helpers for codebench."""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

from .core import (
    AgentSubmission,
    BenchmarkHarness,
    CodeTask,
    ExecutionResult,
    TaskDifficulty,
)

SAMPLE_TASKS: List[dict] = [
    {
        "task_id": "task-001",
        "repo": "anote-ai/repo-parser",
        "description": "Implement a Python function that parses imports from a source file and returns a sorted list of module names.",
        "difficulty": "easy",
        "test_file": "tests/test_parser.py",
        "reference_solution": "import ast\n\ndef parse_imports(source: str) -> list[str]:\n    tree = ast.parse(source)\n    modules = []\n    for node in ast.walk(tree):\n        if isinstance(node, ast.Import):\n            modules.extend(alias.name for alias in node.names)\n        elif isinstance(node, ast.ImportFrom):\n            if node.module:\n                modules.append(node.module)\n    return sorted(set(modules))\n",
        "tags": ["parsing", "ast", "python"],
    },
    {
        "task_id": "task-002",
        "repo": "anote-ai/data-pipeline",
        "description": "Write a class DataPipeline with methods load(path), transform(fn), and save(path) using pandas.",
        "difficulty": "medium",
        "test_file": "tests/test_pipeline.py",
        "reference_solution": "import pandas as pd\n\nclass DataPipeline:\n    def __init__(self):\n        self.df = None\n    def load(self, path):\n        self.df = pd.read_csv(path)\n        return self\n    def transform(self, fn):\n        self.df = fn(self.df)\n        return self\n    def save(self, path):\n        self.df.to_csv(path, index=False)\n        return self\n",
        "tags": ["pandas", "pipeline", "data"],
    },
    {
        "task_id": "task-003",
        "repo": "anote-ai/graph-utils",
        "description": "Implement Dijkstra's shortest path algorithm for a weighted adjacency-list graph.",
        "difficulty": "hard",
        "test_file": "tests/test_graph.py",
        "reference_solution": "import heapq\n\ndef dijkstra(graph, start):\n    dist = {start: 0}\n    heap = [(0, start)]\n    while heap:\n        d, u = heapq.heappop(heap)\n        if d > dist.get(u, float('inf')):\n            continue\n        for v, w in graph.get(u, []):\n            nd = d + w\n            if nd < dist.get(v, float('inf')):\n                dist[v] = nd\n                heapq.heappush(heap, (nd, v))\n    return dist\n",
        "tags": ["graph", "algorithms", "dynamic-programming"],
    },
    {
        "task_id": "task-004",
        "repo": "anote-ai/text-utils",
        "description": "Implement a function that computes the BM25 score for a query against a corpus of documents.",
        "difficulty": "hard",
        "test_file": "tests/test_bm25.py",
        "reference_solution": "import math\nfrom collections import Counter\n\ndef bm25(corpus, query, k1=1.5, b=0.75):\n    N = len(corpus)\n    avgdl = sum(len(d) for d in corpus) / N\n    scores = []\n    tf_corpus = [Counter(doc) for doc in corpus]\n    df = Counter(term for doc in corpus for term in set(doc))\n    for doc, tf in zip(corpus, tf_corpus):\n        score = 0\n        dl = len(doc)\n        for term in query:\n            if term not in tf:\n                continue\n            idf = math.log((N - df[term] + 0.5) / (df[term] + 0.5) + 1)\n            num = tf[term] * (k1 + 1)\n            den = tf[term] + k1 * (1 - b + b * dl / avgdl)\n            score += idf * num / den\n        scores.append(score)\n    return scores\n",
        "tags": ["ir", "nlp", "ranking"],
    },
    {
        "task_id": "task-005",
        "repo": "anote-ai/cache-lib",
        "description": "Implement an LRU cache class with get(key) and put(key, value) methods in O(1) time.",
        "difficulty": "medium",
        "test_file": "tests/test_lru.py",
        "reference_solution": "from collections import OrderedDict\n\nclass LRUCache:\n    def __init__(self, capacity):\n        self.capacity = capacity\n        self.cache = OrderedDict()\n    def get(self, key):\n        if key not in self.cache:\n            return -1\n        self.cache.move_to_end(key)\n        return self.cache[key]\n    def put(self, key, value):\n        if key in self.cache:\n            self.cache.move_to_end(key)\n        self.cache[key] = value\n        if len(self.cache) > self.capacity:\n            self.cache.popitem(last=False)\n",
        "tags": ["data-structures", "caching", "design"],
    },
]


def make_task(i: int = 0) -> CodeTask:
    """Return the i-th sample task as a CodeTask object."""
    return CodeTask(**SAMPLE_TASKS[i % len(SAMPLE_TASKS)])


def make_submission(
    task_id: str,
    agent_name: str = "mock-agent",
    pass_rate: float = 0.8,
    seed: int = 42,
) -> Tuple[AgentSubmission, ExecutionResult]:
    """Create a matched AgentSubmission + ExecutionResult."""
    rng = random.Random(seed)
    tests_total = 10
    tests_passed = round(pass_rate * tests_total)
    regression_count = rng.randint(0, max(0, tests_total - tests_passed))

    submission = AgentSubmission(
        task_id=task_id,
        agent_name=agent_name,
        generated_code="# generated\ndef solution(): pass\n",
        tool_calls_used=rng.randint(1, 15),
        latency_ms=rng.uniform(500, 5000),
        cost_usd=rng.uniform(0.001, 0.05),
    )
    result = ExecutionResult(
        task_id=task_id,
        agent_name=agent_name,
        tests_passed=tests_passed,
        tests_total=tests_total,
        regression_count=regression_count,
        execution_success=pass_rate > 0,
    )
    return submission, result


def make_benchmark(
    n_tasks: int = 10,
    agents: Optional[List[str]] = None,
    seed: int = 42,
) -> BenchmarkHarness:
    """Build a fully-populated BenchmarkHarness."""
    if agents is None:
        agents = ["anote-code", "claude-code", "codex"]

    rng = random.Random(seed)
    harness = BenchmarkHarness()

    difficulties = list(TaskDifficulty)
    for i in range(n_tasks):
        base = SAMPLE_TASKS[i % len(SAMPLE_TASKS)].copy()
        base["task_id"] = f"task-{i:03d}"
        base["difficulty"] = rng.choice(difficulties).value
        task = CodeTask(**base)
        harness.add_task(task)

        for j, agent in enumerate(agents):
            pr = rng.uniform(0.3, 1.0)
            sub, res = make_submission(
                task_id=task.task_id,
                agent_name=agent,
                pass_rate=pr,
                seed=seed + i * 100 + j,
            )
            harness.add_submission(sub)
            harness.add_result(res)

    return harness
