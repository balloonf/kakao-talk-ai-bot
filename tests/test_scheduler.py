from datetime import date, timedelta

import pytest


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path, monkeypatch):
    import app.storage as s
    import app.config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    monkeypatch.setattr(s, "DATA_DIR", tmp_path)


@pytest.mark.asyncio
async def test_run_daily_summary_no_users(monkeypatch):
    """어제 대화한 사용자가 없으면 아무것도 하지 않음."""
    import app.ai as ai
    called = []

    async def fake_summarize(conv):
        called.append(conv)
        return "요약"

    monkeypatch.setattr(ai, "summarize", fake_summarize)
    from app.summarizer import run_daily_summary
    await run_daily_summary()
    assert called == []


@pytest.mark.asyncio
async def test_run_daily_summary_with_user(tmp_path, monkeypatch):
    """어제 대화가 있는 사용자는 요약 생성 후 저장."""
    import app.storage as s
    import app.ai as ai
    import app.config as cfg

    yesterday = date.today() - timedelta(days=1)
    uid = "testuser"
    conv_path = tmp_path / "conversations" / uid / f"{yesterday.isoformat()}.md"
    conv_path.parent.mkdir(parents=True)
    conv_path.write_text("대화 내용", encoding="utf-8")

    async def fake_summarize(conv):
        return "요약 결과"

    monkeypatch.setattr(ai, "summarize", fake_summarize)
    from app.summarizer import run_daily_summary
    await run_daily_summary()

    summary = await s.load_summary(uid)
    assert "요약 결과" in summary
    assert yesterday.isoformat() in summary


@pytest.mark.asyncio
async def test_run_daily_summary_skips_on_error(tmp_path, monkeypatch):
    """요약 실패 시 해당 사용자만 스킵하고 계속 진행."""
    import app.storage as s
    import app.ai as ai

    yesterday = date.today() - timedelta(days=1)
    for uid in ["user_fail", "user_ok"]:
        path = tmp_path / "conversations" / uid / f"{yesterday.isoformat()}.md"
        path.parent.mkdir(parents=True)
        path.write_text("대화", encoding="utf-8")

    call_count = [0]

    async def fake_summarize(conv):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("API 오류")
        return "성공 요약"

    monkeypatch.setattr(ai, "summarize", fake_summarize)
    from app.summarizer import run_daily_summary
    await run_daily_summary()  # 예외 발생해도 완료되어야 함
    assert call_count[0] == 2


@pytest.mark.asyncio
async def test_run_daily_summary_skips_empty_conversation(tmp_path, monkeypatch):
    """빈 대화 파일은 요약하지 않음."""
    import app.ai as ai

    yesterday = date.today() - timedelta(days=1)
    uid = "empty_user"
    path = tmp_path / "conversations" / uid / f"{yesterday.isoformat()}.md"
    path.parent.mkdir(parents=True)
    path.write_text("   ", encoding="utf-8")  # 공백만 있는 파일

    called = []

    async def fake_summarize(conv):
        called.append(conv)
        return "요약"

    monkeypatch.setattr(ai, "summarize", fake_summarize)
    from app.summarizer import run_daily_summary
    await run_daily_summary()
    assert called == []


def test_scheduler_job_registered():
    """APScheduler에 daily_summary 잡이 등록되어 있음."""
    from app.scheduler import create_scheduler
    from unittest.mock import patch
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.scheduler.DATA_DIR", Path(tmpdir)):
            scheduler = create_scheduler()
    job = scheduler.get_job("daily_summary")
    assert job is not None
