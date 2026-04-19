from collections import defaultdict
import asyncio
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from app import knowledge, storage
from app import qwen_playwright
from app.config import TELEGRAM_BOT_TOKEN, FALLBACK_MSG, BOT_NAME
from app.scheduler import create_scheduler, get_scheduler

logger = logging.getLogger(__name__)

_user_locks: dict[str, asyncio.Lock] = defaultdict(lambda: asyncio.Lock())


def _build_context(utterance: str, history: str, summary: str, knowledge_chunks: list[str]) -> str:
    parts = []
    if summary:
        parts.append(f"[이전 대화 요약]\n{summary}")
    if history:
        parts.append(f"[오늘 대화]\n{history}")
    if knowledge_chunks:
        parts.append(f"[관련 정보]\n" + "\n".join(knowledge_chunks))
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
        history, summary, knowledge_chunks = await asyncio.gather(
            storage.load_today(user_id),
            storage.load_summary(user_id),
            knowledge.search(utterance),
        )
        conv_context = _build_context(utterance, history, summary, knowledge_chunks)

        answer = await qwen_playwright.ask(conv_context)

        if not answer:
            answer = "(응답을 받지 못했습니다. 다시 시도해 주세요.)"

        await update.message.reply_text(answer)
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
