from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def patch_knowledge_dir(tmp_path, monkeypatch):
    import app.knowledge as k
    import app.config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    monkeypatch.setattr(k, "KNOWLEDGE_DIR", tmp_path / "knowledge")
    monkeypatch.setattr(k, "CHROMA_DIR", tmp_path / "chroma")
    (tmp_path / "knowledge").mkdir(parents=True, exist_ok=True)
    yield


def test_chunk_markdown_by_heading(tmp_path):
    from app.knowledge import _chunk_markdown
    f = tmp_path / "test.md"
    f.write_text("## 배송 정책\n배송은 2일.\n\n## 반품 정책\n반품은 7일.", encoding="utf-8")
    chunks = _chunk_markdown(f)
    assert len(chunks) == 2
    assert "배송 정책" in chunks[0]
    assert "반품 정책" in chunks[1]


def test_chunk_markdown_fallback_paragraph(tmp_path):
    from app.knowledge import _chunk_markdown
    f = tmp_path / "test.md"
    f.write_text("첫 번째 단락입니다.\n\n두 번째 단락입니다.", encoding="utf-8")
    chunks = _chunk_markdown(f)
    assert len(chunks) == 2
    assert "첫 번째" in chunks[0]
    assert "두 번째" in chunks[1]


def test_chunk_markdown_empty_file(tmp_path):
    from app.knowledge import _chunk_markdown
    f = tmp_path / "empty.md"
    f.write_text("", encoding="utf-8")
    chunks = _chunk_markdown(f)
    assert chunks == []


def test_doc_ids():
    from app.knowledge import _doc_ids
    ids = _doc_ids("배송정책", 3)
    assert ids == ["배송정책_0", "배송정책_1", "배송정책_2"]


def test_list_knowledge_empty(tmp_path, monkeypatch):
    import app.knowledge as k
    monkeypatch.setattr(k, "KNOWLEDGE_DIR", tmp_path / "knowledge")
    (tmp_path / "knowledge").mkdir(exist_ok=True)
    result = k.list_knowledge()
    assert result == []


def test_list_knowledge_with_files(tmp_path, monkeypatch):
    import app.knowledge as k
    kdir = tmp_path / "knowledge"
    kdir.mkdir(exist_ok=True)
    (kdir / "배송.md").write_text("배송 내용", encoding="utf-8")
    monkeypatch.setattr(k, "KNOWLEDGE_DIR", kdir)
    result = k.list_knowledge()
    assert len(result) == 1
    assert result[0]["filename"] == "배송.md"


@pytest.mark.asyncio
async def test_search_returns_empty_when_not_ready(monkeypatch):
    import app.knowledge as k
    monkeypatch.setattr(k, "model_ready", False)
    result = await k.search("배송")
    assert result == ""


@pytest.mark.asyncio
async def test_add_and_delete_knowledge(tmp_path, monkeypatch):
    """add_knowledge가 파일을 생성하고 delete_knowledge가 삭제한다."""
    import app.knowledge as k
    kdir = tmp_path / "knowledge"
    kdir.mkdir(exist_ok=True)
    monkeypatch.setattr(k, "KNOWLEDGE_DIR", kdir)

    # _upsert_file, _delete_file_chunks를 mock
    monkeypatch.setattr(k, "_upsert_file", lambda path: None)
    monkeypatch.setattr(k, "_delete_file_chunks", lambda fname: None)

    await k.add_knowledge("test.md", "테스트 내용")
    assert (kdir / "test.md").exists()
    assert (kdir / "test.md").read_text(encoding="utf-8") == "테스트 내용"

    deleted = await k.delete_knowledge("test.md")
    assert deleted is True
    assert not (kdir / "test.md").exists()


@pytest.mark.asyncio
async def test_delete_knowledge_not_found(tmp_path, monkeypatch):
    import app.knowledge as k
    kdir = tmp_path / "knowledge"
    kdir.mkdir(exist_ok=True)
    monkeypatch.setattr(k, "KNOWLEDGE_DIR", kdir)
    deleted = await k.delete_knowledge("없는파일.md")
    assert deleted is False
