import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_update(text="안녕하세요", user_id="12345"):
    """Fake telegram Update 객체 생성."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.effective_chat.id = "chat_1"
    return update


def _make_context():
    context = MagicMock()
    context.bot.send_chat_action = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_handle_message_model_not_ready(monkeypatch):
    """knowledge.model_ready=False 이면 FALLBACK_MSG 반환."""
    import app.telegram_bot as tb
    import app.knowledge as k

    monkeypatch.setattr(k, "model_ready", False)

    update = _make_update()
    await tb.handle_message(update, _make_context())

    update.message.reply_text.assert_called_once()
    args = update.message.reply_text.call_args[0]
    assert args[0]  # FALLBACK_MSG 전달됨


@pytest.mark.asyncio
async def test_handle_message_happy_path(monkeypatch):
    """정상 메시지 처리: Qwen 응답을 텔레그램으로 전송하고 저장."""
    import app.telegram_bot as tb
    import app.knowledge as k
    import app.storage as s
    import app.qwen_playwright as qp

    monkeypatch.setattr(k, "model_ready", True)
    monkeypatch.setattr(k, "search", AsyncMock(return_value=[]))
    monkeypatch.setattr(s, "load_today", AsyncMock(return_value=""))
    monkeypatch.setattr(s, "load_summary", AsyncMock(return_value=""))
    monkeypatch.setattr(s, "append_message", AsyncMock())
    monkeypatch.setattr(qp, "ask", AsyncMock(return_value="테스트 응답입니다"))

    update = _make_update(text="질문", user_id="user1")
    await tb.handle_message(update, _make_context())

    update.message.reply_text.assert_called_once_with("테스트 응답입니다")
    s.append_message.assert_called_once_with("user1", "질문", "테스트 응답입니다")


@pytest.mark.asyncio
async def test_handle_message_empty_qwen_response(monkeypatch):
    """Qwen이 빈 문자열 반환 시 fallback 메시지 전송."""
    import app.telegram_bot as tb
    import app.knowledge as k
    import app.storage as s
    import app.qwen_playwright as qp

    monkeypatch.setattr(k, "model_ready", True)
    monkeypatch.setattr(k, "search", AsyncMock(return_value=[]))
    monkeypatch.setattr(s, "load_today", AsyncMock(return_value=""))
    monkeypatch.setattr(s, "load_summary", AsyncMock(return_value=""))
    monkeypatch.setattr(s, "append_message", AsyncMock())
    monkeypatch.setattr(qp, "ask", AsyncMock(return_value=""))

    update = _make_update()
    await tb.handle_message(update, _make_context())

    sent = update.message.reply_text.call_args[0][0]
    assert "응답을 받지 못했습니다" in sent


@pytest.mark.asyncio
async def test_handle_message_qwen_exception_doesnt_crash(monkeypatch):
    """qwen_playwright.ask()가 오류 문자열 반환해도 봇이 계속 동작."""
    import app.telegram_bot as tb
    import app.knowledge as k
    import app.storage as s
    import app.qwen_playwright as qp

    monkeypatch.setattr(k, "model_ready", True)
    monkeypatch.setattr(k, "search", AsyncMock(return_value=[]))
    monkeypatch.setattr(s, "load_today", AsyncMock(return_value=""))
    monkeypatch.setattr(s, "load_summary", AsyncMock(return_value=""))
    monkeypatch.setattr(s, "append_message", AsyncMock())
    monkeypatch.setattr(qp, "ask", AsyncMock(return_value="(Qwen 응답 실패: [RuntimeError] 오류)"))

    update = _make_update()
    await tb.handle_message(update, _make_context())

    sent = update.message.reply_text.call_args[0][0]
    assert "Qwen 응답 실패" in sent


@pytest.mark.asyncio
async def test_qwen_ask_new_signature(monkeypatch):
    """ask(conv_context) -> str 시그니처 검증."""
    import app.qwen_playwright as qp

    monkeypatch.setattr(qp, "_fetch_answer", AsyncMock(return_value="직접 반환"))

    result = await qp.ask("컨텍스트 문자열")
    assert result == "직접 반환"
