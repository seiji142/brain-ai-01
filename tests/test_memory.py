import pytest
import json
import os
import shutil
from pathlib import Path
from ai_architect.pipelines.ingest import ingest_episode, validate_episode
from ai_architect.core.memory import save_episode, load_episode, list_episodes
from ai_architect.core.utils import redact_text, new_id, now_iso, date_range_filter_ok

TEST_DIR = Path("./memory_test")

@pytest.fixture(autouse=True)
def setup_teardown():
    os.environ["MEMORY_ROOT"] = str(TEST_DIR / "memory")
    os.environ["LOG_DIR"] = str(TEST_DIR / "logs")
    os.environ["CHROMA_PERSIST_DIR"] = str(TEST_DIR / "chroma")
    os.environ["APP_ENV"] = "test"
    yield
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)

def test_redact_text():
    text = "Contact: user@example.com, token sk-abc123def456ghi789"
    result = redact_text(text)
    assert "[REDACTED]" in result
    assert "user@example.com" not in result

def test_new_id():
    id1 = new_id("ep_")
    id2 = new_id("ep_")
    assert id1.startswith("ep_")
    assert id1 != id2

def test_now_iso_format():
    ts = now_iso()
    assert ts.endswith("Z")
    assert "T" in ts

def test_validate_episode_valid():
    ep = {
        "project": "test",
        "source_type": "meeting",
        "author": "tester",
        "title": "Test",
        "summary": "Test summary",
        "timestamp": now_iso(),
    }
    ok, msg = validate_episode(ep)
    assert ok
    assert msg == ""

def test_validate_episode_invalid():
    ep = {"project": "test"}
    ok, msg = validate_episode(ep)
    assert not ok
    assert "Missing required" in msg

def test_ingest_episode():
    ep = {
        "project": "test-project",
        "source_type": "meeting",
        "author": "tester",
        "title": "Test decision",
        "summary": "This is a test decision",
        "timestamp": now_iso(),
        "decisions": [{"text": "Use Python", "owner": "tester"}],
        "evidence": [{"type": "doc", "url_or_path": "test.md", "excerpt": "test"}],
        "tags": ["test"],
    }
    res = ingest_episode(ep)
    assert res["ok"] is True
    assert "episode_id" in res
    assert res["episode_id"].startswith("ep_")

def test_save_and_load_episode():
    ep = {
        "id": "ep_test_001",
        "project": "test",
        "title": "Test",
        "summary": "Test",
        "timestamp": now_iso(),
        "source_type": "chat",
        "author": "tester",
    }
    save_episode(ep)
    loaded = load_episode("ep_test_001")
    assert loaded["id"] == "ep_test_001"
    assert loaded["project"] == "test"

def test_list_episodes():
    ep1 = {"id": "ep_list_a", "project": "proj1", "title": "A", "summary": "A", "timestamp": now_iso(), "source_type": "chat", "author": "t"}
    ep2 = {"id": "ep_list_b", "project": "proj2", "title": "B", "summary": "B", "timestamp": now_iso(), "source_type": "chat", "author": "t"}
    save_episode(ep1)
    save_episode(ep2)
    proj1_eps = list_episodes(project="proj1")
    assert len(proj1_eps) == 1
    assert proj1_eps[0]["id"] == "ep_list_a"

def test_date_range_filter():
    ts = "2026-01-15T10:00:00Z"
    assert date_range_filter_ok(ts, "2026-01-01T00:00:00Z", "2026-02-01T00:00:00Z") is True
    assert date_range_filter_ok(ts, "2026-02-01T00:00:00Z", None) is False
    assert date_range_filter_ok(ts, None, "2026-01-01T00:00:00Z") is False

def test_redact_episode_removes_pii():
    from ai_architect.core.redact import redact_episode
    ep = {
        "title": "Contact user@example.com",
        "summary": "Token: sk-abc123def456ghi789xyz",
            "decisions": [{"text": "use api key sk-abc123def456ghi789xyz"}],
        "actions": [],
        "risks": [],
        "evidence": [{"type": "email", "url_or_path": "", "excerpt": "user@test.com"}],
        "embedding_text": "test",
    }
    redacted = redact_episode(ep)
    assert "[REDACTED]" in redacted["title"]
    assert "[REDACTED]" in redacted["summary"]
    assert "[REDACTED]" in redacted["decisions"][0]["text"]
    assert "[REDACTED]" in redacted["evidence"][0]["excerpt"]
