# KakaoTalk AI 자동응답 봇

카카오채널(오픈빌더) 기반 AI 자동응답 서버.
ChromaDB RAG + Claude API + 마크다운 대화 저장 + 일일 자동 요약.

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env   # API 키 입력
```

## 환경변수 (.env)

| 변수 | 설명 |
|------|------|
| `ANTHROPIC_API_KEY` | Anthropic API 키 |
| `KAKAO_SECRET_TOKEN` | 오픈빌더 → 서버 인증 토큰 (임의 문자열) |
| `MODEL` | 기본값: `claude-haiku-4-5-20251001` (AI 콜백 승인 후 `claude-sonnet-4-6`으로 변경) |
| `BOT_NAME` | 봇 이름 (시스템 프롬프트에 사용) |
| `TIMEZONE` | 기본값: `Asia/Seoul` |
| `DATA_DIR` | 데이터 저장 경로, 기본값: `./data` |

## 서버 실행

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- 대시보드: http://localhost:8000/
- API 문서: http://localhost:8000/docs

## ngrok 설정 (Phase 1 — 로컬 운영)

### 정적 도메인 설정 (URL 고정)

ngrok 무료 계정도 정적 도메인 1개 제공 (재시작 시 URL 유지).

1. [ngrok 대시보드](https://dashboard.ngrok.com) → Domains → "New Domain" 클릭
2. 생성된 도메인 확인 (예: `fox-happy-uniquely.ngrok-free.app`)
3. 서버 실행 후 터널 시작:

```bash
ngrok http --domain=fox-happy-uniquely.ngrok-free.app 8000
```

또는 `ngrok.yml`에 저장:

```yaml
# ~/.config/ngrok/ngrok.yml
version: "3"
agent:
  authtoken: YOUR_AUTHTOKEN
tunnels:
  kakao:
    proto: http
    addr: 8000
    domain: fox-happy-uniquely.ngrok-free.app
```

```bash
ngrok start kakao
```

### 카카오 오픈빌더 스킬 서버 URL

```
https://fox-happy-uniquely.ngrok-free.app/webhook
```

> **주의**: Phase 1은 로컬 PC + ngrok 전용. 실제 고객 트래픽 처리 전 Railway/Render 등 클라우드로 이전하세요.

## 카카오 오픈빌더 설정

1. [카카오 i 오픈빌더](https://i.kakao.com) → 봇 생성
2. 스킬 → 스킬 추가 → URL: `https://{ngrok-domain}/webhook`
3. Header: `Authorization` = `Bearer {KAKAO_SECRET_TOKEN}` (`.env`와 동일한 값)
4. 폴백 블록에 스킬 연결 (모든 발화 → 스킬)
5. **AI 콜백 기능 신청** (설정 → AI 챗봇 관리, 영업일 1-2일 소요)
6. 카카오채널과 봇 연결 후 배포

## 지식베이스 관리

`data/knowledge/` 폴더에 `.md` 파일을 추가하거나 웹 대시보드에서 편집.

- 파일 구조: 헤딩(`## `, `### `)으로 항목 구분
- 서버 재시작 시 자동 인덱싱
- 대시보드 → 지식베이스에서 런타임 추가/삭제 가능

> **주의**: 대시보드 외부에서 파일을 직접 삭제하면 ChromaDB에 stale 데이터가 남음.
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
    배송정책.md
    반품정책.md
  conversations/
    {user_id}/
      2026-04-18.md              ← 날짜별 대화 마크다운
  summaries/
    {user_id}/
      summary.md                 ← 누적 요약
  scheduler.db                   ← APScheduler SQLite
```
