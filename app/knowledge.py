from __future__ import annotations

import asyncio
import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from app.config import DATA_DIR

model_ready: bool = False

_chroma_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None
_embed_model: SentenceTransformer | None = None

KNOWLEDGE_DIR = DATA_DIR / "knowledge"
CHROMA_DIR = DATA_DIR / "chroma"
RULES_FILE = KNOWLEDGE_DIR / "rules.md"

_DEFAULT_RULES = "당신은 친절하고 유능한 AI 어시스턴트입니다. 질문에 핵심만 간결하게 답변하세요."


def load_rules() -> str:
    """rules.md 에서 응답 규칙을 읽어 반환. 파일 없으면 기본값 사용."""
    if RULES_FILE.exists():
        return RULES_FILE.read_text(encoding="utf-8").strip()
    return _DEFAULT_RULES


def init_knowledge() -> None:
    global _chroma_client, _collection, _embed_model, model_ready

    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    _collection = _chroma_client.get_or_create_collection("knowledge")

    for md_file in KNOWLEDGE_DIR.glob("*.md"):
        _upsert_file(md_file)

    model_ready = True


def _chunk_markdown(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    # 헤딩 기준 분할
    chunks = re.split(r"\n(?=#{1,3} )", text)
    chunks = [c.strip() for c in chunks if c.strip()]
    if not chunks:
        return []
    # 헤딩이 없으면 단락 기준 폴백
    if len(chunks) == 1 and not re.match(r"^#{1,3} ", chunks[0]):
        chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
    return chunks


def _doc_ids(filestem: str, count: int) -> list[str]:
    return [f"{filestem}_{i}" for i in range(count)]


def _upsert_file(path: Path) -> None:
    assert _collection is not None and _embed_model is not None
    chunks = _chunk_markdown(path)
    if not chunks:
        return
    ids = _doc_ids(path.stem, len(chunks))
    embeddings = _embed_model.encode(chunks).tolist()
    _collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=[{"source": path.name}] * len(chunks),
    )


def _delete_file_chunks(filename: str) -> None:
    assert _collection is not None
    _collection.delete(where={"source": filename})


async def search(utterance: str, top_k: int = 3) -> str:
    if not model_ready or _collection is None or _embed_model is None:
        return ""

    def _sync_search() -> str:
        embedding = _embed_model.encode([utterance]).tolist()
        results = _collection.query(
            query_embeddings=embedding,
            n_results=min(top_k, _collection.count()),
            include=["documents"],
        )
        docs = results.get("documents", [[]])[0]
        return "\n\n---\n\n".join(docs) if docs else ""

    return await asyncio.to_thread(_sync_search)


async def add_knowledge(filename: str, content: str) -> None:
    path = KNOWLEDGE_DIR / filename
    await asyncio.to_thread(path.write_text, content, "utf-8")
    await asyncio.to_thread(_upsert_file, path)


async def delete_knowledge(filename: str) -> bool:
    path = KNOWLEDGE_DIR / filename
    if not path.exists():
        return False
    await asyncio.to_thread(path.unlink)
    await asyncio.to_thread(_delete_file_chunks, filename)
    return True


def list_knowledge() -> list[dict]:
    if not KNOWLEDGE_DIR.exists():
        return []
    return [
        {"id": p.stem, "filename": p.name, "size": p.stat().st_size}
        for p in sorted(KNOWLEDGE_DIR.glob("*.md"))
    ]
