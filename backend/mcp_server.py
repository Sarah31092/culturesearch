from mcp.server.fastmcp import FastMCP

from app.mcp_tools import (
    event_detail as get_event_detail,
    list_events,
    search_date,
    search_region,
    search_type,
    similar_events,
)


mcp = FastMCP("culture-event-search")


@mcp.tool(description="키워드, 지역, 날짜, 유형 조건으로 문화행사를 통합 검색합니다.")
def culture_search(
    keyword: str = "",
    region: str = "",
    district: str = "",
    date: str = "",
    event_type: str = "",
    limit: int = 50,
) -> list[dict]:
    return list_events(
        keyword=keyword or None,
        region=region or None,
        district=district or None,
        date=date or None,
        event_type=event_type or None,
        limit=limit,
    )


@mcp.tool(description="지역명으로 문화행사를 검색합니다.")
def region_search(region: str, limit: int = 50) -> list[dict]:
    return search_region(region, limit)


@mcp.tool(description="행사 기간에 지정한 날짜가 포함된 문화행사를 검색합니다.")
def date_search(date: str, limit: int = 50) -> list[dict]:
    return search_date(date, limit)


@mcp.tool(description="유형별 검색입니다. 축제·전시·공연·체험은 오늘 진행 중이거나 이후 종료하는 행사만 검색합니다.")
def type_search(event_type: str, limit: int = 50) -> list[dict]:
    return search_type(event_type, limit)


@mcp.tool(description="행사 ID로 상세정보를 조회합니다.")
def event_detail(event_id: int) -> dict | None:
    return get_event_detail(event_id)


@mcp.tool(description="ChromaDB에서 설명이 유사한 문화행사를 검색합니다.")
def similar_search(query: str, limit: int = 10) -> list[dict]:
    return similar_events(query, limit)


if __name__ == "__main__":
    mcp.run(transport="stdio")
