import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_ask_returns_answer_on_success(monkeypatch):
    """API 성공 시 응답 문자열 반환."""
    import app.gemini as g

    monkeypatch.setattr(g, "_call_gemini", lambda ctx: "Gemini 응답")

    result = await g.ask("테스트 컨텍스트")

    assert result == "Gemini 응답"


@pytest.mark.asyncio
async def test_ask_returns_error_string_on_exception(monkeypatch):
    """API 예외 시 오류 문자열 반환 (예외 전파 없음)."""
    import app.gemini as g

    def _fail(ctx):
        raise RuntimeError("API 오류")

    monkeypatch.setattr(g, "_call_gemini", _fail)
    monkeypatch.setattr(g, "send_alert", AsyncMock())

    result = await g.ask("테스트 컨텍스트")

    assert "Gemini 응답 실패" in result
    assert "RuntimeError" in result


@pytest.mark.asyncio
async def test_ask_calls_send_alert_on_error(monkeypatch):
    """에러 시 send_alert 호출 확인."""
    import app.gemini as g

    def _fail(ctx):
        raise ValueError("잘못된 키")

    mock_alert = AsyncMock()
    monkeypatch.setattr(g, "_call_gemini", _fail)
    monkeypatch.setattr(g, "send_alert", mock_alert)

    await g.ask("테스트 컨텍스트")

    mock_alert.assert_awaited_once()
    assert "Gemini 오류" in mock_alert.call_args[0][0]
