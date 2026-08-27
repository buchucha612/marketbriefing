"""Collect market-commentary news from public RSS feeds.

Domestic and macro/sector stories are collected from Korean Google News RSS.
US market stories are collected from US English Google News RSS and only the
headline is translated into Korean for display.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "storage" / "raw"
KST = ZoneInfo("Asia/Seoul")

QUERY_CONFIGS = [
    {
        "topic_hint": "domestic",
        "query": '코스피 OR 코스닥 OR "국내 증시" OR "한국 증시" OR "서울 증시"',
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko",
        "translate_headline": False,
    },
    {
        "topic_hint": "us",
        "query": '"US stock market" OR "Wall Street" OR Nasdaq OR "S&P 500" OR Dow',
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
        "translate_headline": True,
    },
    {
        "topic_hint": "macro",
        "query": '금리 OR 환율 OR 유가 OR 원자재 OR "금값" OR "금 선물" OR "은 가격" OR "은 선물" OR 구리 OR 천연가스 OR 달러 OR 원화 OR FOMC OR Fed OR CPI OR "국채 금리"',
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko",
        "translate_headline": False,
    },
    {
        "topic_hint": "sector",
        "query": '반도체 OR AI OR "2차전지" OR 바이오 OR 조선 OR 방산 OR "증시 테마"',
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko",
        "translate_headline": False,
    },
]


def weekly_window(now: datetime) -> tuple[date, date]:
    local_now = now.astimezone(KST)
    days_since_saturday = (local_now.weekday() - 5) % 7
    end_date = (local_now - timedelta(days=days_since_saturday)).date()
    start_offset = 6 if local_now.weekday() == 5 else 5
    start_date = end_date - timedelta(days=start_offset)
    return start_date, end_date


def query_configs_for_run(now: datetime) -> list[dict]:
    start_date, end_date = weekly_window(now)
    before_date = end_date + timedelta(days=1)
    configs = list(QUERY_CONFIGS)

    for config in QUERY_CONFIGS:
        weekly_config = dict(config)
        weekly_config["query"] = (
            f'({config["query"]}) '
            f"after:{start_date.isoformat()} before:{before_date.isoformat()}"
        )
        weekly_config["query_label"] = f'{config["topic_hint"]}_weekly'
        configs.append(weekly_config)

    return configs


def fetch(url: str, accept: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            ),
            "Accept": accept,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).isoformat()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def rss_url(config: dict) -> str:
    params = {
        "q": config["query"],
        "hl": config["hl"],
        "gl": config["gl"],
        "ceid": config["ceid"],
    }
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


def translate_headline(text: str) -> str:
    if not text:
        return text
    params = {
        "client": "gtx",
        "sl": "en",
        "tl": "ko",
        "dt": "t",
        "q": text,
    }
    url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params)
    try:
        payload = json.loads(fetch(url, "application/json").decode("utf-8"))
    except Exception:
        return text
    translated = "".join(part[0] for part in payload[0] if part and part[0])
    return translated or text


def fallback_translate_headline(text: str) -> str:
    if not text:
        return text
    source = ""
    body = text
    if " - " in text:
        body, source = text.rsplit(" - ", 1)
        source = f" - {source}"

    replacements = [
        ("Dow Jones Futures", "다우존스 선물"),
        ("Nasdaq Futures", "나스닥 선물"),
        ("S&P 500 Futures", "S&P 500 선물"),
        ("Wall Street stocks", "월스트리트 주식"),
        ("U.S. Stocks", "미국 주식"),
        ("Stock Market Today", "오늘의 주식시장"),
        ("Market Rally", "시장 랠리"),
        ("Earnings Movers", "실적 관련 변동 종목"),
        ("hot inflation data", "높은 인플레이션 지표"),
        ("sales forecast", "매출 전망"),
        ("strong quarter", "강한 분기 실적"),
        ("eye-popping", "깜짝"),
        ("Investors Brace", "투자자들이 대비"),
        ("Chip Giant", "반도체 대형주"),
        ("Healthcare", "헬스케어"),
        ("Wall Street", "월스트리트"),
        ("Nvidia", "엔비디아"),
        ("Microsoft", "마이크로소프트"),
        ("Apple", "애플"),
        ("Alphabet", "알파벳"),
        ("Google", "구글"),
        ("Amazon", "아마존"),
        ("Meta", "메타"),
        ("Tesla", "테슬라"),
        ("Salesforce", "세일즈포스"),
        ("CrowdStrike", "크라우드스트라이크"),
        ("Okta", "옥타"),
        ("Micron", "마이크론"),
        ("Dow", "다우"),
        ("Nasdaq", "나스닥"),
        ("stocks", "주식"),
        ("stock", "주식"),
        ("futures", "선물"),
        ("rise", "상승"),
        ("rises", "상승"),
        ("higher", "상승"),
        ("gain", "상승"),
        ("gains", "상승"),
        ("surge", "급등"),
        ("jumps", "급등"),
        ("slides", "하락"),
        ("lower", "하락"),
        ("mixed", "혼조"),
        ("ends", "마감"),
        ("end", "마감"),
        ("ahead of", "앞두고"),
        ("after", "이후"),
        ("with", "함께"),
        ("as", "속"),
        ("lead", "주도"),
        ("results", "실적"),
        ("earnings", "실적"),
        ("forecast", "전망"),
        ("inflation", "인플레이션"),
        ("data", "지표"),
        ("investors", "투자자들"),
        ("serve", "서비스"),
        ("wows", "긍정적 반응 유도"),
        ("wow", "긍정적 반응 유도"),
        ("quarter", "분기 실적"),
        ("sales", "매출"),
        ("forecast", "전망"),
        ("results", "실적"),
        ("less-than-perfect", "기대 이하"),
        ("pull", "끌어내림"),
        ("pulls", "끌어내림"),
        ("healthcare", "헬스케어"),
        ("should", ""),
        ("not", "아닌"),
        ("and", "및"),
        ("or", "또는"),
        ("the", ""),
        ("a", ""),
        ("an", ""),
    ]
    translated = body
    for source_text, target_text in replacements:
        translated = re.sub(re.escape(source_text), target_text, translated, flags=re.IGNORECASE)
    translated = re.sub(r"\s+", " ", translated).strip(" ;:|")
    if is_likely_english(translated):
        translated = f"미국 증시 헤드라인: {translated}"
    return translated + source


def is_likely_english(text: str) -> bool:
    letters = re.findall(r"[A-Za-z]", text or "")
    korean = re.findall(r"[가-힣]", text or "")
    return len(letters) >= 12 and len(letters) > len(korean) * 2


def translated_display_title(title: str, should_translate: bool) -> tuple[str, str]:
    if should_translate and is_likely_english(title):
        translated = translate_headline(title)
        if is_likely_english(translated):
            translated = fallback_translate_headline(title)
        return translated, translated
    return title, ""


def collect_news() -> dict:
    collected_dt = datetime.now(timezone.utc)
    collected_at = collected_dt.isoformat()
    by_id: dict[str, dict] = {}
    errors: list[dict] = []
    query_counts: dict[str, int] = {}

    for config in query_configs_for_run(collected_dt):
        query = config["query"]
        query_label = config.get("query_label", config["topic_hint"])
        try:
            root = ElementTree.fromstring(fetch(rss_url(config), "application/rss+xml, application/xml, text/xml"))
        except Exception as exc:
            errors.append({"query": query, "error": str(exc)})
            query_counts[query_label] = 0
            continue

        nodes = root.findall("./channel/item")[:15]
        query_counts[query_label] = len(nodes)

        for node in nodes:
            original_title = clean_text(node.findtext("title"))
            link = clean_text(node.findtext("link"))
            original_description = clean_text(node.findtext("description"))
            published_at = parse_date(node.findtext("pubDate"))
            source_node = node.find("source")
            source = clean_text(source_node.text if source_node is not None else "")
            display_title, title_ko = translated_display_title(
                original_title,
                config["translate_headline"] or config["gl"] == "US",
            )
            stable = hashlib.sha1(f"{original_title}|{link}".encode("utf-8")).hexdigest()[:16]

            if stable not in by_id:
                by_id[stable] = {
                    "id": stable,
                    "title": display_title,
                    "title_ko": title_ko,
                    "title_original": original_title,
                    "description": original_description,
                    "description_original": original_description,
                    "source": source or "Google News",
                    "source_locale": config["gl"],
                    "url": link,
                    "published_at": published_at,
                    "matched_queries": [],
                    "topic_hints": [],
                }
            elif title_ko:
                by_id[stable]["title"] = title_ko
                by_id[stable]["title_ko"] = title_ko
            by_id[stable]["matched_queries"].append(query)
            by_id[stable]["topic_hints"].append(config["topic_hint"])

    items = sorted(by_id.values(), key=lambda item: item["published_at"], reverse=True)
    return {
        "collected_at": collected_at,
        "source": "google-news-rss",
        "items": items,
        "query_counts": query_counts,
        "errors": errors,
    }


def load_previous_news(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("items"):
        return payload
    return None


def refresh_translated_titles(payload: dict) -> dict:
    refreshed_items = []
    for item in payload.get("items", []):
        refreshed = dict(item)
        should_translate = refreshed.get("source_locale") == "US" or "us" in refreshed.get("topic_hints", [])
        title = refreshed.get("title_original") or refreshed.get("title", "")
        if should_translate and is_likely_english(refreshed.get("title", "")):
            translated, title_ko = translated_display_title(title, True)
            refreshed["title"] = translated
            refreshed["title_ko"] = title_ko
        refreshed_items.append(refreshed)
    return {**payload, "items": refreshed_items}


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / "news_dynamic.json"
    payload = collect_news()

    if not payload["items"] and payload["errors"]:
        previous = load_previous_news(output_path)
        if previous:
            payload = {
                **previous,
                "source": f"{previous.get('source', 'google-news-rss')}-stale-fallback",
                "fallback_reason": "latest_google_news_rss_collection_failed",
                "fallback_at": datetime.now(timezone.utc).isoformat(),
                "latest_errors": payload["errors"],
            }

    payload = refresh_translated_titles(payload)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        "Wrote "
        f"{output_path} "
        f"items={len(payload['items'])} "
        f"query_counts={payload['query_counts']} "
        f"errors={len(payload['errors'])}"
    )


if __name__ == "__main__":
    main()
