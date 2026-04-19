import pytest
from httpx import AsyncClient, ASGITransport


def _make_body(user_id: str = "user123", utterance: str = "안녕"):
    return {"userRequest": {"user": {"id": user_id}, "utterance": utterance}}


@pytest.fixture(autouse=True)
def mock_deps(monkeypatch):
    """AI, knowledge, storage를 모두 mock."""
    import app.knowledge as k
    import app.ai as ai
    import app.storage as s

    monkeypatch.setattr(k, "model_ready", True)

    async def fake_search(utterance, top_k=3):
        return "지식 내용"

    async def fake_respond(utterance, history, summary, chunks):
        return f"응답: {utterance}"

    async def fake_load_today(uid):
        return ""

    async def fake_load_summary(uid):
        return ""

    async def fake_append_message(uid, utt, resp):
        pass

    monkeypatch.setattr(k, "search", fake_search)
    monkeypatch.setattr(ai, "respond", fake_respond)
    monkeypatch.setattr(s, "load_today", fake_load_today)
    monkeypatch.setattr(s, "load_summary", fake_load_summary)
    monkeypatch.setattr(s, "append_message", fake_append_message)


@pytest.fixture
def app_client():
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_webhook_valid_request(app_client):
    async with app_client as client:
        resp = await client.post(
            "/webhook",
            json=_make_body(),
            headers={"Authorization": "Bearer test-secret"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "2.0"
    assert "simpleText" in data["template"]["outputs"][0]
    assert "응답: 안녕" in data["template"]["outputs"][0]["simpleText"]["text"]


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
async def test_webhook_fallback_on_ai_error(app_client, monkeypatch):
    import app.ai as ai
    from app.config import FALLBACK_MSG

    async def fail_respond(*args, **kwargs):
        return FALLBACK_MSG

    monkeypatch.setattr(ai, "respond", fail_respond)
    async with app_client as client:
        resp = await client.post(
            "/webhook",
            json=_make_body(),
            headers={"Authorization": "Bearer test-secret"},
        )
    assert resp.status_code == 200
    text = resp.json()["template"]["outputs"][0]["simpleText"]["text"]
    assert text == FALLBACK_MSG


@pytest.mark.asyncio
async def test_webhook_new_user_no_history(app_client, monkeypatch):
    """신규 사용자 — history/summary 없어도 정상 동작."""
    import app.ai as ai
    captured = {}

    async def capture_respond(utterance, history, summary, chunks):
        captured["history"] = history
        captured["summary"] = summary
        return "ok"

    monkeypatch.setattr(ai, "respond", capture_respond)
    async with app_client as client:
        await client.post(
            "/webhook",
            json=_make_body(user_id="brand_new_user"),
            headers={"Authorization": "Bearer test-secret"},
        )
    assert captured["history"] == ""
    assert captured["summary"] == ""


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
