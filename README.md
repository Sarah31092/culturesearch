# AI 문화행사 추천

FastAPI와 HTML/CSS/JavaScript로 제공된 문화행사 CSV 3개를 검색하고 추천하는 웹 애플리케이션입니다. 별도 API나 다른 행사 데이터는 사용하지 않습니다. 원본 CSV를 읽어 SQLite에 통합 저장하며, RAG 검색용 임베딩은 개발자가 명령으로 생성합니다.

## 주요 기능

- 문화행사 통합, 지역, 날짜, 유형 검색 및 상세정보 조회
- 축제·전시·공연·체험 유형 검색은 한국 날짜 기준 오늘 진행 중이거나 이후 시작하는 행사만 표시
- 서울시 문화행사·전국 축제·전국 공연 CSV 통합 및 중복 정리
- 다섯 가지 행사 유형 분류 및 데이터가 없는 유형의 지원 여부 표시
- ChromaDB 유사 행사 검색 및 검색 근거를 사용하는 AI 질의응답
- 지역·종류·날짜 조건을 분석하는 행사 추천 에이전트
- HTTP MCP 도구 API 및 MCP 표준 입출력(stdio) 서버
- 행사 데이터나 검색 결과가 비어 있어도 안내 메시지 표시

유형은 `축제`, `공연`, `전시`, `체험`, `문화강좌`만 사용합니다. 전국 축제 CSV는 축제, 전국 공연 CSV는 공연으로 분류합니다. 서울 데이터는 CSV의 테마·행사명·설명에 근거해 분류하고, 확인되지 않는 유형은 미분류로 둡니다. 해당 자료에 없는 유형은 화면에서 데이터 없음으로 표시합니다.

## 기술과 구성

- Python 3.12, FastAPI, Uvicorn, SQLAlchemy, SQLite
- ChromaDB와 로컬 해시 기반 벡터 임베딩
- OpenAI API(선택 사항), python-dotenv
- MCP Python SDK
- HTML, CSS, JavaScript

```text
backend/
  app/
    main.py              FastAPI 화면/API 및 MCP HTTP 엔드포인트
    data_pipeline.py     CSV 전처리와 SQLite 저장
    database.py          SQLite 연결
    models.py            행사 테이블
    mcp_tools.py         검색 도구 함수와 도구 정의
    rag.py               로컬 임베딩 생성 및 ChromaDB 검색
    agent.py             요청 조건 분석, 근거 기반 추천/질의응답
    templates/index.html 웹 UI
    static/              CSS와 브라우저 JavaScript
  scripts/
    build_data.py        CSV 데이터 적재 실행 파일
    build_embeddings.py ChromaDB 임베딩 생성 실행 파일
  data/                  제공된 CSV 원본 3개
  mcp_server.py          MCP 표준 입출력 서버
  main.py                Uvicorn 실행 진입점
  culture.db             실행 시 생성되는 SQLite 파일
  chroma/                임베딩 생성 시 만들어지는 저장소
```

## 설치

프로젝트 루트에서 기존 가상환경을 활성화하고 필요한 패키지를 설치합니다.

```powershell
cd C:\fastapiworkspace\culturesearch
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`OPENAI_API_KEY`가 설정되어 있으면 AI 응답 생성에 사용합니다. 설정하지 않았거나 OpenAI 요청이 실패해도 실제 CSV 검색 결과와 명시적인 안내를 표시합니다. API 키를 코드에 입력하지 마세요.

## 데이터 준비와 적재

아래 파일을 `backend/data`에 준비합니다. 파일명과 원본은 변경하지 않습니다.

- `서울시 문화행사 정보.csv`
- `전국문화축제표준데이터.csv`
- `전국공연행사정보표준데이터.csv`

먼저 SQLite DB에 행사 데이터를 적재합니다. 이 명령은 기존 `events` 행을 CSV 데이터로 교체합니다.

```powershell
cd C:\fastapiworkspace\culturesearch\backend
..\.venv\Scripts\python.exe -m scripts.build_data
```

## 임베딩 생성

DB 적재 후 개발자가 직접 실행합니다. ChromaDB 데이터만 새로 생성하며 SQLite 행은 변경하지 않습니다.

```powershell
cd C:\fastapiworkspace\culturesearch\backend
..\.venv\Scripts\python.exe -m scripts.build_embeddings
```

임베딩은 외부 임베딩 API 없이 로컬에서 생성합니다. 임베딩을 만들기 전에는 검색 결과가 비어 있을 수 있습니다.

## 웹 실행

```powershell
cd C:\fastapiworkspace\culturesearch\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다.

## API 및 기능 확인

- 상태 및 지원 유형: `GET http://127.0.0.1:8000/api/status`
- 통합 검색: `GET /api/events?keyword=축제`
- 서울 검색: `GET /api/events?region=서울특별시`
- 날짜 검색: `GET /api/events?date=2026-12-26`
- 유형 검색: `GET /api/events?event_type=공연`
- 상세정보: `GET /api/events/{행사ID}`
- RAG 유사 검색: `GET /api/search/similar?query=겨울%20축제`
- 맞춤 추천: `POST /api/recommend` 본문 `{"message":"서울의 축제를 추천해줘"}`
- 질의응답: `POST /api/ask` 본문 `{"message":"검색된 행사의 장소를 알려줘"}`
- MCP 도구 목록/호출: `GET /api/mcp/tools`, `POST /api/mcp/call`

빠른 수동 테스트 순서: 데이터 적재 → 웹 실행 → 상태 확인 → 지역·날짜·유형별 검색 → 행사 카드에서 상세정보 확인 → 임베딩 생성 → 유사 검색 및 질의응답 확인. MCP API 호출 예:

```json
{"name":"region_search","arguments":{"region":"서울특별시","limit":10}}
```

## MCP 서버 실행 및 연결

표준 MCP 클라이언트는 stdio 서버를 실행합니다. 터미널에서 직접 실행할 때:

```powershell
cd C:\fastapiworkspace\culturesearch\backend
..\.venv\Scripts\python.exe mcp_server.py
```

MCP 클라이언트의 서버 설정 예시(경로는 프로젝트 위치에 맞게 변경):

```json
{
  "mcpServers": {
    "culture-events": {
      "command": "C:\\fastapiworkspace\\culturesearch\\.venv\\Scripts\\python.exe",
      "args": ["C:\\fastapiworkspace\\culturesearch\\backend\\mcp_server.py"],
      "env": {
        "PYTHONPATH": "C:\\fastapiworkspace\\culturesearch\\backend"
      }
    }
  }
}
```

서버는 `culture_search`, `region_search`, `date_search`, `type_search`, `event_detail`, `similar_search` 도구를 제공합니다. 유사 검색 도구는 임베딩을 미리 생성한 뒤 사용해야 합니다.
