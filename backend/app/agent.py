import os
import re
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from .mcp_tools import call_tool


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def analyze_request(text):
    region: str | None = None
    region_names = (
        ("서울", "서울특별시"), ("부산", "부산광역시"), ("대구", "대구광역시"),
        ("인천", "인천광역시"), ("광주", "광주광역시"), ("대전", "대전광역시"),
        ("울산", "울산광역시"), ("세종", "세종특별자치시"), ("경기", "경기도"),
        ("강원", "강원특별자치도"), ("충북", "충청북도"), ("충남", "충청남도"),
        ("전북", "전북특별자치도"), ("전남", "전라남도"), ("경북", "경상북도"),
        ("경남", "경상남도"), ("제주", "제주특별자치도"),
    )
    for word, name in region_names:
        if word in text:
            region = name
            break

    event_type: str | None = None
    for kind in ("축제", "공연", "전시", "체험", "문화강좌"):
        if kind in text:
            event_type = kind
            break

    date_value: str | None = None
    date_match = re.search(r"(20\d{2})[-./년 ]*(\d{1,2})[-./월 ]*(\d{1,2})", text)
    if date_match:
        try:
            candidate = (
                f"{int(date_match.group(1)):04d}-"
                f"{int(date_match.group(2)):02d}-"
                f"{int(date_match.group(3)):02d}"
            )
            date.fromisoformat(candidate)
            date_value = candidate
        except ValueError:
            date_value = None
    return region, event_type, date_value


def search_for_request(text, limit=20):
    region, event_type, date_value = analyze_request(text)
    results = call_tool("culture_search", {
        "limit": limit,
        "region": region,
        "event_type": event_type,
        "date": date_value,
        "keyword": None if (region or event_type or date_value) else text,
    })
    if not results and not (region or event_type or date_value):
        results = call_tool("similar_search", {"query": text, "limit": min(limit, 10)})
    return region, event_type, date_value, results


def openai_answer(question, events):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, "OPENAI_API_KEY 환경변수가 설정되지 않았습니다."

    evidence = [
        {
            "id": item["id"],
            "title": item["title"],
            "event_type": item["event_type"],
            "region": item["region"],
            "district": item["district"],
            "venue": item["venue"],
            "start_date": item["start_date"],
            "end_date": item["end_date"],
            "description": item["description"],
            "address": item["address"],
            "fee": item["fee"],
        }
        for item in events
    ]
    if not evidence:
        return None, "현재 등록된 CSV 행사 데이터에서 관련 행사를 찾지 못했습니다."

    prompt = (
        "아래 검색된 행사 데이터만 근거로 사용자가 이해하기 쉽게 답변하세요.\n"
        "데이터에 없는 행사명, 장소, 날짜, 요금은 절대 만들지 마세요.\n"
        "확인할 수 없는 정보는 '확인 필요'라고 안내하세요.\n"
        f"사용자 질문: {question}\n"
        f"검색 근거: {evidence}"
    )
    try:
        client = OpenAI(api_key=api_key)
        system_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": "행사 검색 근거에 없는 정보를 추측하지 않는 문화행사 추천 도우미입니다.",
        }
        user_message: ChatCompletionUserMessageParam = {"role": "user", "content": prompt}
        messages: list[ChatCompletionMessageParam] = [system_message, user_message]
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.2,
            stream=False,
        )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            return None, "OpenAI 응답 데이터가 비어 있습니다."
        return content, None
    except OpenAIError as exc:
        return None, f"OpenAI 요청 실패: {exc.__class__.__name__}"


def grounded_answer(events):
    lines = []
    for event in events[:8]:
        place = " · ".join(filter(None, (event.get("region"), event.get("district"), event.get("venue"))))
        period = " ~ ".join(filter(None, (event.get("start_date"), event.get("end_date"))))
        details = [value for value in (event.get("event_type"), place, period) if value]
        lines.append(f"- {event['title']}" + (f" ({', '.join(details)})" if details else ""))
    return "CSV에서 검색한 행사입니다. 상세 내용은 행사 상세정보에서 확인하세요.\n" + "\n".join(lines)


def agent_recommend(message, limit=20):
    region, event_type, date_value, events = search_for_request(message, limit)
    conditions = []
    if region:
        conditions.append(f"지역: {region}")
    if event_type:
        conditions.append(f"행사 종류: {event_type}")
    if date_value:
        conditions.append(f"날짜: {date_value}")

    if not events:
        return "현재 등록된 CSV 행사 데이터에서 조건에 맞는 행사를 찾지 못했습니다.", events

    ai_answer, error = openai_answer(message, events)
    if ai_answer:
        if conditions:
            ai_answer = f"검색 조건 - {', '.join(conditions)}\n\n" + ai_answer
        return ai_answer, events
    notice = error or "OpenAI 설정이 없어 CSV 검색 결과를 표시합니다."
    return f"{notice}\n\n{grounded_answer(events)}", events


def agent_answer(question, limit=5):
    _, _, _, events = search_for_request(question, limit)
    if not events:
        return "현재 등록된 CSV 행사 데이터에서 관련 행사를 찾지 못했습니다.", events
    ai_answer, error = openai_answer(question, events)
    if ai_answer:
        return ai_answer, events
    notice = error or "OpenAI 설정이 없어 CSV 검색 결과를 표시합니다."
    return f"{notice}\n\n{grounded_answer(events)}", events
