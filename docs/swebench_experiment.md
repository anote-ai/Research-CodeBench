# SWE-bench Verified Experiment

CodeBench now supports real-world tasks from
[SWE-bench Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified),
replacing the synthetic sample tasks for benchmark runs. The adapter lives in
`src/codebench/swebench_adapter.py`.

## Leakage policy (important)

The gold `patch`, `test_patch`, `FAIL_TO_PASS`, and `PASS_TO_PASS` fields must
**never** be shown to a coding agent. The adapter enforces this:

- `swebench_instance_to_codetask()` produces a fully agent-safe `CodeTask`:
  `test_file` and `reference_solution` hold placeholder strings, never gold data.
- The agent-facing view (`agent_prompt_payload()`) contains only the issue
  description (`problem_statement`), repo name, base commit, difficulty, and tags.
- Gold data is kept only in the clearly-marked `hidden_reference` block of the
  sample file, for internal sanity checks and harness evaluation — not inference.

## Workflow

### 1. Prepare a sample

```bash
python scripts/prepare_swebench_sample.py                 # 5 tasks (default)
python scripts/prepare_swebench_sample.py --limit 30      # scale up later
python scripts/prepare_swebench_sample.py --limit 50 --difficulty easy
```

This downloads `SWE-bench/SWE-bench_Verified` from Hugging Face (requires the
`datasets` package) and writes `data/swebench_verified_sample.jsonl`. Each line
contains:

| Key | Contents | Agent-visible? |
|-----|----------|----------------|
| `task` | Agent-safe `CodeTask` fields | Yes |
| `base_commit` | Commit to check the repo out at | Yes |
| `environment_setup_commit` | Commit for environment setup | No (infra only) |
| `hidden_reference` | Gold patch, test patch, FAIL_TO_PASS, PASS_TO_PASS | **Never** |

SWE-bench difficulty labels map to CodeBench difficulties:

| SWE-bench label | CodeBench difficulty |
|-----------------|----------------------|
| `<15 min fix` | easy |
| `15 min - 1 hour` | medium |
| `1-4 hours` | hard |
| `>4 hours` | hard |
| missing/unknown | medium |

### 2. Create a predictions template

```bash
python scripts/create_swebench_predictions_template.py --model-name anote-code
```

Writes `predictions/swebench_predictions_template.jsonl` with one stub per
sampled task in the official SWE-bench harness format:

```json
{"instance_id": "astropy__astropy-12907", "model_name_or_path": "anote-code", "model_patch": ""}
```

### 3. Run agents to generate patches

For each task, give the agent only the agent-safe fields (`task.description`,
`task.repo`, `base_commit`, tags). The agent checks out `repo` at
`base_commit`, works on the issue, and produces a unified diff. Fill that diff
into the `model_patch` field of the corresponding template line. (Full agent
automation is intentionally not implemented yet.)

### 4. Evaluate with the official SWE-bench harness

```bash
pip install swebench
python -m swebench.harness.run_evaluation \
    --dataset_name SWE-bench/SWE-bench_Verified \
    --predictions_path predictions/swebench_predictions_template.jsonl \
    --max_workers 4 \
    --run_id codebench-swebench-v0
```

The harness applies each `model_patch` in a containerized environment and runs
the hidden FAIL_TO_PASS / PASS_TO_PASS tests.

### 5. Convert results back into CodeBench metrics

From the harness report, build `ExecutionResult` objects per (task, agent):

- `tests_passed` / `tests_total` — from the FAIL_TO_PASS + PASS_TO_PASS outcomes
- `regression_count` — PASS_TO_PASS tests that now fail
- `execution_success` — the instance is marked *resolved*

These feed directly into the existing `codebench.evaluate` leaderboard
(pass@k, regression rate, cost-adjusted score) without any API changes.

## Testing

Adapter tests run offline with fake instances (no Hugging Face download):

```bash
python -m pytest tests/test_swebench_adapter.py -q
```
