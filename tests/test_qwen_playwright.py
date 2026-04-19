import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_ask_saves_pending_on_success(monkeypatch):
    """Playwright 성공 시 save_pending 호출."""
    import app.qwen_playwright as qp
    import app.storage as s

    monkeypatch.setattr(qp, "_fetch_answer", AsyncMock(return_value="Qwen 응답"))

    saved = {}

    async def capture_save(uid, prev_utterance, answer):
        saved["uid"] = uid
        saved["prev_utterance"] = prev_utterance
        saved["answer"] = answer

    monkeypatch.setattr(s, "save_pending", capture_save)

    await qp.ask("user1", "안녕", "컨텍스트")

    assert saved["uid"] == "user1"
    assert saved["prev_utterance"] == "안녕"
    assert saved["answer"] == "Qwen 응답"


@pytest.mark.asyncio
async def test_ask_saves_error_message_on_exception(monkeypatch):
    """Playwright 예외 시 오류 메시지를 pending에 저장 (silent drop 없음)."""
    import app.qwen_playwright as qp
    import app.storage as s

    monkeypatch.setattr(qp, "_fetch_answer", AsyncMock(side_effect=RuntimeError("네트워크 오류")))

    saved = {}

    async def capture_save(uid, prev_utterance, answer):
        saved["answer"] = answer

    monkeypatch.setattr(s, "save_pending", capture_save)

    await qp.ask("user1", "안녕", "컨텍스트")

    assert "Qwen 응답 실패" in saved["answer"]


@pytest.mark.asyncio
async def test_fetch_answer_session_expired_raises(monkeypatch):
    """로그인 페이지 리다이렉트 감지 시 RuntimeError."""
    import app.qwen_playwright as qp

    class FakePage:
        url = "https://chat.qwen.ai/login"
        async def goto(self, *a, **kw): pass
        async def wait_for_timeout(self, *a): pass

    class FakeContext:
        async def new_page(self): return FakePage()

    class FakeBrowser:
        async def new_context(self, **kw): return FakeContext()
        async def close(self): pass

    class FakeP:
        chromium = type("C", (), {
            "launch": AsyncMock(return_value=FakeBrowser())
        })()

    class FakePlaywright:
        async def __aenter__(self): return FakeP()
        async def __aexit__(self, *a): pass

    monkeypatch.setattr(qp, "async_playwright", lambda: FakePlaywright())

    with pytest.raises(RuntimeError, match="세션 만료"):
        await qp._fetch_answer("테스트 컨텍스트")
