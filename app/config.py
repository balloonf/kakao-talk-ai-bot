import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
MODEL: str = os.getenv("MODEL", "claude-haiku-4-5-20251001")
BOT_NAME: str = os.getenv("BOT_NAME", "AI 봇")
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Seoul")
DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data"))
OPERATOR_CHAT_ID: str | None = os.getenv("OPERATOR_CHAT_ID")
FALLBACK_MSG: str = "잠시 후 다시 시도해 주세요."
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
