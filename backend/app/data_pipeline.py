import csv
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete

from .database import SessionLocal
from .models import Event


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

TYPE_KEYWORDS = {
    "축제": ("축제", "페스티벌", "festival"),
    "공연": ("공연", "콘서트", "연극", "뮤지컬", "음악회", "오페라", "국악", "무용"),
    "전시": ("전시", "전시회", "갤러리", "미술"),
    "체험": ("체험", "캠프", "클래스", "만들기", "놀이"),
    "문화강좌": ("강좌", "교육", "아카데미", "교실", "학습"),
}

REGION_ALIASES = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기": "경기도",
    "강원": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}


def clean(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def province_name(value):
    value = clean(value)
    if not value:
        return None
    for prefix, full_name in REGION_ALIASES.items():
        if value.startswith(prefix):
            return full_name
    return value.split()[0]


def district_name(value):
    value = clean(value)
    if not value:
        return None
    parts = value.split()
    if len(parts) < 2:
        return None
    if parts[1].endswith(("구", "군", "시")):
        return parts[1]
    return None


def parse_date(value):
    value = clean(value)
    if not value:
        return None
    match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", value)
    if not match:
        return None
    try:
        return datetime(*(int(part) for part in match.groups())).strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_float(value):
    value = clean(value)
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def classify_type(source, category, title, description):
    if source == "national_festival":
        return "축제"
    if source == "national_performance":
        return "공연"
    text = " ".join(str(item or "") for item in (category, title, description)).lower()
    for event_type, keywords in TYPE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return event_type
    return None


def read_csv(filename):
    path = DATA_DIR / filename
    with path.open("r", encoding="cp949", errors="replace", newline="") as file:
        return list(csv.DictReader(file))


def split_seoul_date(value):
    value = clean(value)
    if not value:
        return None, None
    start, separator, end = value.partition("~")
    return parse_date(start), parse_date(end if separator else start)


def build_events():
    events = []
    seen = set()

    def add(row):
        row["title"] = clean(row.get("title"))
        if not row["title"]:
            return
        row["region"] = province_name(row.get("region"))
        row["district"] = clean(row.get("district"))
        row["venue"] = clean(row.get("venue"))
        key = (
            row["title"].casefold(),
            (row["region"] or "").casefold(),
            (row["district"] or "").casefold(),
            (row["venue"] or "").casefold(),
            row.get("start_date"),
            row.get("end_date"),
        )
        if key in seen:
            return
        seen.add(key)
        events.append(row)

    for source_row in read_csv("서울시 문화행사 정보.csv"):
        start, end = split_seoul_date(source_row.get("날짜"))
        add({
            "title": source_row.get("공연/행사명"),
            "source": "seoul",
            "event_type": classify_type(
                "seoul", source_row.get("테마분류"), source_row.get("공연/행사명"),
                source_row.get("프로그램소개"),
            ),
            "region": "서울특별시",
            "district": source_row.get("자치구"),
            "venue": source_row.get("장소"),
            "start_date": parse_date(source_row.get("시작일")) or start,
            "end_date": parse_date(source_row.get("종료일")) or end,
            "description": source_row.get("프로그램소개"),
            "category": source_row.get("테마분류"),
            "target": source_row.get("이용대상"),
            "fee": source_row.get("이용요금"),
            "phone": source_row.get("문의"),
            "homepage": source_row.get("홈페이지?주소"),
            "address": source_row.get("장소"),
            "latitude": parse_float(source_row.get("위도(X좌표)")),
            "longitude": parse_float(source_row.get("경도(Y좌표)")),
            "image_url": source_row.get("대표이미지"),
            "detail_url": source_row.get("문화포털상세URL"),
        })

    for source_row in read_csv("전국문화축제표준데이터.csv"):
        address = source_row.get("소재지도로명주소") or source_row.get("소재지지번주소")
        add({
            "title": source_row.get("축제명"),
            "source": "national_festival",
            "event_type": "축제",
            "region": address,
            "district": district_name(address),
            "venue": source_row.get("개최장소"),
            "start_date": parse_date(source_row.get("축제시작일자")),
            "end_date": parse_date(source_row.get("축제종료일자")),
            "description": source_row.get("축제내용"),
            "category": None,
            "target": None,
            "fee": None,
            "phone": source_row.get("전화번호"),
            "homepage": source_row.get("홈페이지주소"),
            "address": address,
            "latitude": parse_float(source_row.get("위도")),
            "longitude": parse_float(source_row.get("경도")),
            "image_url": None,
            "detail_url": source_row.get("홈페이지주소"),
        })

    for source_row in read_csv("전국공연행사정보표준데이터.csv"):
        address = source_row.get("소재지도로명주소") or source_row.get("소재지지번주소")
        add({
            "title": source_row.get("행사명"),
            "source": "national_performance",
            "event_type": "공연",
            "region": address,
            "district": district_name(address),
            "venue": source_row.get("장소"),
            "start_date": parse_date(source_row.get("행사시작일자")),
            "end_date": parse_date(source_row.get("행사종료일자")),
            "description": source_row.get("행사내용"),
            "category": source_row.get("분류"),
            "target": source_row.get("입장연령"),
            "fee": source_row.get("관람요금") or source_row.get("요금정보"),
            "phone": source_row.get("전화번호"),
            "homepage": source_row.get("홈페이지주소"),
            "address": address,
            "latitude": parse_float(source_row.get("위도")),
            "longitude": parse_float(source_row.get("경도")),
            "image_url": None,
            "detail_url": source_row.get("홈페이지주소"),
        })
    return events


def load_database():
    from .database import Base, engine

    Base.metadata.create_all(bind=engine)
    events = build_events()
    db = SessionLocal()
    try:
        db.execute(delete(Event))
        db.add_all([Event(**row) for row in events])
        db.commit()
        return len(events)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
