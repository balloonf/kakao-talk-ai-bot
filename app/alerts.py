import logging

from telegram import Bot

from app.config import TELEGRAM_BOT_TOKEN, OPERATOR_CHAT_ID

logger = logging.getLogger(__name__)


async def send_alert(message: str) -> None:
    """운영자에게 텔레그램 알림 전송. OPERATOR_CHAT_ID 미설정 시 로그만 남김."""
    if not OPERATOR_CHAT_ID:
        logger.warning("OPERATOR_CHAT_ID 미설정 — 알림 전송 생략: %s", message)
        return
    try:
        async with Bot(token=TELEGRAM_BOT_TOKEN) as bot:
            await bot.send_message(chat_id=OPERATOR_CHAT_ID, text=f"⚠️ 봇 알림\n\n{message}")
    except Exception as e:
        logger.error("알림 전송 실패: %s", e)
