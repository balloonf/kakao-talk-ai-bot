from datetime import date, timedelta
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path, monkeypatch):
    import app.storage as s
    import app.config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    # storage 함수들이 DATA_DIR을 직접 사용하도록 재임포트 없이 패치
    monkeypatch.setattr(s, "DATA_DIR", tmp_path)
    yield


@pytest.mark.asyncio
async def test_load_today_no_file():
    from app.storage import load_today
    result = await load_today("user1")
    assert result == ""


@pytest.mark.asyncio
async def test_append_and_load_today(tmp_path):
    from app import storage as s
    import app.config as cfg
    # data dir already patched via autouse fixture

    await s.append_message("user1", "안녕", "안녕하세요!")
    content = await s.load_today("user1")
    assert "안녕" in content
    assert "안녕하세요!" in content


@pytest.mark.asyncio
async def test_append_message_creates_dir(tmp_path):
    from app import storage as s
    await s.append_message("new_user", "테스트", "응답")
    today = date.today().isoformat()
    # 파일이 생성되었는지 확인
    content = await s.load_today("new_user")
    assert "테스트" in content


@pytest.mark.asyncio
async def test_load_summary_no_file():
    from app.storage import load_summary
    result = await load_summary("user1")
    assert result == ""


@pytest.mark.asyncio
async def test_append_summary_and_load():
    from app import storage as s
    d = date.today() - timedelta(days=1)
    await s.append_summary("user1", d, "테스트 요약 내용")
    summary = await s.load_summary("user1")
    assert "테스트 요약 내용" in summary
    assert d.isoformat() in summary


@pytest.mark.asyncio
async def test_append_summary_idempotent():
    """같은 날짜 요약을 두 번 추가해도 이중 작성 안 됨."""
    from app import storage as s
    d = date.today() - timedelta(days=2)
    await s.append_summary("user1", d, "첫 번째 요약")
    await s.append_summary("user1", d, "두 번째 요약 — 저장되면 안 됨")
    summary = await s.load_summary("user1")
    assert summary.count(d.isoformat()) == 1
    assert "두 번째 요약" not in summary


@pytest.mark.asyncio
async def test_get_active_users_empty():
    from app.storage import get_active_users
    users = await get_active_users(date.today())
    assert users == []


@pytest.mark.asyncio
async def test_get_active_users_with_data():
    from app import storage as s
    await s.append_message("alice", "hello", "hi")
    users = await s.get_active_users(date.today())
    assert "alice" in users


@pytest.mark.asyncio
async def test_get_active_users_excludes_other_dates():
    from app import storage as s
    yesterday = date.today() - timedelta(days=1)
    await s.append_message("bob", "hello", "hi")  # today
    users = await s.get_active_users(yesterday)
    assert "bob" not in users
