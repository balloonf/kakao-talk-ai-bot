import asyncio
import os
import tempfile
from pathlib import Path

import pytest

# 테스트용 환경변수 — 실제 API 호출 없음
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-bot-token")
os.environ.setdefault("MODEL", "claude-haiku-4-5-20251001")
os.environ.setdefault("BOT_NAME", "테스트봇")


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """각 테스트마다 격리된 data 디렉터리."""
    import app.config as cfg
    import app.storage as storage_mod

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage_mod, "DATA_DIR", tmp_path, raising=False)
    # storage 내 _conv_dir 등이 DATA_DIR을 직접 참조하므로 함수 재바인딩 불필요
    # (모듈 속성을 통해 접근)
    return tmp_path


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
