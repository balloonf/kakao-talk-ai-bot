"""
1회 실행용 Qwen 세션 초기화.
비 헤드리스 브라우저를 열어 수동 로그인 후 세션을 저장합니다.
실행: python -m app.qwen_init
"""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

SESSION_PATH = Path("data/qwen_session/state.json")


async def main() -> None:
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://chat.qwen.ai")
        print("브라우저가 열렸습니다. chat.qwen.ai에 로그인해 주세요.")
        print("로그인 완료 후 채팅 화면이 보이면 Enter를 누르세요...")
        input()

        await context.storage_state(path=str(SESSION_PATH))
        print(f"세션 저장 완료: {SESSION_PATH}")

        # 셀렉터 확인용: 현재 페이지 주요 요소 출력
        print("\n--- 셀렉터 확인 ---")
        for sel in [
            "textarea",
            "[contenteditable='true']",
            "#chat-input",
            ".chat-input",
        ]:
            count = await page.locator(sel).count()
            if count > 0:
                print(f"textarea 후보: {sel} ({count}개)")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
