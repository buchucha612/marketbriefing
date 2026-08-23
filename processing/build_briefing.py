"""Build a daily briefing JSON with content-based topic classification."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "storage" / "raw"
DAILY_DIR = ROOT / "storage" / "daily"
SERVING_DIR = ROOT / "serving"
KST = ZoneInfo("Asia/Seoul")

SECTION_LABELS = {
    "domestic": "국내 증시",
    "us": "미국 증시",
    "macro": "금리·환율·유가·원자재",
    "sector": "섹터/테마",
    "weekly": "금주의 브리핑",
    "uncategorized": "미분류",
}

THEME_RULES = [
    {
        "name": "반도체·AI",
        "keywords": ["반도체", "AI", "인공지능", "HBM", "엔비디아", "NVIDIA", "SK하이닉스", "삼성전자"],
        "representatives": ["삼성전자", "SK하이닉스", "한미반도체", "NVIDIA", "AMD"],
    },
    {
        "name": "2차전지·전기차",
        "keywords": ["2차전지", "배터리", "전기차", "테슬라", "리튬", "양극재"],
        "representatives": ["LG에너지솔루션", "삼성SDI", "에코프로", "Tesla"],
    },
    {
        "name": "바이오·헬스케어",
        "keywords": ["바이오", "제약", "헬스케어", "FDA", "임상", "신약"],
        "representatives": ["삼성바이오로직스", "셀트리온", "유한양행"],
    },
    {
        "name": "조선·방산",
        "keywords": ["조선", "방산", "수주", "선박", "한화오션", "HD현대", "방위"],
        "representatives": ["HD현대중공업", "한화오션", "현대로템", "LIG넥스원"],
    },
    {
        "name": "자동차·모빌리티",
        "keywords": ["자동차", "현대차", "기아", "자율주행", "모빌리티"],
        "representatives": ["현대차", "기아", "Tesla"],
    },
    {
        "name": "금융·은행",
        "keywords": ["금융주", "은행", "보험", "증권", "배당", "자사주"],
        "representatives": ["KB금융", "신한지주", "하나금융지주"],
    },
    {
        "name": "에너지·원자재",
        "keywords": ["에너지", "원유", "유가", "천연가스", "구리", "금값", "원자재"],
        "representatives": ["S-Oil", "한국전력", "Exxon Mobil", "Chevron"],
    },
    {
        "name": "미국 빅테크",
        "keywords": ["기술주", "빅테크", "애플", "마이크로소프트", "알파벳", "아마존", "메타", "Nasdaq"],
        "representatives": ["Apple", "Microsoft", "Alphabet", "Amazon", "Meta"],
    },
]

CATALYST_KEYWORDS = [
    "정책",
    "정부",
    "대통령",
    "수주",
    "실적",
    "가이던스",
    "투자",
    "승인",
    "FDA",
    "인수",
    "계약",
    "buyback",
    "earnings",
]

RISK_KEYWORDS = [
    "금리",
    "Fed",
    "FOMC",
    "CPI",
    "PPI",
    "인플레이션",
    "환율",
    "유가",
    "관세",
    "중동",
    "Treasury",
    "yield",
]

TOPIC_RULES = {
    "domestic": {
        "keywords": [
            "코스피",
            "코스닥",
            "한국증시",
            "한국 증시",
            "국내증시",
            "국내 증시",
            "서울증시",
            "외국인",
            "기관",
            "개인투자자",
            "삼성전자",
            "SK하이닉스",
            "현대차",
            "네이버",
            "카카오",
        ],
    },
    "us": {
        "keywords": [
            "미국증시",
            "미국 증시",
            "뉴욕증시",
            "월가",
            "나스닥",
            "S&P500",
            "S&P 500",
            "다우",
            "다우존스",
            "테슬라",
            "엔비디아",
            "애플",
            "알파벳",
            "마이크로소프트",
            "넷플릭스",
            "월스트리트",
            "US stock",
            "US stocks",
            "Wall Street",
            "Nasdaq",
            "Dow",
        ],
    },
    "macro": {
        "keywords": [
            "환율",
            "원달러",
            "달러",
            "금리",
            "국채",
            "유가",
            "국제유가",
            "브렌트",
            "브렌트유",
            "WTI",
            "원유",
            "원자재",
            "금값",
            "금 가격",
            "금 선물",
            "국제 금",
            "은값",
            "은 가격",
            "은 선물",
            "구리",
            "천연가스",
            "Fed",
            "FOMC",
            "CPI",
            "PPI",
            "인플레이션",
            "중동",
            "Treasury",
            "Treasuries",
            "yield",
            "yields",
            "oil",
            "crude",
            "dollar",
            "commodity",
            "commodities",
            "gold",
            "silver",
            "copper",
            "natural gas",
        ],
    },
    "sector": {
        "keywords": [
            "반도체",
            "AI",
            "2차전지",
            "바이오",
            "조선",
            "방산",
            "자동차",
            "금융주",
            "에너지",
            "기술주",
            "테마",
            "semiconductor",
            "technology",
            "tech",
        ],
    },
}


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def local_date(value: str) -> date | None:
    parsed = parse_datetime(value)
    if not parsed:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(KST).date()


def format_korean_date(value: date) -> str:
    return f"{value.month}월 {value.day}일"


def weekly_window(now: datetime) -> tuple[date, date]:
    local_now = now.astimezone(KST)
    days_since_saturday = (local_now.weekday() - 5) % 7
    end_date = (local_now - timedelta(days=days_since_saturday)).date()
    start_offset = 6 if local_now.weekday() == 5 else 5
    start_date = end_date - timedelta(days=start_offset)
    return start_date, end_date


def topic_score(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    matched = []
    lower_text = text.lower()
    for keyword in keywords:
        if keyword.lower() in lower_text:
            matched.append(keyword)
    return len(matched), matched


def build_reason(primary_topic: str, secondary_topics: list[str], matched_keywords: dict[str, list[str]]) -> str:
    if primary_topic == "uncategorized":
        return "분류 키워드가 충분히 감지되지 않아 미분류로 보관했습니다."
    primary_matches = ", ".join(matched_keywords.get(primary_topic, [])[:4])
    reason = f"{SECTION_LABELS[primary_topic]} 키워드({primary_matches})가 가장 많이 감지되었습니다."
    if secondary_topics:
        secondary_labels = ", ".join(SECTION_LABELS[topic] for topic in secondary_topics[:2])
        reason += f" 보조 주제: {secondary_labels}."
    return reason


def classify_article(item: dict) -> dict:
    hint_scores = Counter(item.get("topic_hints", []))
    text = normalize_text(
        f'{item.get("title", "")} '
        f'{item.get("title_original", "")} '
        f'{item.get("description", "")} '
        f'{item.get("description_original", "")}'
    )
    scores = {}
    matched_keywords = {}
    for topic, config in TOPIC_RULES.items():
        score, matched = topic_score(text, config["keywords"])
        score += hint_scores.get(topic, 0)
        scores[topic] = score
        matched_keywords[topic] = matched

    ranked = sorted(scores.items(), key=lambda row: (-row[1], row[0]))
    primary_topic = ranked[0][0] if ranked and ranked[0][1] > 0 else "uncategorized"
    secondary_topics = [topic for topic, score in ranked[1:] if score > 0]

    classified = dict(item)
    classified["primary_topic"] = primary_topic
    classified["secondary_topics"] = secondary_topics
    classified["classification"] = {
        "method": "keyword_score",
        "scores": scores,
        "matched_keywords": matched_keywords,
        "reason": build_reason(primary_topic, secondary_topics, matched_keywords),
    }
    return classified


def dedupe_news(items: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for item in sorted(items, key=lambda row: row.get("published_at", ""), reverse=True):
        key = (item.get("title", "").strip().lower(), item.get("source", ""))
        if key in seen or not item.get("title"):
            continue
        seen.add(key)
        deduped.append(classify_article(item))
    return deduped


def group_news(items: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        grouped[item.get("primary_topic", "uncategorized")].append(item)
    return dict(grouped)


def group_prices(items: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        grouped[item.get("market", "other")].append(item)
    return dict(grouped)


def price_line(item: dict) -> str:
    change = item.get("change_pct")
    if change is None:
        return f'{item["name"]}: {item["close"]:,.2f}'
    direction = "상승" if change > 0 else "하락" if change < 0 else "보합"
    return (
        f'{item["name"]}: {item["close"]:,.2f} '
        f'({abs(change):.2f}% {direction}, {item.get("as_of", "확인 전")} 기준)'
    )


def article_text(item: dict) -> str:
    return normalize_text(
        f'{item.get("title", "")} '
        f'{item.get("title_original", "")} '
        f'{item.get("description", "")} '
        f'{item.get("description_original", "")}'
    )


def matched_theme_counts(news: list[dict]) -> list[dict]:
    themes = []
    for theme in THEME_RULES:
        matched_items = []
        matched_days = set()
        for item in news:
            text = article_text(item).lower()
            if any(keyword.lower() in text for keyword in theme["keywords"]):
                matched_items.append(item)
                item_date = local_date(item.get("published_at", ""))
                if item_date:
                    matched_days.add(item_date.isoformat())
        if matched_items:
            sources = Counter(item.get("source", "출처 미상") for item in matched_items)
            themes.append(
                {
                    "name": theme["name"],
                    "count": len(matched_items),
                    "days": len(matched_days),
                    "sources": [source for source, _ in sources.most_common(3)],
                    "representatives": theme["representatives"],
                }
            )
    return sorted(themes, key=lambda row: (-row["count"], -row["days"], row["name"]))


def filter_by_keywords(news: list[dict], keywords: list[str], limit: int) -> list[dict]:
    matched = []
    for item in news:
        text = article_text(item).lower()
        if any(keyword.lower() in text for keyword in keywords):
            matched.append(item)
    return matched[:limit]


def article_reference(item: dict) -> str:
    source = item.get("source") or "출처 미상"
    published = local_date(item.get("published_at", ""))
    date_text = format_korean_date(published) if published else "날짜 미상"
    return f'{item.get("title", "제목 없음")} ({source}, {date_text})'


def linked_article_reference(item: dict) -> dict:
    return {
        "text": article_reference(item),
        "url": item.get("url", ""),
    }


def build_weekly_blocks(news: list[dict]) -> list[dict]:
    themes = matched_theme_counts(news)
    repeated = [theme for theme in themes if theme["count"] >= 2 or theme["days"] >= 2]
    one_off = [theme for theme in themes if theme not in repeated]
    catalysts = filter_by_keywords(news, CATALYST_KEYWORDS, 5) or news[:5]
    risks = filter_by_keywords(news, RISK_KEYWORDS, 5)

    recurring_items = [
        f'{theme["name"]}: 관련 기사 {theme["count"]}건, 관찰일 {theme["days"]}일, 주요 출처 {", ".join(theme["sources"])}'
        for theme in (repeated or themes[:5])
    ]
    if not recurring_items:
        recurring_items = ["해당 주 수집 기사에서 반복 강도가 뚜렷한 테마·섹터가 감지되지 않았습니다."]

    catalyst_items = [linked_article_reference(item) for item in catalysts]
    if not catalyst_items:
        catalyst_items = ["해당 주 기사 데이터 안에서 뉴스·정책·수급 촉매로 분류할 재료가 부족합니다."]

    sustainable_items = []
    if repeated:
        sustainable_items.append(
            "지속 관찰 후보: "
            + ", ".join(theme["name"] for theme in repeated[:4])
            + "처럼 복수 기사 또는 복수 관찰일에 반복 등장한 테마"
        )
    if one_off:
        sustainable_items.append(
            "단발성 후보: "
            + ", ".join(theme["name"] for theme in one_off[:4])
            + "처럼 한정된 기사에서만 감지된 테마"
        )
    if not sustainable_items:
        sustainable_items = ["반복 출현 기준으로 지속/단발 테마를 나눌 만큼의 주간 데이터가 아직 부족합니다."]

    schedule_items = [linked_article_reference(item) for item in risks]
    if not schedule_items:
        schedule_items = [
            "수집 기사에서 다음 주 일정이 직접 확인되지 않았습니다. 금리, 환율, 유가, 원자재 지표 변화와 미국 주요 경제지표 발표 여부를 우선 점검하세요."
        ]

    representative_items = [
        f'{theme["name"]}: {", ".join(theme["representatives"])}'
        for theme in themes[:5]
    ]
    if not representative_items:
        representative_items = ["테마별 대표 관찰 종목을 연결할 만큼의 테마 신호가 아직 부족합니다."]

    return [
        {"title": "한 주간 반복적으로 강했던 테마·섹터", "items": recurring_items},
        {"title": "주요 뉴스·정책·수급과 상승 촉매", "items": catalyst_items},
        {"title": "단발성 테마와 지속 가능한 테마 구분", "items": sustainable_items},
        {"title": "다음 주 주요 일정과 위험 요인", "items": schedule_items},
        {"title": "테마별 대표 관찰 종목", "items": representative_items},
    ]


def build_weekly_section(news_items: list[dict], generated_at: datetime) -> dict:
    start_date, end_date = weekly_window(generated_at)
    weekly_news = [
        item
        for item in news_items
        if (published := local_date(item.get("published_at", ""))) and start_date <= published <= end_date
    ]
    period = f"{format_korean_date(start_date)}~{format_korean_date(end_date)}"
    return {
        "id": "weekly",
        "title": "금주의 브리핑",
        "summary": f"{period} 기준으로 수집된 기사 {len(weekly_news)}건을 묶어 주간 테마와 위험 요인을 정리했습니다.",
        "prices": [],
        "articles": [],
        "article_count": len(weekly_news),
        "weekly_period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "label": period,
            "rule": "토요일 마감 기준. 토요일 전에는 직전 완료 구간을 표시합니다.",
        },
        "weekly_blocks": build_weekly_blocks(weekly_news),
        "empty_message": "해당 주간 구간에 포함되는 수집 기사가 아직 없습니다.",
    }


def summarize_section(topic: str, news: list[dict], prices: list[dict]) -> str:
    if news:
        lead = news[0]["title"]
        return f"{SECTION_LABELS[topic]} 핵심 기사: {lead}"
    if prices:
        return f"{SECTION_LABELS[topic]} 가격 데이터 {len(prices)}건이 수집되었습니다."
    return f"{SECTION_LABELS[topic]}에 배치된 기사가 없습니다."


def build_section(topic: str, prices: list[dict], news: list[dict]) -> dict:
    cards = [
        {
            "title": item["title"],
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "published_at": item.get("published_at", ""),
            "primary_topic": item.get("primary_topic", ""),
            "secondary_topics": item.get("secondary_topics", []),
        }
        for item in news[:8]
    ]
    return {
        "id": topic,
        "title": SECTION_LABELS.get(topic, topic),
        "summary": summarize_section(topic, news, prices),
        "prices": [price_line(item) for item in prices],
        "articles": cards,
        "article_count": len(news),
        "empty_message": "내용 기반 분류 결과 이 섹션에 배치된 기사가 없습니다." if not cards else "",
    }


def build_headline(news_items: list[dict]) -> str:
    if not news_items:
        return "아직 수집된 시황 데이터가 없습니다."
    return " / ".join(item["title"] for item in news_items[:3])


def classification_summary(news_items: list[dict]) -> dict:
    counts = Counter(item.get("primary_topic", "uncategorized") for item in news_items)
    return {
        "method": "content_keyword_score",
        "counts": dict(counts),
        "labels": SECTION_LABELS,
    }


def build_briefing(prices_payload: dict, news_payload: dict) -> dict:
    price_items = prices_payload.get("items", [])
    news_items = dedupe_news(news_payload.get("items", []))
    news_groups = group_news(news_items)
    price_groups = group_prices(price_items)
    generated_dt = datetime.now(timezone.utc)
    generated_at = generated_dt.isoformat()

    domestic_news = news_groups.get("domestic", [])
    us_news = news_groups.get("us", [])
    macro_news = news_groups.get("macro", [])
    sector_news = news_groups.get("sector", [])

    if sector_news:
        domestic_news = domestic_news + [item for item in sector_news if "domestic" in item.get("secondary_topics", [])]
        us_news = us_news + [item for item in sector_news if "us" in item.get("secondary_topics", [])]

    sections = {
        "domestic": build_section("domestic", price_groups.get("domestic", []), domestic_news),
        "us": build_section("us", price_groups.get("us", []), us_news),
        "macro": build_section("macro", price_groups.get("macro", []), macro_news),
        "sector": build_section("sector", [], sector_news),
        "weekly": build_weekly_section(news_items, generated_dt),
        "uncategorized": build_section("uncategorized", [], news_groups.get("uncategorized", [])),
    }

    return {
        "date": generated_at[:10],
        "generated_at": generated_at,
        "headline": build_headline(news_items),
        "sections": sections,
        "domestic": sections["domestic"],
        "us": sections["us"],
        "macro": sections["macro"],
        "sector": sections["sector"],
        "weekly": sections["weekly"],
        "uncategorized": sections["uncategorized"],
        "classification_summary": classification_summary(news_items),
        "collection_status": {
            "news_source": news_payload.get("source"),
            "price_source": prices_payload.get("source"),
            "news_query_counts": news_payload.get("query_counts", {}),
            "news_errors": news_payload.get("errors", []),
            "price_errors": prices_payload.get("errors", []),
        },
        "meta": {
            "mode": "dynamic-content-classified-us-market",
            "disclaimer": "기사는 공개 RSS를 통해 동적으로 수집한 결과입니다. 분류는 제목/설명 키워드 점수 기반입니다.",
        },
    }


def main() -> None:
    prices = load_json(RAW_DIR / "prices_dynamic.json", {"source": "not-collected", "items": [], "errors": []})
    news = load_json(RAW_DIR / "news_dynamic.json", {"source": "not-collected", "items": [], "errors": []})
    briefing = build_briefing(prices, news)

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    SERVING_DIR.mkdir(parents=True, exist_ok=True)
    daily_path = DAILY_DIR / "daily_market_briefing.json"
    serving_path = SERVING_DIR / "daily_market_briefing.json"
    serving_js_path = SERVING_DIR / "briefing-data.js"
    daily_path.write_text(json.dumps(briefing, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copyfile(daily_path, serving_path)
    serving_js_path.write_text(
        "window.DAILY_MARKET_BRIEFING = "
        + json.dumps(briefing, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    print(
        "Built briefing "
        f"articles={sum(section['article_count'] for section in briefing['sections'].values())} "
        f"generated_at={briefing['generated_at']}"
    )
    print(f"Wrote {daily_path}")
    print(f"Wrote {serving_path}")
    print(f"Wrote {serving_js_path}")


if __name__ == "__main__":
    main()
