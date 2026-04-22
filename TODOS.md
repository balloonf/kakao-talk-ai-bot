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

## From Eng Review (2026-04-19) — Telegram 전환

- **ngrok → 클라우드 이전 (Railway/Render) 업데이트**
  - 텔레그램 Long Polling 전환으로 ngrok 의존성 제거됨. Railway/Render 이전 시에도 Long Polling 그대로 사용 가능. 이전 시 환경변수 TELEGRAM_BOT_TOKEN만 설정하면 됨.

