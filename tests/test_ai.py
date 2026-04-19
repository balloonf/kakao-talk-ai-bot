import pytest


@pytest.mark.asyncio
async def test_respond_returns_fallback_on_timeout(monkeypatch):
    """Claude 타임아웃 시 fallback 메시지 반환."""
    import asyncio
    from app import ai
    from app.config import FALLBACK_MSG

    async def fake_call(system_text, user_content):
        raise asyncio.TimeoutError

    monkeypatch.setattr(ai, "_call_claude", fake_call)
    result = await ai.respond("안녕", "", "", "")
    assert result == FALLBACK_MSG


@pytest.mark.asyncio
async def test_respond_returns_text_on_success(monkeypatch):
    """Claude 정상 응답 시 텍스트 반환."""
    from app import ai

    async def fake_call(system_text, user_content):
        return "안녕하세요!"

    monkeypatch.setattr(ai, "_call_claude", fake_call)
    result = await ai.respond("안녕", "", "", "")
    assert result == "안녕하세요!"


@pytest.mark.asyncio
async def test_respond_includes_history_and_summary(monkeypatch):
    """history, summary, knowledge_chunks가 user_content에 포함됨."""
    from app import ai
    captured = {}

    async def fake_call(system_text, user_content):
        captured["system"] = system_text
        captured["user"] = user_content
        return "ok"

    monkeypatch.setattr(ai, "_call_claude", fake_call)
    await ai.respond("질문", "오늘 대화", "요약 내용", "지식 청크")
    assert "요약 내용" in captured["user"]
    assert "오늘 대화" in captured["user"]
    assert "질문" in captured["user"]
    assert "지식 청크" in captured["system"]


@pytest.mark.asyncio
async def test_respond_handles_other_exception(monkeypatch):
    """예외 발생 시 fallback 반환 (타임아웃 외 에러도)."""
    from app import ai
    from app.config import FALLBACK_MSG

    async def fake_call(system_text, user_content):
        raise ValueError("API 에러")

    monkeypatch.setattr(ai, "_call_claude", fake_call)
    result = await ai.respond("안녕", "", "", "")
    assert result == FALLBACK_MSG


@pytest.mark.asyncio
async def test_summarize_returns_text(monkeypatch):
    """summarize 정상 동작."""
    import asyncio
    from app import ai

    def fake_create(**kwargs):
        class FakeContent:
            text = "요약 결과입니다."
        class FakeResponse:
            content = [FakeContent()]
        return FakeResponse()

    monkeypatch.setattr(ai._client.messages, "create", fake_create)
    result = await ai.summarize("대화 내용")
    assert "요약" in result


@pytest.mark.asyncio
async def test_summarize_returns_fallback_on_error(monkeypatch):
    from app import ai

    def fake_create(**kwargs):
        raise RuntimeError("API 오류")

    monkeypatch.setattr(ai._client.messages, "create", fake_create)
    result = await ai.summarize("대화 내용")
    assert result == "(요약 실패)"
