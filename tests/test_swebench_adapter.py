"""Tests for codebench.swebench_adapter (no network access required)."""

import json

import pytest

from codebench.core import CodeTask, TaskDifficulty
from codebench import swebench_adapter
from codebench.swebench_adapter import (
    HIDDEN_FIELDS,
    PREDICTION_KEYS,
    REFERENCE_SOLUTION_PLACEHOLDER,
    TEST_FILE_PLACEHOLDER,
    agent_prompt_payload,
    extract_hidden_reference,
    load_swebench_verified,
    map_swebench_difficulty,
    read_swebench_sample,
    swebench_instance_to_codetask,
    write_predictions_jsonl,
    write_swebench_sample,
)

GOLD_PATCH = "diff --git a/astropy/io.py b/astropy/io.py\n--- SECRET GOLD PATCH ---\n"
GOLD_TEST_PATCH = "diff --git a/tests/test_io.py b/tests/test_io.py\n--- SECRET TEST PATCH ---\n"


def make_instance(i=0, difficulty="15 min - 1 hour"):
    """A fake SWE-bench Verified instance with all relevant fields."""
    return {
        "instance_id": f"astropy__astropy-{1000 + i}",
        "repo": "astropy/astropy",
        "base_commit": f"abc{i:03d}def",
        "environment_setup_commit": f"env{i:03d}",
        "problem_statement": f"Issue {i}: reading FITS files crashes with a TypeError.",
        "hints_text": "",
        "difficulty": difficulty,
        "patch": GOLD_PATCH,
        "test_patch": GOLD_TEST_PATCH,
        "FAIL_TO_PASS": '["tests/test_io.py::test_fits_read"]',
        "PASS_TO_PASS": '["tests/test_io.py::test_fits_write"]',
    }


@pytest.fixture
def fake_dataset(monkeypatch):
    """Route the adapter's HF loader to 12 fake instances of mixed difficulty."""
    labels = ["<15 min fix", "15 min - 1 hour", "1-4 hours", ">4 hours"]
    instances = [make_instance(i, difficulty=labels[i % len(labels)]) for i in range(12)]
    monkeypatch.setattr(swebench_adapter, "_load_raw_dataset", lambda split: instances)
    return instances


# ---------------------------------------------------------------- mapping

def test_instance_maps_to_codetask():
    instance = make_instance(difficulty="15 min - 1 hour")
    task = swebench_instance_to_codetask(instance)
    assert isinstance(task, CodeTask)
    assert task.task_id == instance["instance_id"]
    assert task.repo == "astropy/astropy"
    assert task.description == instance["problem_statement"]
    assert task.difficulty == TaskDifficulty.MEDIUM
    assert task.test_file == TEST_FILE_PLACEHOLDER
    assert task.reference_solution == REFERENCE_SOLUTION_PLACEHOLDER
    assert "swebench" in task.tags
    assert "astropy/astropy" in task.tags
    assert "medium" in task.tags
    assert f"base_commit:{instance['base_commit']}" in task.tags


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("<15 min fix", TaskDifficulty.EASY),
        ("15 min - 1 hour", TaskDifficulty.MEDIUM),
        ("1-4 hours", TaskDifficulty.HARD),
        (">4 hours", TaskDifficulty.HARD),
        ("easy", TaskDifficulty.EASY),
        ("HARD", TaskDifficulty.HARD),
        (None, TaskDifficulty.MEDIUM),
        ("something new", TaskDifficulty.MEDIUM),
    ],
)
def test_difficulty_mapping(raw, expected):
    assert map_swebench_difficulty(raw) == expected


# ------------------------------------------------------------ no leakage

def test_codetask_contains_no_gold_data():
    task = swebench_instance_to_codetask(make_instance())
    dumped = json.dumps(task.model_dump(mode="json"))
    assert "SECRET GOLD PATCH" not in dumped
    assert "SECRET TEST PATCH" not in dumped
    assert "FAIL_TO_PASS" not in dumped
    assert "PASS_TO_PASS" not in dumped
    assert "test_fits_read" not in dumped


