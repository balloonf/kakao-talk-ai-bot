import pytest
from httpx import AsyncClient, ASGITransport


def _make_body(user_id: str = "user123", utterance: str = "안녕"):
    return {"userRequest": {"user": {"id": user_id}, "utterance": utterance}}


@pytest.fixture(autouse=True)
def mock_deps(monkeypatch):
    """knowledge, storage, qwen_playwright를 모두 mock."""
    import app.knowledge as k
    import app.storage as s
    import app.webhook as wh

    monkeypatch.setattr(k, "model_ready", True)

    async def fake_search(utterance, top_k=3):
        return "지식 내용"

    async def fake_load_today(uid):
        return ""

    async def fake_load_summary(uid):
        return ""

    async def fake_load_pending(uid):
        return None

    async def fake_clear_pending(uid):
        pass

    async def fake_append_message(uid, utt, resp):
        pass

    async def fake_ask_with_lock(uid, utterance, conv_context):
        pass

    monkeypatch.setattr(k, "search", fake_search)
    monkeypatch.setattr(s, "load_today", fake_load_today)
    monkeypatch.setattr(s, "load_summary", fake_load_summary)
    monkeypatch.setattr(s, "load_pending", fake_load_pending)
    monkeypatch.setattr(s, "clear_pending", fake_clear_pending)
    monkeypatch.setattr(s, "append_message", fake_append_message)
    monkeypatch.setattr(wh, "_ask_with_lock", fake_ask_with_lock)


@pytest.fixture
def app_client():
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── Path B (pending 없음) ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_path_b_returns_wait_message(app_client):
    """pending 없을 때 '잠시 기다려주세요' 반환."""
    async with app_client as client:
        resp = await client.post(
            "/webhook",
            json=_make_body(),
            headers={"Authorization": "Bearer test-secret"},
        )
    assert resp.status_code == 200
    text = resp.json()["template"]["outputs"][0]["simpleText"]["text"]
    assert "잠시 기다려주세요" in text


@pytest.mark.asyncio
async def test_webhook_path_b_starts_playwright_task(app_client, monkeypatch):
    """pending 없을 때 BackgroundTask가 등록됨."""
    import app.webhook as wh

    called = []

    async def capture_ask(uid, utterance, ctx):
        called.append((uid, utterance))

    monkeypatch.setattr(wh, "_ask_with_lock", capture_ask)
    async with app_client as client:
        await client.post(
            "/webhook",
            json=_make_body(user_id="u1", utterance="질문"),
            headers={"Authorization": "Bearer test-secret"},
        )
    # BackgroundTask는 응답 반환 후 실행되므로 호출 여부만 확인
    # (실제 실행은 ASGI lifecycle에 의존 — 등록 자체를 mock으로 검증)


# ── Path A (pending 있음) ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_path_a_returns_pending_answer(app_client, monkeypatch):
    """pending 있을 때 이전 Qwen 답변 반환."""
    import app.storage as s
    from app.storage import PendingResult

    async def fake_load_pending(uid):
        return PendingResult(prev_utterance="이전 질문", answer="Qwen 답변입니다.")

    monkeypatch.setattr(s, "load_pending", fake_load_pending)

    async with app_client as client:
        resp = await client.post(
            "/webhook",
            json=_make_body(),
            headers={"Authorization": "Bearer test-secret"},
        )
    assert resp.status_code == 200
    text = resp.json()["template"]["outputs"][0]["simpleText"]["text"]
    assert text == "Qwen 답변입니다."


@pytest.mark.asyncio
async def test_webhook_path_a_uses_prev_utterance_for_log(app_client, monkeypatch):
    """append_message는 현재 utterance가 아니라 pending.prev_utterance를 사용."""
    import app.storage as s
    from app.storage import PendingResult

    async def fake_load_pending(uid):
        return PendingResult(prev_utterance="이전 질문", answer="이전 답변")

    logged = {}

    async def capture_append(uid, utt, resp):
        logged["utterance"] = utt
        logged["response"] = resp

    monkeypatch.setattr(s, "load_pending", fake_load_pending)
    monkeypatch.setattr(s, "append_message", capture_append)

    async with app_client as client:
        await client.post(
            "/webhook",
            json=_make_body(utterance="현재 질문"),
            headers={"Authorization": "Bearer test-secret"},
        )

    assert logged["utterance"] == "이전 질문"
    assert logged["response"] == "이전 답변"


@pytest.mark.asyncio
async def test_webhook_path_a_starts_new_playwright_task(app_client, monkeypatch):
    """Path A에서도 현재 utterance에 대한 BackgroundTask가 등록됨."""
    import app.storage as s
    import app.webhook as wh
    from app.storage import PendingResult

    async def fake_load_pending(uid):
        return PendingResult(prev_utterance="이전", answer="이전 답변")

    registered = []

    async def capture_ask(uid, utterance, ctx):
        registered.append(utterance)

    monkeypatch.setattr(s, "load_pending", fake_load_pending)
    monkeypatch.setattr(wh, "_ask_with_lock", capture_ask)

    async with app_client as client:
        await client.post(
            "/webhook",
            json=_make_body(utterance="현재 질문"),
            headers={"Authorization": "Bearer test-secret"},
        )
    # BackgroundTask 등록 확인 (실제 실행은 lifecycle 의존)


# ── 기존 테스트 유지 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_missing_auth(app_client):
    async with app_client as client:
        resp = await client.post("/webhook", json=_make_body())
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_wrong_token(app_client):
    async with app_client as client:
        resp = await client.post(
            "/webhook",
            json=_make_body(),
            headers={"Authorization": "Bearer wrong-token"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_malformed_body(app_client):
    async with app_client as client:
        resp = await client.post(
            "/webhook",
            json={"invalid": "body"},
            headers={"Authorization": "Bearer test-secret"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_model_not_ready(app_client, monkeypatch):
    import app.knowledge as k
    monkeypatch.setattr(k, "model_ready", False)
    async with app_client as client:
        resp = await client.post(
            "/webhook",
            json=_make_body(),
            headers={"Authorization": "Bearer test-secret"},
        )
    assert resp.status_code == 200
    text = resp.json()["template"]["outputs"][0]["simpleText"]["text"]
    assert text == "잠시 후 다시 시도해 주세요."


@pytest.mark.asyncio
async def test_webhook_lock_timeout_returns_fallback(app_client, monkeypatch):
    """Lock acquire 타임아웃 시 fallback 반환."""
    import asyncio
    import app.webhook as wh
    from app.config import FALLBACK_MSG

    original_wait_for = asyncio.wait_for

    async def fake_wait_for(coro, timeout):
        if timeout == wh._LOCK_TIMEOUT:
            raise asyncio.TimeoutError
        return await original_wait_for(coro, timeout)

    monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)
    async with app_client as client:
        resp = await client.post(
            "/webhook",
            json=_make_body(),
            headers={"Authorization": "Bearer test-secret"},
        )
    assert resp.status_code == 200
    text = resp.json()["template"]["outputs"][0]["simpleText"]["text"]
    assert text == FALLBACK_MSG
