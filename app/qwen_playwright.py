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
        import traceback
        err_type = type(e).__name__
        err_msg = str(e) or "(메시지 없음)"
        logger.error(
            "qwen_playwright.ask failed for %s: [%s] %s\n%s",
            user_id, err_type, err_msg, traceback.format_exc()
        )
        await storage.save_pending(user_id, utterance, f"(Qwen 응답 실패: [{err_type}] {err_msg})")


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

            # 전송 전 기존 응답 개수 기록
            before_count = await page.evaluate(f'() => document.querySelectorAll("{ANSWER_SEL}").length')
            logger.info("before send: %d existing answers", before_count)

            textarea = page.locator(TEXTAREA_SEL)
            await textarea.fill(conv_context[:MAX_CONTEXT_CHARS])
            await textarea.press("Enter")

            await page.wait_for_selector(LOADING_SEL, state="visible", timeout=10_000)
            await page.wait_for_selector(LOADING_SEL, state="hidden", timeout=ANSWER_TIMEOUT)

            # 새 응답이 DOM에 추가될 때까지 대기 (최대 5초)
            expected = before_count + 1
            await page.wait_for_function(
                f'() => document.querySelectorAll("{ANSWER_SEL}").length >= {expected}',
                timeout=5_000,
            )
            await page.wait_for_timeout(300)

            answer = await page.evaluate(f'''() => {{
                const els = document.querySelectorAll("{ANSWER_SEL}");
                if (els.length < {expected}) return "";
                const target = els[{before_count}];
                return (target.innerText || target.textContent || "").trim();
            }}''')

            logger.info("qwen answer extracted: len=%d preview=%r", len(answer), answer[:50])

            return answer
        finally:
            await browser.close()
