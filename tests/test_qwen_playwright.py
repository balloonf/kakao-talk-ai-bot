import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_ask_returns_answer_on_success(monkeypatch):
    """Playwright 성공 시 응답 문자열 직접 반환."""
    import app.qwen_playwright as qp

    monkeypatch.setattr(qp, "_fetch_answer", AsyncMock(return_value="Qwen 응답"))

    result = await qp.ask("테스트 컨텍스트")

    assert result == "Qwen 응답"


@pytest.mark.asyncio
async def test_ask_returns_error_string_on_exception(monkeypatch):
    """Playwright 예외 시 오류 메시지 문자열 반환 (예외 전파 없음)."""
    import app.qwen_playwright as qp

    monkeypatch.setattr(qp, "_fetch_answer", AsyncMock(side_effect=RuntimeError("네트워크 오류")))

    result = await qp.ask("테스트 컨텍스트")

    assert "Qwen 응답 실패" in result
    assert "RuntimeError" in result


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
