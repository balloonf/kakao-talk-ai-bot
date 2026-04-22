import asyncio
import logging

from google import genai

from app.alerts import send_alert
from app.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _call_gemini(conv_context: str) -> str:
    client = _get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=conv_context,
    )
    if hasattr(response, "prompt_feedback") and response.prompt_feedback:
        block = getattr(response.prompt_feedback, "block_reason", None)
        if block:
            raise RuntimeError(f"Gemini content blocked: {block}")
    return response.text


async def ask(conv_context: str) -> str:
    """Gemini API로 질문하고 응답 문자열을 반환."""
    try:
        return await asyncio.to_thread(_call_gemini, conv_context)
    except Exception as e:
        import traceback
        err_type = type(e).__name__
        err_msg = str(e) or "(메시지 없음)"
        logger.error(
            "gemini.ask failed: [%s] %s\n%s",
            err_type, err_msg, traceback.format_exc()
        )
        await send_alert(f"Gemini 오류 발생: [{err_type}] {err_msg}")
        return f"(Gemini 응답 실패: [{err_type}] {err_msg})"
