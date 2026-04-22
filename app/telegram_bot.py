from collections import defaultdict
import asyncio
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from app import ai, knowledge, storage
from app.knowledge import load_rules
from app import gemini
from app.config import TELEGRAM_BOT_TOKEN, FALLBACK_MSG, BOT_NAME
from app.scheduler import create_scheduler, get_scheduler

logger = logging.getLogger(__name__)

_user_locks: dict[str, asyncio.Lock] = defaultdict(lambda: asyncio.Lock())


_ERROR_PATTERNS = [
    "(Gemini 응답 실패",
    "(Qwen 응답 실패",
    "(응답을 받지 못했습니다",
    "건너뛰기",
    "생각이 끝났습니다",
]
_MAX_HISTORY_TURNS = 5   # 최근 N개 교환만 포함
_MAX_HISTORY_CHARS = 1500  # 이 길이 초과 시 자동 요약


def _extract_user_line(block: str) -> str:
    """블록에서 사용자 발화 줄만 추출."""
    for line in block.splitlines():
        if "사용자" in line and "]: " in line:
            return line.split("]: ", 1)[-1].strip()
    return block


def _trim_history(history: str) -> str:
    """오류 응답 제거 + 중복 질문 제거 + 최근 N개 교환만 유지."""
    if not history:
        return ""
    blocks = history.strip().split("\n\n")
    # 오류 응답이 포함된 블록 제거
    clean = [b for b in blocks if not any(p in b for p in _ERROR_PATTERNS)]
    # 중복 질문 제거 — 같은 사용자 발화가 여러 번이면 마지막만 유지
    seen: dict[str, int] = {}
    for i, block in enumerate(clean):
        key = _extract_user_line(block)
        seen[key] = i  # 마지막 인덱스 덮어쓰기
    deduped = [clean[i] for i in sorted(seen.values())]
    # 최근 N개만
    recent = deduped[-_MAX_HISTORY_TURNS:]
    return "\n\n".join(recent)


def _build_context(utterance: str, knowledge: str, history: str, summary: str) -> str:
    parts = [f"[시스템]\n{load_rules()}"]
    if summary:
        parts.append(f"[이전 대화내용 요약]\n{summary}")
    if history:
        parts.append(f"[이전 대화내용]\n{history}")
    if knowledge:
        parts.append(f"[관련 정보]\n{knowledge}")
    parts.append(f"[사용자 메시지]\n{utterance}")
    return "\n\n".join(parts)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    utterance = update.message.text

    if not knowledge.model_ready:
        await update.message.reply_text(FALLBACK_MSG)
        return

    await context.bot.send_chat_action(update.effective_chat.id, "typing")

    async with _user_locks[user_id]:
        knowledge_str, history, summary = await asyncio.gather(
            knowledge.search(utterance),
            storage.load_today(user_id),
            storage.load_summary(user_id),
        )
        trimmed = _trim_history(history)
        if len(trimmed) > _MAX_HISTORY_CHARS:
            try:
                result = await ai.summarize(trimmed)
                if result and "(요약 실패)" not in result:
                    trimmed = f"(자동 요약)\n{result}"
                else:
                    trimmed = trimmed[-_MAX_HISTORY_CHARS:]
            except Exception:
                trimmed = trimmed[-_MAX_HISTORY_CHARS:]
        conv_context = _build_context(utterance, knowledge_str, trimmed, summary)

        answer = await gemini.ask(conv_context)

        if not answer:
            answer = "(응답을 받지 못했습니다. 다시 시도해 주세요.)"

        # 텔레그램 메시지 최대 4096자 — 초과 시 분할 전송
        MAX_LEN = 4096
        for i in range(0, len(answer), MAX_LEN):
            await update.message.reply_text(answer[i:i + MAX_LEN])
        await storage.append_message(user_id, utterance, answer)


async def post_init(application):
    logger.info("Starting %s ...", BOT_NAME)
    await asyncio.to_thread(knowledge.init_knowledge)
    create_scheduler().start()


async def post_shutdown(application):
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)


def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
