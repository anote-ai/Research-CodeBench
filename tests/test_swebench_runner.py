"""Tests for codebench.swebench_runner (offline: local git repos, no network)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from codebench.swebench_runner import (
    build_agent_prompt,
    capture_model_patch,
    create_worktree,
    ensure_repo_clone,
    load_agent_safe_tasks,
    run_swebench_attempts,
)

GOLD_SENTINEL = "XGOLDPATCHX-must-never-leak"
HIDDEN_TEST_SENTINEL = "XHIDDENTESTX-must-never-leak"


def _git(args, cwd):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )


def _sha(cwd):
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(cwd),
        check=True, capture_output=True, text=True,
    ).stdout.strip()


@pytest.fixture
def fake_remote(tmp_path):
    """A local 'remote' repo acme/widget with two commits.

    base_commit is the FIRST commit, so tests prove worktrees check out
    base_commit rather than the branch tip.
    """
    repo = tmp_path / "remotes" / "acme" / "widget"
    repo.mkdir(parents=True)
    _git(["init", "-q"], repo)
    (repo / "app.py").write_text("VERSION = 1\n", encoding="utf-8")
    _git(["add", "-A"], repo)
    _git(["commit", "-q", "-m", "base"], repo)
    base_commit = _sha(repo)
    (repo / "app.py").write_text("VERSION = 2\n", encoding="utf-8")
    _git(["add", "-A"], repo)
    _git(["commit", "-q", "-m", "tip"], repo)
    return {"git_base_url": str(tmp_path / "remotes"), "repo": "acme/widget",
            "base_commit": base_commit}


@pytest.fixture
def sample_file(tmp_path, fake_remote):
    """A poisoned sample JSONL: gold fields carry sentinel strings."""
    record = {
        "task": {
            "task_id": "acme__widget-1",
            "repo": fake_remote["repo"],
            "description": "The widget crashes when VERSION is read.",
            "difficulty": "medium",
            "tags": ["swebench", "acme/widget", "medium"],
            "test_file": "swebench://hidden-tests",
            "reference_solution": "swebench://hidden-gold-patch",
        },
        "base_commit": fake_remote["base_commit"],
        "environment_setup_commit": "envsha",
        "hidden_reference": {
            "patch": GOLD_SENTINEL,
            "test_patch": HIDDEN_TEST_SENTINEL,
            "FAIL_TO_PASS": f'["{HIDDEN_TEST_SENTINEL}::t1"]',
            "PASS_TO_PASS": "[]",
            "_note": "reference-only",
        },
    }
    path = tmp_path / "sample.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return path


def run_kwargs(tmp_path, sample_file, fake_remote, **overrides):
    kwargs = dict(
        sample_path=sample_file,
        agent_cmd="noop",
        model_name="test-agent",
        attempts=1,
        run_name="t",
        workspaces_dir=tmp_path / "workspaces",
        attempts_dir=tmp_path / "attempts",
        predictions_dir=tmp_path / "predictions",
        git_base_url=fake_remote["git_base_url"],
    )
    kwargs.update(overrides)
    return kwargs


# ------------------------------------------------------------- safe loading

def test_load_agent_safe_tasks_drops_hidden_fields(sample_file):
    tasks = load_agent_safe_tasks(sample_file)
    assert len(tasks) == 1
    task = tasks[0]
    assert task.task_id == "acme__widget-1"
    assert task.repo == "acme/widget"
    assert task.base_commit
    dumped = json.dumps(task.model_dump())
    assert GOLD_SENTINEL not in dumped
    assert HIDDEN_TEST_SENTINEL not in dumped
    assert "hidden_reference" not in dumped


def test_prompt_contains_only_allowed_fields(sample_file):
    task = load_agent_safe_tasks(sample_file)[0]
    prompt = build_agent_prompt(task)
    assert task.description in prompt
    assert task.repo in prompt
    assert task.base_commit in prompt
    assert GOLD_SENTINEL not in prompt
    assert HIDDEN_TEST_SENTINEL not in prompt


# ---------------------------------------------------------------- checkout

def test_worktree_checks_out_base_commit_not_tip(tmp_path, fake_remote):
    clone = ensure_repo_clone(
        fake_remote["repo"], tmp_path / "workspaces", fake_remote["git_base_url"]
    )
    wt = create_worktree(clone, fake_remote["base_commit"], tmp_path / "wt")
    assert (wt / "app.py").read_text() == "VERSION = 1\n"  # not the tip's VERSION = 2


def test_clone_is_cached(tmp_path, fake_remote):
    c1 = ensure_repo_clone(
        fake_remote["repo"], tmp_path / "workspaces", fake_remote["git_base_url"]
    )
    c2 = ensure_repo_clone(
        fake_remote["repo"], tmp_path / "workspaces", fake_remote["git_base_url"]
    )
    assert c1 == c2 and c1.exists()


# ------------------------------------------------------------- diff capture

def test_capture_model_patch_includes_new_and_edited_files(tmp_path, fake_remote):
    clone = ensure_repo_clone(
        fake_remote["repo"], tmp_path / "workspaces", fake_remote["git_base_url"]
    )
    wt = create_worktree(clone, fake_remote["base_commit"], tmp_path / "wt")
    (wt / "app.py").write_text("VERSION = 1\nFIXED = True\n", encoding="utf-8")
    (wt / "new_module.py").write_text("x = 1\n", encoding="utf-8")
    patch = capture_model_patch(wt, fake_remote["base_commit"])
    assert "FIXED = True" in patch
    assert "new_module.py" in patch


# ------------------------------------------------------- end-to-end running

def test_noop_run_produces_empty_patch_predictions(tmp_path, sample_file, fake_remote):
    files = run_swebench_attempts(**run_kwargs(tmp_path, sample_file, fake_remote))
    assert set(files) == {1}
    rows = [json.loads(l) for l in files[1].read_text().splitlines()]
    assert rows == [
        {"instance_id": "acme__widget-1", "model_name_or_path": "test-agent",
         "model_patch": ""}
    ]
    record_dir = tmp_path / "attempts" / "t" / "acme__widget-1" / "attempt-1"
    assert (record_dir / "prompt.md").exists()
    assert (record_dir / "meta.json").exists()
    assert (record_dir / "model.patch").read_text() == ""


def test_scripted_agent_patch_roundtrip(tmp_path, sample_file, fake_remote):
    # a "real" agent: writes fix.py into its working directory
    agent_cmd = (
        f'{sys.executable} -c '
        f'"import pathlib; pathlib.Path(\'fix.py\').write_text(\'patched\')"'
    )
    files = run_swebench_attempts(
        **run_kwargs(tmp_path, sample_file, fake_remote, agent_cmd=agent_cmd)
    )
    row = json.loads(files[1].read_text().splitlines()[0])
    assert set(row) == {"instance_id", "model_name_or_path", "model_patch"}
    assert "fix.py" in row["model_patch"]
    assert "patched" in row["model_patch"]
    # worktree cleaned up by default
    assert not (tmp_path / "workspaces" / "runs" / "t").exists() or not any(
        (tmp_path / "workspaces" / "runs" / "t").iterdir()
    )


def test_multiple_attempts_one_predictions_file_each(tmp_path, sample_file, fake_remote):
    files = run_swebench_attempts(
        **run_kwargs(tmp_path, sample_file, fake_remote, attempts=3)
    )
    assert set(files) == {1, 2, 3}
    for k, path in files.items():
        assert path.name == f"t_attempt{k}.jsonl"
        assert len(path.read_text().splitlines()) == 1
    for k in (1, 2, 3):
        assert (tmp_path / "attempts" / "t" / "acme__widget-1" / f"attempt-{k}").exists()


def test_failed_agent_yields_empty_patch(tmp_path, sample_file, fake_remote):
    files = run_swebench_attempts(
        **run_kwargs(tmp_path, sample_file, fake_remote,
                     agent_cmd=f"{sys.executable} -c \"raise SystemExit(3)\"")
    )
    row = json.loads(files[1].read_text().splitlines()[0])
    assert row["model_patch"] == ""
    meta = json.loads(
        (tmp_path / "attempts" / "t" / "acme__widget-1" / "attempt-1" / "meta.json").read_text()
    )
    assert meta["exit_code"] == 3


def test_resume_skips_completed_attempts(tmp_path, sample_file, fake_remote):
    run_swebench_attempts(**run_kwargs(tmp_path, sample_file, fake_remote))
    meta_path = tmp_path / "attempts" / "t" / "acme__widget-1" / "attempt-1" / "meta.json"
    before = meta_path.stat().st_mtime_ns
    # an agent that would fail if actually executed
    files = run_swebench_attempts(
        **run_kwargs(tmp_path, sample_file, fake_remote, resume=True,
                     agent_cmd="false && this-should-never-run")
    )
    assert meta_path.stat().st_mtime_ns == before  # not re-run
    row = json.loads(files[1].read_text().splitlines()[0])
    assert row["instance_id"] == "acme__widget-1"


def test_invalid_attempts_rejected(tmp_path, sample_file, fake_remote):
    with pytest.raises(ValueError):
        run_swebench_attempts(**run_kwargs(tmp_path, sample_file, fake_remote, attempts=0))


# ---------------------------------------------------------------- leakage

def test_no_gold_data_anywhere_in_run_artifacts(tmp_path, sample_file, fake_remote):
    run_swebench_attempts(
        **run_kwargs(tmp_path, sample_file, fake_remote, attempts=2)
    )
    artifact_roots = [tmp_path / "attempts", tmp_path / "predictions"]
    checked = 0
    for root in artifact_roots:
        for path in root.rglob("*"):
            if path.is_file():
                content = path.read_text(encoding="utf-8", errors="replace")
                assert GOLD_SENTINEL not in content, path
                assert HIDDEN_TEST_SENTINEL not in content, path
                assert "hidden_reference" not in content, path
                checked += 1
    assert checked >= 7  # prompts, logs, patches, metas, predictions
