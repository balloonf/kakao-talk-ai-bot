import asyncio
import logging
import re
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app import ai, knowledge, storage
from app.config import FALLBACK_MSG, KAKAO_SECRET_TOKEN

logger = logging.getLogger(__name__)
router = APIRouter()

_user_locks: dict[str, asyncio.Lock] = defaultdict(lambda: asyncio.Lock())
_LOCK_TIMEOUT = 0.5


def _sanitize_user_id(user_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", user_id)


def _kakao_response(text: str) -> dict:
    return {
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": text}}]},
    }


@router.post("/webhook")
async def webhook(request: Request) -> JSONResponse:
    # Authorization 검증
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {KAKAO_SECRET_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # cold start 중 요청 처리
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
        acquired = await asyncio.wait_for(lock.acquire(), timeout=_LOCK_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning("webhook: lock timeout for user %s", user_id)
        return JSONResponse(_kakao_response(FALLBACK_MSG))

    try:
        history, summary, knowledge_chunks = await asyncio.gather(
            storage.load_today(user_id),
            storage.load_summary(user_id),
            knowledge.search(utterance),
        )

        response_text = await ai.respond(utterance, history, summary, knowledge_chunks)
        await storage.append_message(user_id, utterance, response_text)
    finally:
        lock.release()

    return JSONResponse(_kakao_response(response_text))