def test_agent_prompt_payload_excludes_hidden_fields():
    instance = make_instance()
    payload = agent_prompt_payload(instance)
    for field in HIDDEN_FIELDS:
        assert field not in payload
    dumped = json.dumps(payload)
    assert "SECRET GOLD PATCH" not in dumped
    assert "SECRET TEST PATCH" not in dumped
    # allowed fields are present
    assert payload["task_id"] == instance["instance_id"]
    assert payload["repo"] == instance["repo"]
    assert payload["base_commit"] == instance["base_commit"]
    assert payload["description"] == instance["problem_statement"]


def test_extract_hidden_reference_keeps_gold_for_sanity_checks():
    hidden = extract_hidden_reference(make_instance())
    assert hidden["patch"] == GOLD_PATCH
    assert hidden["test_patch"] == GOLD_TEST_PATCH
    assert "never" in hidden["_note"].lower()


# --------------------------------------------------------------- loading

def test_load_limit(fake_dataset):
    assert len(load_swebench_verified(limit=5)) == 5
    assert len(load_swebench_verified(limit=30)) == len(fake_dataset)  # capped by data
    assert len(load_swebench_verified()) == len(fake_dataset)


def test_load_invalid_limit(fake_dataset):
    with pytest.raises(ValueError):
        load_swebench_verified(limit=0)


def test_load_difficulty_filter(fake_dataset):
    easy = load_swebench_verified(difficulty="easy")
    assert easy and all(i["difficulty"] == "<15 min fix" for i in easy)
    hard = load_swebench_verified(difficulty="1-4 hours")  # raw label accepted too
    assert hard and all(
        map_swebench_difficulty(i["difficulty"]) == TaskDifficulty.HARD for i in hard
    )


# ---------------------------------------------------------- sample files

def test_write_swebench_sample_default_limit(fake_dataset, tmp_path):
    out = tmp_path / "data" / "sample.jsonl"
    records = write_swebench_sample(out)
    assert len(records) == 5  # default limit
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5

    for line in lines:
        record = json.loads(line)
        task = record["task"]
        # agent-safe task: placeholders only, no gold text anywhere in it
        assert task["test_file"] == TEST_FILE_PLACEHOLDER
        assert task["reference_solution"] == REFERENCE_SOLUTION_PLACEHOLDER
        assert "SECRET GOLD PATCH" not in json.dumps(task)
        # gold data lives only in the clearly-marked hidden block
        assert record["hidden_reference"]["patch"] == GOLD_PATCH
        assert record["base_commit"]


def test_write_and_read_sample_roundtrip(fake_dataset, tmp_path):
    out = tmp_path / "sample.jsonl"
    written = write_swebench_sample(out, limit=3)
    assert read_swebench_sample(out) == written


# ------------------------------------------------------------ predictions

def test_predictions_jsonl_official_format(tmp_path):
    out = tmp_path / "predictions" / "preds.jsonl"
    predictions = [
        {
            "instance_id": "astropy__astropy-1000",
            "model_name_or_path": "anote-code",
            "model_patch": "",
            "extra_key": "should be dropped",
        },
        {
            "instance_id": "astropy__astropy-1001",
            "model_name_or_path": "anote-code",
            "model_patch": "diff --git a/x b/x\n",
        },
    ]
    write_predictions_jsonl(predictions, out)

    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        row = json.loads(line)
        assert set(row.keys()) == set(PREDICTION_KEYS)
    assert json.loads(lines[0])["model_patch"] == ""


def test_predictions_jsonl_rejects_missing_keys(tmp_path):
    with pytest.raises(ValueError, match="model_patch"):
        write_predictions_jsonl(
            [{"instance_id": "x", "model_name_or_path": "y"}],
            tmp_path / "preds.jsonl",
        )
