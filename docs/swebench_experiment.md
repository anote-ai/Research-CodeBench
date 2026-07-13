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

`scripts/run_swebench_agent.py` automates real attempts. Per task × attempt it
checks out the target repo at `base_commit` in an isolated git worktree
(clones are cached under `workspaces/repos/`), runs your agent command there,
captures `git diff` against `base_commit` as `model_patch`, and writes one
official predictions JSONL per attempt index.

```bash
# dry-run the whole pipeline first (no real agent, empty patches)
python scripts/run_swebench_agent.py --agent-cmd noop --run-name dryrun

# 3 independent attempts per task with Claude Code
python scripts/run_swebench_agent.py \
    --model-name anote-code --attempts 3 --timeout 1800 --run-name v1 \
    --agent-cmd 'claude -p "$(cat {prompt_file})" --permission-mode acceptEdits'
# → predictions/v1_attempt1.jsonl, v1_attempt2.jsonl, v1_attempt3.jsonl
```

`--agent-cmd` is a shell template with `{prompt_file}`, `{workdir}`,
`{instance_id}`, and `{repo}` placeholders, so any agent CLI plugs in. The
agent's prompt and working directory contain only agent-safe data — the
runner strips `hidden_reference` at load time (`load_agent_safe_tasks`) and
never writes gold fields into prompts, logs, or attempt records
(`attempts/{run}/{instance}/attempt-{k}/`). Failed or timed-out attempts are
recorded with an empty patch so they still count as rollouts. Use `--resume`
to continue an interrupted run and `--attempts N` for multiple independent
rollouts per task (the harness allows one prediction per instance per file,
hence one predictions file per attempt index).

### 4. Evaluate with the official SWE-bench harness

```bash
pip install swebench   # or: pip install -e ".[eval]"
for k in 1 2 3; do
  python -m swebench.harness.run_evaluation \
      --dataset_name SWE-bench/SWE-bench_Verified \
      --predictions_path predictions/v1_attempt$k.jsonl \
      --max_workers 2 \
      --run_id v1-attempt$k
done
```

The harness applies each `model_patch` in a containerized environment
(Docker must be running) and runs the hidden FAIL_TO_PASS / PASS_TO_PASS
tests. Each run writes a summary `{model}.{run_id}.json` plus per-instance
reports under `logs/run_evaluation/{run_id}/{model}/`.

### 5. Convert results back into CodeBench metrics

```bash
python scripts/convert_swebench_report.py \
    --run-ids v1-attempt1 v1-attempt2 v1-attempt3 \
    --model-name anote-code -k 3 \
    --output data/swebench_results_anote-code_v1.json
```

Each evaluated (instance, attempt) becomes one `ExecutionResult` rollout:

- `tests_passed` / `tests_total` — from the FAIL_TO_PASS + PASS_TO_PASS outcomes
- `regression_count` — PASS_TO_PASS tests that now fail
- `execution_success` — the instance is marked *resolved*

Pooling one harness run per attempt gives exactly the rollout shape
`codebench.evaluate.reliability_at_k` consumes (n = attempts, c = resolved
attempts), replacing synthetic rollouts with real ones in the H-experiment
pipeline — no API changes.

## Testing

Adapter, runner, and results tests all run offline (fake instances, local
git fixture repos, fixture harness reports — no Hugging Face download, no
Docker):

```bash
python -m pytest tests/test_swebench_adapter.py tests/test_swebench_runner.py tests/test_swebench_results.py -q
```
