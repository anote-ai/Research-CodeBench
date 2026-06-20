"""Sample tasks and factory helpers for codebench."""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

from .core import (
    AgentSubmission,
    BenchmarkHarness,
    CodeTask,
    ComplexityScore,
    ExecutionResult,
    TaskDifficulty,
    TestCategory,
    TestResult,
    TestSuite,
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
    {
        "task_id": "task-006",
        "repo": "anote-ai/sort-lib",
        "description": "Implement merge sort on a list of integers. Return a new sorted list.",
        "difficulty": "easy",
        "test_file": "tests/test_mergesort.py",
        "reference_solution": "def merge_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    mid = len(arr) // 2\n    left = merge_sort(arr[:mid])\n    right = merge_sort(arr[mid:])\n    result = []\n    i = j = 0\n    while i < len(left) and j < len(right):\n        if left[i] <= right[j]:\n            result.append(left[i]); i += 1\n        else:\n            result.append(right[j]); j += 1\n    result.extend(left[i:])\n    result.extend(right[j:])\n    return result\n",
        "tags": ["algorithms", "sorting", "divide-and-conquer"],
    },
    {
        "task_id": "task-007",
        "repo": "anote-ai/trie-lib",
        "description": "Implement a Trie data structure supporting insert(word), search(word), and starts_with(prefix).",
        "difficulty": "medium",
        "test_file": "tests/test_trie.py",
        "reference_solution": "class TrieNode:\n    def __init__(self):\n        self.children = {}\n        self.is_end = False\n\nclass Trie:\n    def __init__(self):\n        self.root = TrieNode()\n    def insert(self, word):\n        node = self.root\n        for ch in word:\n            node = node.children.setdefault(ch, TrieNode())\n        node.is_end = True\n    def search(self, word):\n        node = self.root\n        for ch in word:\n            if ch not in node.children:\n                return False\n            node = node.children[ch]\n        return node.is_end\n    def starts_with(self, prefix):\n        node = self.root\n        for ch in prefix:\n            if ch not in node.children:\n                return False\n            node = node.children[ch]\n        return True\n",
        "tags": ["data-structures", "trie", "strings"],
    },
    {
        "task_id": "task-008",
        "repo": "anote-ai/api-client",
        "description": "Write a retry decorator that retries a function up to N times on exception, with exponential backoff.",
        "difficulty": "medium",
        "test_file": "tests/test_retry.py",
        "reference_solution": "import time\nimport functools\n\ndef retry(max_attempts=3, backoff=2.0):\n    def decorator(fn):\n        @functools.wraps(fn)\n        def wrapper(*args, **kwargs):\n            delay = 1.0\n            for attempt in range(max_attempts):\n                try:\n                    return fn(*args, **kwargs)\n                except Exception:\n                    if attempt == max_attempts - 1:\n                        raise\n                    time.sleep(delay)\n                    delay *= backoff\n        return wrapper\n    return decorator\n",
        "tags": ["api-integration", "resilience", "decorators"],
    },
    {
        "task_id": "task-009",
        "repo": "anote-ai/dp-lib",
        "description": "Implement the 0/1 knapsack problem using dynamic programming. Return the maximum value.",
        "difficulty": "hard",
        "test_file": "tests/test_knapsack.py",
        "reference_solution": "def knapsack(weights, values, capacity):\n    n = len(weights)\n    dp = [[0] * (capacity + 1) for _ in range(n + 1)]\n    for i in range(1, n + 1):\n        for w in range(capacity + 1):\n            dp[i][w] = dp[i-1][w]\n            if weights[i-1] <= w:\n                dp[i][w] = max(dp[i][w], dp[i-1][w - weights[i-1]] + values[i-1])\n    return dp[n][capacity]\n",
        "tags": ["algorithms", "dynamic-programming", "optimization"],
    },
    {
        "task_id": "task-010",
        "repo": "anote-ai/stream-utils",
        "description": "Implement a streaming median data structure supporting add(num) and get_median() in O(log n) amortised time.",
        "difficulty": "hard",
        "test_file": "tests/test_median.py",
        "reference_solution": "import heapq\n\nclass MedianFinder:\n    def __init__(self):\n        self.low = []   # max-heap (negated)\n        self.high = []  # min-heap\n    def add(self, num):\n        heapq.heappush(self.low, -num)\n        heapq.heappush(self.high, -heapq.heappop(self.low))\n        if len(self.high) > len(self.low):\n            heapq.heappush(self.low, -heapq.heappop(self.high))\n    def get_median(self):\n        if len(self.low) > len(self.high):\n            return float(-self.low[0])\n        return (-self.low[0] + self.high[0]) / 2.0\n",
        "tags": ["data-structures", "heap", "streaming"],
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


def make_test_suite(
    task_id: str,
    agent_name: str = "mock-agent",
    unit_pass_rate: float = 0.8,
    integration_pass_rate: float = 0.7,
    edge_case_pass_rate: float = 0.5,
    n_unit: int = 5,
    n_integration: int = 3,
    n_edge: int = 2,
    seed: int = 42,
) -> TestSuite:
    """Build a TestSuite with realistic pass/fail patterns."""
    rng = random.Random(seed)
    results: List[TestResult] = []

    spec = [
        (TestCategory.UNIT, n_unit, unit_pass_rate),
        (TestCategory.INTEGRATION, n_integration, integration_pass_rate),
        (TestCategory.EDGE_CASE, n_edge, edge_case_pass_rate),
    ]
    for category, n, rate in spec:
        for j in range(n):
            passed = rng.random() < rate
            results.append(
                TestResult(
                    test_name=f"{category.value}_{j:02d}",
                    category=category,
                    passed=passed,
                    execution_time_ms=rng.uniform(1.0, 200.0),
                    error_message=None if passed else "AssertionError",
                )
            )
    return TestSuite(task_id=task_id, agent_name=agent_name, test_results=results)


def make_complexity_score(
    task_id: str,
    agent_name: str = "mock-agent",
    seed: int = 42,
) -> ComplexityScore:
    """Generate a plausible ComplexityScore for a submission."""
    rng = random.Random(seed)
    return ComplexityScore(
        task_id=task_id,
        agent_name=agent_name,
        cyclomatic_complexity=rng.randint(1, 25),
        lines_of_code=rng.randint(10, 150),
        n_functions=rng.randint(1, 10),
    )


def make_rollout_benchmark(
    n_tasks: int = 10,
    agents: Optional[List[str]] = None,
    n_rollouts: int = 5,
    seed: int = 42,
) -> BenchmarkHarness:
    """Build a BenchmarkHarness with n_rollouts independent submissions per (task, agent).

    Each agent is assigned a 'true' skill level drawn once per task; individual
    rollout pass rates are then sampled around that skill level to simulate
    run-to-run variance. This gives reliability@k its required n>1 rollout counts.
    """
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
            # True skill: stable per (task, agent) pair
            true_skill = rng.uniform(0.3, 1.0)
            # Variance: higher-skill agents are slightly more consistent
            variance = rng.uniform(0.05, 0.25) * (1.0 - true_skill * 0.5)

            for r in range(n_rollouts):
                rollout_seed = seed + i * 1000 + j * 100 + r
                rollout_rng = random.Random(rollout_seed)
                # Per-rollout pass rate sampled around true skill
                pr = max(0.0, min(1.0, true_skill + rollout_rng.gauss(0, variance)))
                sub, res = make_submission(
                    task_id=task.task_id,
                    agent_name=agent,
                    pass_rate=pr,
                    seed=rollout_seed,
                )
                # Override execution_success: a rollout is fully successful only
                # when all tests pass — a meaningful threshold for reliability@k.
                res = res.model_copy(update={"execution_success": pr >= 0.95})
                harness.add_submission(sub)
                harness.add_result(res)

    return harness


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

            suite = make_test_suite(
                task_id=task.task_id,
                agent_name=agent,
                unit_pass_rate=pr,
                integration_pass_rate=pr * 0.9,
                edge_case_pass_rate=pr * 0.7,
                seed=seed + i * 100 + j + 1,
            )
            harness.add_test_suite(suite)

            cx = make_complexity_score(
                task_id=task.task_id,
                agent_name=agent,
                seed=seed + i * 100 + j + 2,
            )
            harness.add_complexity_score(cx)

    return harness
