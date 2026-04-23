# 텔레그램 AI 자동응답 봇

텔레그램 기반 AI 자동응답 봇.
ChromaDB RAG + Qwen(Playwright) + 마크다운 대화 저장 + 일일 자동 요약.

## 설치

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # 환경변수 입력
```

## 환경변수 (.env)

| 변수 | 필수 | 설명 |
|------|------|------|
| `TELEGRAM_BOT_TOKEN` | ✅ | @BotFather에서 발급 |
| `OPERATOR_CHAT_ID` | 선택 | 오류 알림 받을 텔레그램 사용자 ID |
| `BOT_NAME` | 선택 | 봇 이름, 기본값: `AI 봇` |
| `TIMEZONE` | 선택 | 기본값: `Asia/Seoul` |
| `DATA_DIR` | 선택 | 데이터 저장 경로, 기본값: `./data` |
| `PLAYWRIGHT_HEADLESS` | 선택 | `false`로 설정 시 브라우저 화면 표시, 기본값: `true` |
| `ANTHROPIC_API_KEY` | 선택 | 대화 요약 기능 사용 시 필요 |

## Qwen 세션 초기화

최초 실행 또는 세션 만료 시 로그인 필요:

```bash
python -m app.qwen_init
```

브라우저가 열리면 Qwen에 로그인 후 엔터 입력. 세션이 `data/qwen_session/state.json`에 저장됩니다.

## 봇 실행

```bash
python -m app.telegram_bot
```

## 응답 규칙 설정

`data/knowledge/rules.md` 파일을 편집해 AI 응답 규칙을 설정합니다.
봇 재시작 없이 다음 메시지부터 즉시 적용됩니다.

```
## 응답 규칙
1. 항상 한국어로 답변합니다.
2. 친절하고 간결하게 답변합니다.
...
```

## 지식베이스 관리

`data/knowledge/` 폴더에 `.md` 파일을 추가하면 자동으로 벡터 인덱싱됩니다.

- `rules.md`: 응답 규칙 (시스템 프롬프트로 항상 포함)
- 그 외 `.md` 파일: RAG 검색 대상 (질문과 관련된 내용만 컨텍스트에 포함)
- 파일 구조: 헤딩(`## `, `### `)으로 항목 구분
- 서버 재시작 시 자동 재인덱싱

> **주의**: `data/knowledge/` 외부에서 파일을 직접 삭제하면 ChromaDB에 stale 데이터가 남습니다.
> `data/chroma/` 폴더를 삭제하고 서버를 재시작하면 재인덱싱됩니다.

## 테스트

```bash
pytest
```

## 데이터 구조

```
data/
  chroma/                        ← ChromaDB 벡터 저장소
  knowledge/
    rules.md                     ← 응답 규칙 (시스템 프롬프트)
    상품정보.md
    배송정책.md
  qwen_session/
    state.json                   ← Playwright 로그인 세션
  conversations/
    {user_id}/
      2026-04-20.md              ← 날짜별 대화 마크다운
  summaries/
    {user_id}/
      summary.md                 ← 누적 요약
  scheduler.db                   ← APScheduler SQLite
```
