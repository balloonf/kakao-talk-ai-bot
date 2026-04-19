import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
KAKAO_SECRET_TOKEN: str = os.environ["KAKAO_SECRET_TOKEN"]
MODEL: str = os.getenv("MODEL", "claude-haiku-4-5-20251001")
BOT_NAME: str = os.getenv("BOT_NAME", "AI 봇")
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Seoul")
DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data"))
FALLBACK_MSG: str = "잠시 후 다시 시도해 주세요."
CLAUDE_TIMEOUT: float = 2.0
