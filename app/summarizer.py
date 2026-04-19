import logging
from datetime import date, timedelta

from app import ai, storage

logger = logging.getLogger(__name__)


async def run_daily_summary() -> None:
    yesterday = date.today() - timedelta(days=1)
    user_ids = await storage.get_active_users(yesterday)

    if not user_ids:
        logger.info("daily_summary: 어제 대화한 사용자 없음")
        return

    for user_id in user_ids:
        try:
            conversation = await storage.load_conversation(user_id, yesterday)
            if not conversation.strip():
                continue
            summary = await ai.summarize(conversation)
            await storage.append_summary(user_id, yesterday, summary)
            logger.info("daily_summary: %s 요약 완료", user_id)
        except Exception:
            logger.exception("daily_summary: %s 요약 실패 — 스킵", user_id)
