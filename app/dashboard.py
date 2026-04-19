import re
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app import config as _cfg, knowledge, storage

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _validate_filename(filename: str) -> str:
    if not filename.endswith(".md"):
        filename += ".md"
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=422, detail="잘못된 파일명")
    if not re.match(r"^[\w\-.가-힣]+\.md$", filename):
        raise HTTPException(status_code=422, detail="잘못된 파일명 형식")
    return filename


async def _get_recent_conversations(days: int = 7) -> list[dict]:
    conv_root = _cfg.DATA_DIR / "conversations"
    if not conv_root.exists():
        return []

    result = []
    today = date.today()
    date_range = [(today - timedelta(days=i)).isoformat() for i in range(days)]

    for user_dir in sorted(conv_root.iterdir()):
        if not user_dir.is_dir():
            continue
        user_id = user_dir.name
        for date_str in date_range:
            conv_file = user_dir / f"{date_str}.md"
            if conv_file.exists():
                content = await storage.load_conversation(
                    user_id, date.fromisoformat(date_str)
                )
                msg_count = content.count("**[")
                summary = await storage.load_summary(user_id)
                last_summary_line = ""
                if summary:
                    lines = [l for l in summary.splitlines() if l and not l.startswith("#")]
                    last_summary_line = lines[0] if lines else ""
                result.append(
                    {
                        "user_id": user_id,
                        "date": date_str,
                        "message_count": msg_count,
                        "summary": last_summary_line,
                    }
                )
                break
    return result


@router.get("/", response_class=HTMLResponse)
async def dashboard_index(request: Request):
    conversations = await _get_recent_conversations()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "conversations": conversations},
    )


@router.get("/user/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: str):
    today = date.today()
    history = await storage.load_today(user_id)
    summary = await storage.load_summary(user_id)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "conversations": [],
            "detail": {
                "user_id": user_id,
                "date": today.isoformat(),
                "history": history,
                "summary": summary,
            },
        },
    )


@router.get("/knowledge")
async def list_knowledge():
    return {"items": knowledge.list_knowledge()}


class KnowledgeCreate(BaseModel):
    filename: str
    content: str


@router.post("/knowledge", status_code=200)
async def create_knowledge(body: KnowledgeCreate):
    filename = _validate_filename(body.filename)
    await knowledge.add_knowledge(filename, body.content)
    return {"status": "ok", "filename": filename}


@router.delete("/knowledge/{knowledge_id}", status_code=200)
async def delete_knowledge(knowledge_id: str):
    filename = _validate_filename(f"{knowledge_id}.md") if not knowledge_id.endswith(".md") else knowledge_id
    deleted = await knowledge.delete_knowledge(filename)
    if not deleted:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    return {"status": "ok", "filename": filename}
