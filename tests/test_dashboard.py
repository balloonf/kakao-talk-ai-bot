import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path, monkeypatch):
    import app.storage as s
    import app.knowledge as k
    import app.config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    monkeypatch.setattr(s, "DATA_DIR", tmp_path)
    (tmp_path / "knowledge").mkdir(parents=True)


@pytest.fixture(autouse=True)
def mock_knowledge_startup(monkeypatch):
    """startup 이벤트에서 knowledge.init_knowledge() 호출 방지."""
    import app.knowledge as k
    monkeypatch.setattr(k, "model_ready", True)
    monkeypatch.setattr(k, "init_knowledge", lambda: None)


@pytest.fixture(autouse=True)
def mock_scheduler(monkeypatch):
    import app.scheduler as sch
    from unittest.mock import MagicMock
    fake_scheduler = MagicMock()
    fake_scheduler.running = False
    monkeypatch.setattr(sch, "_scheduler", fake_scheduler)
    monkeypatch.setattr(sch, "get_scheduler", lambda: fake_scheduler)


@pytest.fixture
def client():
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_dashboard_empty(client):
    async with client as c:
        resp = await c.get("/")
    assert resp.status_code == 200
    assert "아직 대화 없음" in resp.text


@pytest.mark.asyncio
async def test_dashboard_with_conversation(tmp_path, client, monkeypatch):
    import app.storage as s
    await s.append_message("kakao_user1", "안녕", "안녕하세요!")
    async with client as c:
        resp = await c.get("/")
    assert resp.status_code == 200
    assert "kakao_user1" in resp.text


@pytest.mark.asyncio
async def test_knowledge_list_empty(client, monkeypatch):
    import app.knowledge as k
    monkeypatch.setattr(k, "list_knowledge", lambda: [])
    async with client as c:
        resp = await c.get("/knowledge")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


@pytest.mark.asyncio
async def test_knowledge_list_with_files(client, monkeypatch):
    import app.knowledge as k
    monkeypatch.setattr(k, "list_knowledge", lambda: [{"id": "배송", "filename": "배송.md", "size": 100}])
    async with client as c:
        resp = await c.get("/knowledge")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["filename"] == "배송.md"


@pytest.mark.asyncio
async def test_post_knowledge_valid(client, monkeypatch):
    import app.knowledge as k
    added = []

    async def fake_add(filename, content):
        added.append((filename, content))

    monkeypatch.setattr(k, "add_knowledge", fake_add)
    async with client as c:
        resp = await c.post("/knowledge", json={"filename": "test.md", "content": "내용"})
    assert resp.status_code == 200
    assert added[0] == ("test.md", "내용")


@pytest.mark.asyncio
async def test_post_knowledge_missing_fields(client):
    async with client as c:
        resp = await c.post("/knowledge", json={"filename": "test.md"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_knowledge_path_traversal(client, monkeypatch):
    import app.knowledge as k
    monkeypatch.setattr(k, "add_knowledge", lambda f, c: None)
    async with client as c:
        resp = await c.post("/knowledge", json={"filename": "../../etc/passwd.md", "content": "x"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_knowledge_exists(client, monkeypatch):
    import app.knowledge as k

    async def fake_delete(filename):
        return True

    monkeypatch.setattr(k, "delete_knowledge", fake_delete)
    async with client as c:
        resp = await c.delete("/knowledge/배송")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_knowledge_not_found(client, monkeypatch):
    import app.knowledge as k

    async def fake_delete(filename):
        return False

    monkeypatch.setattr(k, "delete_knowledge", fake_delete)
    async with client as c:
        resp = await c.delete("/knowledge/없는파일")
    assert resp.status_code == 404
