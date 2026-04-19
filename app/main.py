import logging

from fastapi import FastAPI

from app import knowledge
from app.scheduler import get_scheduler
from app.webhook import router as webhook_router
from app.dashboard import router as dashboard_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

app = FastAPI(title="KakaoTalk AI 봇")
app.include_router(webhook_router)
app.include_router(dashboard_router)


@app.on_event("startup")
async def startup():
    import asyncio
    # 임베딩 모델과 ChromaDB는 blocking I/O — 별도 스레드에서 초기화
    await asyncio.to_thread(knowledge.init_knowledge)
    get_scheduler().start()


@app.on_event("shutdown")
async def shutdown():
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
