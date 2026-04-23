import anthropic

from app.config import ANTHROPIC_API_KEY, MODEL

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


async def summarize(conversation: str) -> str:
    prompt = (
        "다음 대화 내용을 간결하게 요약해 주세요. "
        "주요 주제, 문의 사항, 처리 결과를 포함하세요. "
        "3줄 이내로 작성하세요.\n\n"
        f"{conversation}"
    )

    def _sync_call() -> str:
        client = _get_client()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

    import asyncio
    try:
        return await asyncio.wait_for(asyncio.to_thread(_sync_call), timeout=10.0)
    except Exception:
        return "(요약 실패)"
