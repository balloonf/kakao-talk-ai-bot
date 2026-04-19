import asyncio
import re
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from app.config import DATA_DIR

PENDING_TTL = 600  # 10분


@dataclass
class PendingResult:
    prev_utterance: str
    answer: str


def _sanitize_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", value)


def _conv_dir(user_id: str) -> Path:
    return DATA_DIR / "conversations" / _sanitize_id(user_id)


def _summary_path(user_id: str) -> Path:
    return DATA_DIR / "summaries" / _sanitize_id(user_id) / "summary.md"


def _conv_path(user_id: str, d: date) -> Path:
    return _conv_dir(user_id) / f"{d.isoformat()}.md"


# ── sync helpers (run inside asyncio.to_thread) ──────────────────────────────

def _read_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _append_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def _write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ── public async API ─────────────────────────────────────────────────────────

async def load_today(user_id: str) -> str:
    path = _conv_path(user_id, date.today())
    return await asyncio.to_thread(_read_file, path)


async def load_summary(user_id: str) -> str:
    return await asyncio.to_thread(_read_file, _summary_path(user_id))


async def append_message(user_id: str, utterance: str, response: str) -> None:
    from datetime import datetime
    now = datetime.now().strftime("%H:%M")
    text = f"**[{now}] 사용자**: {utterance}\n**[{now}] 봇**: {response}\n\n"
    path = _conv_path(user_id, date.today())
    await asyncio.to_thread(_append_file, path, text)


async def load_conversation(user_id: str, d: date) -> str:
    path = _conv_path(user_id, d)
    return await asyncio.to_thread(_read_file, path)


async def append_summary(user_id: str, d: date, summary: str) -> None:
    path = _summary_path(user_id)
    existing = await asyncio.to_thread(_read_file, path)
    date_heading = f"## {d.isoformat()}"
    if date_heading in existing:
        return  # 이미 해당 날짜 요약 존재 — 이중 작성 방지
    entry = f"{date_heading}\n{summary}\n\n"
    await asyncio.to_thread(_append_file, path, entry)


async def save_pending(user_id: str, prev_utterance: str, answer: str) -> None:
    path = DATA_DIR / "pending" / f"{user_id}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"{int(time.time())}\n{prev_utterance}\n{answer}"
    await asyncio.to_thread(_write_file, path, content)


async def load_pending(user_id: str) -> PendingResult | None:
    path = DATA_DIR / "pending" / f"{user_id}.txt"
    if not path.exists():
        return None
    content = await asyncio.to_thread(_read_file, path)
    lines = content.split("\n", 2)
    if len(lines) < 3:
        return None
    ts, prev_utterance, answer = int(lines[0]), lines[1], lines[2]
    if time.time() - ts > PENDING_TTL:
        await asyncio.to_thread(path.unlink)
        return None
    return PendingResult(prev_utterance=prev_utterance, answer=answer)


async def clear_pending(user_id: str) -> None:
    path = DATA_DIR / "pending" / f"{user_id}.txt"
    if path.exists():
        await asyncio.to_thread(path.unlink)


async def get_active_users(d: date) -> list[str]:
    conv_root = DATA_DIR / "conversations"
    if not conv_root.exists():
        return []
    date_str = d.isoformat()
    users = []
    for user_dir in conv_root.iterdir():
        if user_dir.is_dir() and (user_dir / f"{date_str}.md").exists():
            users.append(user_dir.name)
    return users
