"""Build a daily briefing JSON with content-based topic classification."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "storage" / "raw"
DAILY_DIR = ROOT / "storage" / "daily"
SERVING_DIR = ROOT / "serving"

SECTION_LABELS = {
    "domestic": "국내 증시",
    "us": "미국 증시",
    "macro": "금리·환율·유가·원자재",
    "sector": "섹터/테마",
    "uncategorized": "미분류",
}

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
    generated_at = datetime.now(timezone.utc).isoformat()

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
