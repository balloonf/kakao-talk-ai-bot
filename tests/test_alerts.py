import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_send_alert_no_operator_id(monkeypatch):
    """OPERATOR_CHAT_ID 미설정 시 Bot 호출 없이 로그만."""
    import app.alerts as alerts
    monkeypatch.setattr(alerts, "OPERATOR_CHAT_ID", None)

    with patch("app.alerts.Bot") as mock_bot_cls:
        await alerts.send_alert("테스트 오류")
        mock_bot_cls.assert_not_called()


@pytest.mark.asyncio
async def test_send_alert_sends_message(monkeypatch):
    """OPERATOR_CHAT_ID 설정 시 텔레그램 메시지 전송."""
    import app.alerts as alerts
    monkeypatch.setattr(alerts, "OPERATOR_CHAT_ID", "12345")

    mock_bot = AsyncMock()
    mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
    mock_bot.__aexit__ = AsyncMock(return_value=False)

    with patch("app.alerts.Bot", return_value=mock_bot):
        await alerts.send_alert("Qwen 세션 만료")

    mock_bot.send_message.assert_called_once()
    call_kwargs = mock_bot.send_message.call_args
    assert "12345" in str(call_kwargs)
    assert "Qwen 세션 만료" in str(call_kwargs)


@pytest.mark.asyncio
async def test_send_alert_bot_failure_doesnt_raise(monkeypatch):
    """Bot 전송 실패해도 예외 전파 없음."""
    import app.alerts as alerts
    monkeypatch.setattr(alerts, "OPERATOR_CHAT_ID", "12345")

    mock_bot = AsyncMock()
    mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
    mock_bot.__aexit__ = AsyncMock(return_value=False)
    mock_bot.send_message = AsyncMock(side_effect=Exception("네트워크 오류"))

    with patch("app.alerts.Bot", return_value=mock_bot):
        await alerts.send_alert("테스트")  # 예외 없이 완료되어야 함


@pytest.mark.asyncio
async def test_gemini_ask_sends_alert_on_error(monkeypatch):
    """Gemini 오류 시 send_alert 호출 확인."""
    import app.gemini as g
    import app.alerts as alerts

    def _fail(ctx):
        raise RuntimeError("API 오류")

    alert_called = {}

    async def capture_alert(msg):
        alert_called["msg"] = msg

    monkeypatch.setattr(g, "_call_gemini", _fail)
    monkeypatch.setattr(alerts, "send_alert", capture_alert)
    monkeypatch.setattr(g, "send_alert", capture_alert)

    result = await g.ask("테스트")

    assert "Gemini 응답 실패" in result
    assert "msg" in alert_called
    assert "API 오류" in alert_called["msg"]
