# TODOS

## From CEO Plan (Deferred)

- **대시보드 인증 (HTTP Basic Auth)**
  - Why: 현재 개인용이라 불필요. 팀 공유 시 추가.
  - Depends on: Phase 2 cloud migration

- **ngrok → 클라우드 이전 (Railway/Render)**
  - Why: Phase 1은 로컬 + ngrok. 실제 고객 트래픽 처리 전 이전 필수.
  - Depends on: KakaoTalk AI 콜백 승인 + 로컬 검증 완료

## From Eng Review (2026-04-18)

- **Knowledge search relevance score threshold**
  - What: `knowledge.search()` currently always returns top_k=3 results regardless of match quality. When no good match exists, irrelevant chunks degrade response quality.
  - Why: Improves Claude response quality for off-topic questions. Prevents prompt pollution.
  - Pros: Better AI responses when knowledge base doesn't cover the question.
  - Cons: Requires tuning the threshold (0.4 cosine similarity is a starting point, may need adjustment).
  - Context: ChromaDB returns cosine similarity scores with results. Filter: `[(doc, score) for doc, score in results if score > 0.4]`. If all below threshold, pass empty knowledge_chunks — Claude will answer from its training data.
  - Blocked by: need real traffic to calibrate threshold value

- **ngrok disconnect alerting**
  - What: When ngrok disconnects or local server goes down, all incoming webhooks are silently dropped.
  - Why: For a customer-facing bot, silent downtime = unanswered customer messages.
  - Pros: Operational awareness without checking manually.
  - Cons: Requires a notification channel (Slack webhook, email, etc.).
  - Context: Options: (1) cron job pings `/health` endpoint and alerts on failure, (2) ngrok agent config with `on_disconnect` webhook, (3) simple watchdog script. Simplest: add a `/health` endpoint and check it via external uptime monitor (UptimeRobot free tier).
  - Blocked by: deployment environment decision (Phase 2 cloud migration may make this moot)

## From Eng Review (2026-04-19) — Playwright + Qwen

- **Qwen 세션 만료 / Playwright 실패 알림**
  - What: Playwright가 Qwen 세션 만료(로그인 페이지 리다이렉트)나 기타 오류를 감지하면 오류 메시지를 pending 파일에 저장하지만, 운영자에게 알림이 없음.
  - Why: 세션이 만료되면 모든 사용자 답변이 조용히 `(Qwen 응답 실패: ...)` 가 됨. 운영자가 수동으로 확인하지 않으면 모름.
  - Pros: 재초기화(`python -m app.qwen_init`) 타이밍을 즉각 인지.
  - Cons: 알림 채널 필요 (Slack webhook, 이메일 등).
  - Context: `qwen_playwright.ask()`의 except 블록에서 오류 감지 → 알림 발송. UptimeRobot + `/health` 방식보다 인앱 직접 감지가 더 정확. `playwright-stealth` 도입 시 bot detection 오류도 여기서 처리.
  - Blocked by: 알림 채널 결정 (ngrok alerting TODO와 같은 채널 사용 권장)
