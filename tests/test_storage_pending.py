import time
import pytest
from pathlib import Path


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    import app.storage as s
    monkeypatch.setattr(s, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.mark.asyncio
async def test_save_load_pending_roundtrip(tmp_data_dir):
    from app.storage import save_pending, load_pending

    await save_pending("u1", "이전 질문", "Qwen 답변")
    result = await load_pending("u1")

    assert result is not None
    assert result.prev_utterance == "이전 질문"
    assert result.answer == "Qwen 답변"


@pytest.mark.asyncio
async def test_load_pending_file_not_exists_returns_none(tmp_data_dir):
    from app.storage import load_pending

    result = await load_pending("nonexistent_user")
    assert result is None


@pytest.mark.asyncio
async def test_load_pending_within_ttl_returns_answer(tmp_data_dir):
    from app.storage import save_pending, load_pending

    await save_pending("u2", "질문", "답변")
    result = await load_pending("u2")
    assert result is not None
    assert result.answer == "답변"


@pytest.mark.asyncio
async def test_load_pending_ttl_expired_returns_none(tmp_data_dir, monkeypatch):
    from app import storage

    await storage.save_pending("u3", "질문", "답변")

    # TTL을 초과한 과거 시간으로 패치
    monkeypatch.setattr(storage, "PENDING_TTL", 0)

    result = await storage.load_pending("u3")
    assert result is None

    # 만료된 파일이 삭제됐는지 확인
    path = tmp_data_dir / "pending" / "u3.txt"
    assert not path.exists()


@pytest.mark.asyncio
async def test_clear_pending_removes_file(tmp_data_dir):
    from app.storage import save_pending, clear_pending

    await save_pending("u4", "질문", "답변")
    await clear_pending("u4")

    path = tmp_data_dir / "pending" / "u4.txt"
    assert not path.exists()


@pytest.mark.asyncio
async def test_save_load_pending_multiline_answer(tmp_data_dir):
    """answer에 개행이 포함돼도 올바르게 저장/로드."""
    from app.storage import save_pending, load_pending

    multiline = "첫째 줄\n둘째 줄\n셋째 줄"
    await save_pending("u5", "질문", multiline)
    result = await load_pending("u5")

    assert result is not None
    assert result.answer == multiline
