from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import func

from .agent import agent_answer, agent_recommend
from .data_pipeline import load_database
from .database import Base, SessionLocal, engine
from .mcp_tools import TOOL_DEFINITIONS, call_tool, list_events, event_detail
from .models import Event


BASE_DIR = Path(__file__).resolve().parent
EVENT_TYPES = ("축제", "공연", "전시", "체험", "문화강좌")

app = FastAPI(title="AI 문화행사 추천", description="제공된 CSV 데이터 기반 문화행사 검색과 추천")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
Base.metadata.create_all(bind=engine)


class QuestionRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def main_page(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/api/status")
def data_status():
    db = SessionLocal()
    try:
        total = db.query(func.count(Event.id)).scalar() or 0
        counts = dict(
            db.query(Event.event_type, func.count(Event.id))
            .filter(Event.event_type.isnot(None))
            .group_by(Event.event_type)
            .all()
        )
        return {
            "total": total,
            "types": [
                {"name": event_type, "count": counts.get(event_type, 0),
                 "supported": counts.get(event_type, 0) > 0}
                for event_type in EVENT_TYPES
            ],
        }
    finally:
        db.close()


@app.post("/api/admin/load-data")
def load_data():
    return {"count": load_database()}


@app.get("/api/events")
def get_events(
    keyword: str | None = None,
    region: str | None = None,
    district: str | None = None,
    event_type: str | None = None,
    date_value: str | None = Query(default=None, alias="date"),
    limit: int = Query(default=50, ge=1, le=100),
):
    if date_value:
        try:
            date.fromisoformat(date_value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="날짜는 YYYY-MM-DD 형식이어야 합니다.") from exc
    return list_events(
        limit=limit,
        keyword=keyword,
        region=region,
        district=district,
        event_type=event_type,
        date=date_value,
    )


@app.get("/api/events/{event_id}")
def get_event(event_id: int):
    event = event_detail(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="행사 정보를 찾을 수 없습니다.")
    return event


@app.get("/api/search/similar")
def search_similar_events(
    query: str = Query(min_length=1, max_length=500),
    limit: int = Query(default=10, ge=1, le=100),
):
    from .mcp_tools import similar_events

    return similar_events(query, limit)


@app.post("/api/recommend")
def recommend(request: QuestionRequest):
    answer, events = agent_recommend(request.message)
    return {"answer": answer, "events": events}


@app.post("/api/ask")
def ask_question(request: QuestionRequest):
    answer, events = agent_answer(request.message)
    return {"answer": answer, "events": events}


@app.get("/api/mcp/tools")
def mcp_tools():
    return {"tools": TOOL_DEFINITIONS}


@app.post("/api/mcp/call")
def mcp_call(payload: dict):
    name = payload.get("name")
    arguments = payload.get("arguments", {})
    if not isinstance(name, str) or not isinstance(arguments, dict):
        raise HTTPException(status_code=422, detail="name과 arguments를 확인해주세요.")
    try:
        return {"result": call_tool(name, arguments)}
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
