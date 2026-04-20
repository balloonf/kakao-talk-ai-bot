import logging
from pathlib import Path

from playwright.async_api import async_playwright

from app.alerts import send_alert
from app.config import PLAYWRIGHT_HEADLESS

logger = logging.getLogger(__name__)

SESSION_PATH = Path("data/qwen_session/state.json")
TEXTAREA_SEL = "textarea.message-input-textarea"
LOADING_SEL = ".response-loading"
ANSWER_TIMEOUT = 120_000  # ms
MAX_CONTEXT_CHARS = 8000

# 실제 AI 응답으로 보기 위한 최소 글자 수 (tool-use 설명 텍스트 제외)
MIN_ANSWER_LEN = 80


async def ask(conv_context: str) -> str:
    """Playwright로 Qwen에 질문하고 응답 문자열을 직접 반환."""
    try:
        return await _fetch_answer(conv_context)
    except Exception as e:
        import traceback
        err_type = type(e).__name__
        err_msg = str(e) or "(메시지 없음)"
        logger.error(
            "qwen_playwright.ask failed: [%s] %s\n%s",
            err_type, err_msg, traceback.format_exc()
        )
        await send_alert(f"Qwen 오류 발생: [{err_type}] {err_msg}\n\n세션 만료 시: python -m app.qwen_init")
        return f"(Qwen 응답 실패: [{err_type}] {err_msg})"


# 마지막 AI 응답 텍스트 추출 (thinking 블록·버튼 등 UI 텍스트 제거)
_GET_ASSISTANT_TEXT = """() => {
    const els = document.querySelectorAll(".qwen-chat-message-assistant");
    if (!els.length) return "";
    const last = els[els.length - 1];
    const cloned = last.cloneNode(true);
    // thinking/reasoning 블록 제거
    cloned.querySelectorAll(
        '[class*="think"], [class*="reasoning"], [class*="thought"], details, summary'
    ).forEach(el => el.remove());
    // 버튼 제거 (건너뛰기 등)
    cloned.querySelectorAll('button').forEach(el => el.remove());
    let text = (cloned.innerText || cloned.textContent || "").trim();
    return text;
}"""


def _strip_thinking(text: str) -> str:
    """Qwen thinking 블록 텍스트가 남아있으면 제거."""
    markers = ["생각이 끝났습니다.", "생각 완료", "</think>"]
    for marker in markers:
        idx = text.find(marker)
        if idx != -1:
            text = text[idx + len(marker):].strip()
    return text


async def _fetch_answer(conv_context: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
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

            # 전송 후 초기 대기
            await page.wait_for_timeout(2000)

            # 마지막 AI 응답이 안정될 때까지 폴링 (최대 120초)
            prev_text = ""
            stable_count = 0
            good_answer_since = 0  # MIN_ANSWER_LEN 초과한 이후 경과 틱
            for _ in range(240):
                await page.wait_for_timeout(500)
                current = await page.evaluate(_GET_ASSISTANT_TEXT)

                # MIN_ANSWER_LEN 미만이면 아직 tool-use 단계 → 계속 대기
                if len(current) < MIN_ANSWER_LEN:
                    stable_count = 0
                    good_answer_since = 0
                    prev_text = current
                    continue

                good_answer_since += 1

                if current == prev_text:
                    stable_count += 1
                    if stable_count >= 2:  # 1초 연속 동일 → 완료
                        break
                else:
                    stable_count = 0

                # 충분한 답변이 20초 이상 쌓였으면 강제 반환
                if good_answer_since >= 40:
                    break

                prev_text = current

            answer = _strip_thinking(prev_text)
            logger.info("qwen answer extracted: len=%d preview=%r", len(answer), answer[:80])
            return answer
        finally:
            await browser.close()
