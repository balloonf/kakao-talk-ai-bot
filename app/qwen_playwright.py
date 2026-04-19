import logging
from pathlib import Path

from playwright.async_api import async_playwright

from app import storage

logger = logging.getLogger(__name__)

SESSION_PATH = Path("data/qwen_session/state.json")
TEXTAREA_SEL = "textarea.message-input-textarea"
LOADING_SEL = ".response-loading"
ANSWER_SEL = ".phase-answer"
ANSWER_TIMEOUT = 60_000  # ms
MAX_CONTEXT_CHARS = 4000


async def ask(user_id: str, utterance: str, conv_context: str) -> None:
    """Playwright로 Qwen에 질문하고 결과를 pending 파일에 저장."""
    try:
        answer = await _fetch_answer(conv_context)
        await storage.save_pending(user_id, utterance, answer)
    except Exception as e:
        logger.error("qwen_playwright.ask failed for %s: %s", user_id, e)
        await storage.save_pending(user_id, utterance, f"(Qwen 응답 실패: {e})")


async def _fetch_answer(conv_context: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(storage_state=str(SESSION_PATH))
            page = await context.new_page()
            await page.goto("https://chat.qwen.ai", timeout=30_000)
            await page.wait_for_timeout(2000)

            if "login" in page.url or "signin" in page.url:
                raise RuntimeError("Qwen 세션 만료 — python -m app.qwen_init 으로 재로그인 필요")

            textarea = page.locator(TEXTAREA_SEL)
            await textarea.fill(conv_context[:MAX_CONTEXT_CHARS])
            await textarea.press("Enter")

            await page.wait_for_selector(LOADING_SEL, state="visible", timeout=10_000)
            await page.wait_for_selector(LOADING_SEL, state="hidden", timeout=ANSWER_TIMEOUT)
            await page.wait_for_timeout(500)

            answer = await page.evaluate(f'''() => {{
                const els = document.querySelectorAll("{ANSWER_SEL}");
                if (!els.length) return "";
                return els[els.length - 1].innerText.trim();
            }}''')

            if not answer:
                raise RuntimeError("응답 텍스트를 찾을 수 없음")

            return answer
        finally:
            await browser.close()
