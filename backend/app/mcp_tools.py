from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_

from .database import SessionLocal
from .models import Event


DATE_BASED_EVENT_TYPES = {"축제", "전시", "공연", "체험"}
SEOUL_TIMEZONE = ZoneInfo("Asia/Seoul")


def _serialize(event):
    return {
        "id": event.id,
        "title": event.title,
        "event_type": event.event_type,
        "region": event.region,
        "district": event.district,
        "venue": event.venue,
        "start_date": event.start_date,
        "end_date": event.end_date,
        "description": event.description,
        "address": event.address,
        "fee": event.fee,
        "phone": event.phone,
        "homepage": event.homepage,
        "detail_url": event.detail_url,
        "latitude": event.latitude,
        "longitude": event.longitude,
    }


def list_events(limit=50, **filters):
    limit = max(1, min(int(limit), 100))
    db = SessionLocal()
    try:
        query = db.query(Event)
        if filters.get("upcoming_only"):
            today = datetime.now(SEOUL_TIMEZONE).date().isoformat()
            query = query.filter(
                Event.event_type.in_(DATE_BASED_EVENT_TYPES),
                or_(
                    Event.end_date >= today,
                    and_(Event.end_date.is_(None), Event.start_date >= today),
                ),
            )
        if filters.get("region"):
            query = query.filter(Event.region.ilike(f"%{filters['region']}%"))
        if filters.get("district"):
            query = query.filter(Event.district.ilike(f"%{filters['district']}%"))
        if filters.get("event_type"):
            query = query.filter(Event.event_type == filters["event_type"])
        if filters.get("date"):
            query = query.filter(
                Event.start_date <= filters["date"],
                Event.end_date >= filters["date"],
            )
        elif filters.get("event_type") in DATE_BASED_EVENT_TYPES:
            today = datetime.now(SEOUL_TIMEZONE).date().isoformat()
            query = query.filter(or_(
                Event.end_date >= today,
                and_(Event.end_date.is_(None), Event.start_date >= today),
            ))
        if filters.get("keyword"):
            keyword = f"%{filters['keyword']}%"
            query = query.filter(or_(
                Event.title.ilike(keyword),
                Event.description.ilike(keyword),
                Event.category.ilike(keyword),
                Event.venue.ilike(keyword),
            ))
        events = query.order_by(Event.start_date.asc()).limit(min(limit, 100)).all()
        return [_serialize(event) for event in events]
    finally:
        db.close()


def search_region(region, limit=50):
    return list_events(limit=limit, region=region)


def search_date(date, limit=50):
    return list_events(limit=limit, date=date)


def search_type(event_type, limit=50):
    return list_events(limit=limit, event_type=event_type)


def event_detail(event_id):
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        return _serialize(event) if event else None
    finally:
        db.close()


def similar_events(query, limit=10):
    from .rag import search_similar

    results = search_similar(query, limit)
    db = SessionLocal()
    try:
        items = []
        for result in results:
            event = db.query(Event).filter(Event.id == result["id"]).first()
            if event:
                item = _serialize(event)
                item["distance"] = result["distance"]
                items.append(item)
        return items
    finally:
        db.close()


TOOL_DEFINITIONS = [
    {
        "name": "culture_search",
        "description": "문화행사를 키워드, 지역, 날짜, 유형으로 통합 검색합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "region": {"type": "string"},
                "district": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "event_type": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
        },
    },
    {
        "name": "region_search",
        "description": "지역명으로 문화행사를 검색합니다.",
        "inputSchema": {"type": "object", "properties": {
            "region": {"type": "string"}, "limit": {"type": "integer"},
        }, "required": ["region"]},
    },
    {
        "name": "date_search",
        "description": "행사 기간에 해당 날짜가 포함된 문화행사를 검색합니다.",
        "inputSchema": {"type": "object", "properties": {
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "limit": {"type": "integer"},
        }, "required": ["date"]},
    },
    {
        "name": "type_search",
        "description": "행사 유형별 검색입니다. 축제·전시·공연·체험은 오늘 진행 중이거나 이후 종료하는 행사만 반환합니다.",
        "inputSchema": {"type": "object", "properties": {
            "event_type": {"type": "string"}, "limit": {"type": "integer"},
        }, "required": ["event_type"]},
    },
    {
        "name": "event_detail",
        "description": "행사 ID로 상세정보를 조회합니다.",
        "inputSchema": {"type": "object", "properties": {
            "event_id": {"type": "integer"},
        }, "required": ["event_id"]},
    },
    {
        "name": "similar_search",
        "description": "ChromaDB에서 설명이 유사한 문화행사를 검색합니다.",
        "inputSchema": {"type": "object", "properties": {
            "query": {"type": "string"}, "limit": {"type": "integer"},
        }, "required": ["query"]},
    },
]


def call_tool(name, arguments):
    arguments = dict(arguments or {})
    limit = arguments.pop("limit", 50)
    if name == "culture_search":
        return list_events(limit=limit, **arguments)
    if name == "region_search":
        return search_region(arguments["region"], limit)
    if name == "date_search":
        return search_date(arguments["date"], limit)
    if name == "type_search":
        return search_type(arguments["event_type"], limit)
    if name == "event_detail":
        return event_detail(int(arguments["event_id"]))
    if name == "similar_search":
        return similar_events(arguments["query"], limit)
    raise ValueError(f"지원하지 않는 MCP 도구입니다: {name}")
