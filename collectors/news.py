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
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "storage" / "raw"

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
        "query": '금리 OR 환율 OR 유가 OR 원자재 OR 금 OR 은 OR 구리 OR 천연가스 OR 달러 OR 원화 OR FOMC OR Fed OR CPI OR "국채 금리"',
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


def collect_news() -> dict:
    collected_at = datetime.now(timezone.utc).isoformat()
    by_id: dict[str, dict] = {}
    errors: list[dict] = []
    query_counts: dict[str, int] = {}

    for config in QUERY_CONFIGS:
        query = config["query"]
        try:
            root = ElementTree.fromstring(fetch(rss_url(config), "application/rss+xml, application/xml, text/xml"))
        except Exception as exc:
            errors.append({"query": query, "error": str(exc)})
            query_counts[config["topic_hint"]] = 0
            continue

        nodes = root.findall("./channel/item")[:15]
        query_counts[config["topic_hint"]] = len(nodes)

        for node in nodes:
            original_title = clean_text(node.findtext("title"))
            link = clean_text(node.findtext("link"))
            original_description = clean_text(node.findtext("description"))
            published_at = parse_date(node.findtext("pubDate"))
            source_node = node.find("source")
            source = clean_text(source_node.text if source_node is not None else "")
            display_title = (
                translate_headline(original_title)
                if config["translate_headline"]
                else original_title
            )
            stable = hashlib.sha1(f"{original_title}|{link}".encode("utf-8")).hexdigest()[:16]

            if stable not in by_id:
                by_id[stable] = {
                    "id": stable,
                    "title": display_title,
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


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / "news_dynamic.json"
    payload = collect_news()
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
