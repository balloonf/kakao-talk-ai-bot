import asyncio
import logging
import re
from collections import defaultdict

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse

from app import knowledge, qwen_playwright, storage
from app.config import FALLBACK_MSG, KAKAO_SECRET_TOKEN

logger = logging.getLogger(__name__)
router = APIRouter()

_user_locks: dict[str, asyncio.Lock] = defaultdict(lambda: asyncio.Lock())
_qwen_lock = asyncio.Lock()
_LOCK_TIMEOUT = 0.5
MAX_CONTEXT_CHARS = 4000
WAIT_MSG = "잠시 기다려주세요. 답변을 준비 중입니다."


def _sanitize_user_id(user_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", user_id)


def _kakao_response(text: str) -> dict:
    return {
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": text}}]},
    }


def _build_context(utterance: str, history: str, summary: str, knowledge_chunks: str) -> str:
    """knowledge + utterance 보호, 나머지 budget으로 history 채움."""
    core_parts = []
    if knowledge_chunks:
        core_parts.append(f"[참고 정보]\n{knowledge_chunks}")
    if summary:
        core_parts.append(f"[이전 대화 요약]\n{summary}")
    core_parts.append(f"사용자 질문: {utterance}")
    core_text = "\n\n".join(core_parts)

    budget = MAX_CONTEXT_CHARS - len(core_text) - 2
    if history and budget > 100:
        return f"[오늘 대화]\n{history[-budget:]}\n\n{core_text}"
    return core_text


async def _ask_with_lock(user_id: str, utterance: str, conv_context: str) -> None:
    async with _qwen_lock:
        await qwen_playwright.ask(user_id, utterance, conv_context)


@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {KAKAO_SECRET_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not knowledge.model_ready:
        return JSONResponse(_kakao_response(FALLBACK_MSG))

    try:
        body = await request.json()
        user_request = body["userRequest"]
        user_id = _sanitize_user_id(user_request["user"]["id"])
        utterance: str = user_request["utterance"]
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"잘못된 요청 형식: {e}")

    lock = _user_locks[user_id]
    try:
        await asyncio.wait_for(lock.acquire(), timeout=_LOCK_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning("webhook: lock timeout for user %s", user_id)
        return JSONResponse(_kakao_response(FALLBACK_MSG))

    try:
        history, summary, knowledge_chunks = await asyncio.gather(
            storage.load_today(user_id),
            storage.load_summary(user_id),
            knowledge.search(utterance),
        )
        conv_context = _build_context(utterance, history, summary, knowledge_chunks)

        pending = await storage.load_pending(user_id)
        if pending:
            await storage.clear_pending(user_id)
            await storage.append_message(user_id, pending.prev_utterance, pending.answer)
            background_tasks.add_task(_ask_with_lock, user_id, utterance, conv_context)
            return JSONResponse(_kakao_response(pending.answer))

        background_tasks.add_task(_ask_with_lock, user_id, utterance, conv_context)
        return JSONResponse(_kakao_response(WAIT_MSG))
    finally:
        lock.release()
