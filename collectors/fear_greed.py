"""Collect fear and greed indicators from public endpoints."""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "storage" / "raw"


def fetch_json(url: str, extra_headers: dict | None = None) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 market-briefing-mvp",
        "Accept": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(
        url,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def clamp_score(value: float) -> int:
    return int(round(max(0, min(100, value))))


def sentiment_label(score: int) -> str:
    if score <= 24:
        return "극단적 공포"
    if score <= 44:
        return "공포"
    if score <= 55:
        return "중립"
    if score <= 75:
        return "탐욕"
    return "극단적 탐욕"


def normalize_label(value: str | None, score: int) -> str:
    labels = {
        "extreme fear": "극단적 공포",
        "fear": "공포",
        "neutral": "중립",
        "greed": "탐욕",
        "extreme greed": "극단적 탐욕",
    }
    return labels.get((value or "").strip().lower(), sentiment_label(score))


def change_summary(current: int, previous: int | None) -> dict:
    if previous is None:
        return {"previous_value": None, "change": None, "direction": "비교 불가"}
    change = current - previous
    return {
        "previous_value": previous,
        "change": change,
        "direction": "상승" if change > 0 else "하락" if change < 0 else "보합",
    }


def collect_us_fear_greed() -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.cnn.com",
        "Referer": "https://www.cnn.com/markets/fear-and-greed",
    }
    try:
        payload = fetch_json("https://production.dataviz.cnn.io/index/fearandgreed/current", headers)
    except Exception:
        payload = fetch_json("https://production.dataviz.cnn.io/index/fearandgreed/graphdata/2021-02-01", headers)
    current = payload.get("fear_and_greed", payload)
    history = payload.get("fear_and_greed_historical", {}).get("data", [])
    value = clamp_score(float(current["score"]))
    previous = current.get("previous_close")
    previous = clamp_score(float(previous)) if previous is not None else clamp_score(float(history[-2]["y"])) if len(history) >= 2 else None
    return {
        "id": "us-fear-greed",
        "name": "미국 공포탐욕지수",
        "market": "미국",
        "value": value,
        "label": normalize_label(current.get("rating"), value),
        "updated_at": current.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "source_name": "CNN Fear & Greed Index",
        "source_url": "https://www.cnn.com/markets/fear-and-greed",
        "method": "CNN Fear & Greed Index 공개 데이터",
        **change_summary(value, previous),
    }


def collect_crypto_fear_greed() -> dict:
    payload = fetch_json("https://api.alternative.me/fng/?limit=2&format=json")
    rows = payload.get("data", [])
    if not rows:
        raise ValueError("empty crypto fear and greed payload")
    value = clamp_score(float(rows[0]["value"]))
    previous = clamp_score(float(rows[1]["value"])) if len(rows) > 1 else None
    updated_at = datetime.fromtimestamp(int(rows[0]["timestamp"]), timezone.utc).isoformat()
    return {
        "id": "crypto-fear-greed",
        "name": "암호화폐 공포탐욕지수",
        "market": "가상자산",
        "value": value,
        "label": normalize_label(rows[0].get("value_classification"), value),
        "updated_at": updated_at,
        "source_name": "Alternative.me Crypto Fear & Greed Index",
        "source_url": "https://alternative.me/crypto/fear-and-greed-index/",
        "method": "Alternative.me Crypto Fear & Greed Index 공개 API",
        **change_summary(value, previous),
    }


def fetch_kospi_closes() -> tuple[list[float], str]:
    symbol = urllib.parse.quote("^KS11", safe="")
    payload = fetch_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1mo&interval=1d")
    result = payload["chart"]["result"][0]
    closes = [value for value in result["indicators"]["quote"][0]["close"] if value is not None]
    timestamps = result.get("timestamp", [])
    if len(closes) < 5:
        raise ValueError("not enough KOSPI close values")
    as_of = datetime.fromtimestamp(timestamps[-1], timezone.utc).date().isoformat() if timestamps else ""
    return closes, as_of


def kospi_proxy_score(closes: list[float]) -> int:
    current = closes[-1]
    previous = closes[-2]
    one_day = ((current / previous) - 1) * 100
    lookback = closes[-20:] if len(closes) >= 20 else closes
    low = min(lookback)
    high = max(lookback)
    range_position = 50 if math.isclose(high, low) else ((current - low) / (high - low)) * 100
    moving_average = sum(lookback) / len(lookback)
    momentum = ((current / moving_average) - 1) * 100
    raw_score = 50 + one_day * 8 + (range_position - 50) * 0.45 + momentum * 5
    return clamp_score(raw_score)


def collect_kospi_fear_greed() -> dict:
    closes, as_of = fetch_kospi_closes()
    value = kospi_proxy_score(closes)
    previous = kospi_proxy_score(closes[:-1]) if len(closes) > 5 else None
    return {
        "id": "kospi-fear-greed",
        "name": "코스피 공포탐욕지수",
        "market": "국내",
        "value": value,
        "label": sentiment_label(value),
        "updated_at": f"{as_of}T00:00:00+00:00" if as_of else datetime.now(timezone.utc).isoformat(),
        "source_name": "Yahoo Finance KOSPI chart",
        "source_url": "https://finance.yahoo.com/quote/%5EKS11",
        "method": "최근 1개월 KOSPI 종가의 일간 변화율, 구간 위치, 이동평균 모멘텀 기반 자체 산출",
        **change_summary(value, previous),
    }


def load_previous(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if payload.get("items") else None


def collect_fear_greed() -> dict:
    collected_at = datetime.now(timezone.utc).isoformat()
    collectors = [collect_us_fear_greed, collect_kospi_fear_greed, collect_crypto_fear_greed]
    items = []
    errors = []

    for collector in collectors:
        try:
            items.append(collector())
        except Exception as exc:
            errors.append({"collector": collector.__name__, "error": str(exc)})

    return {
        "collected_at": collected_at,
        "source": "dynamic-public-fear-greed",
        "items": items,
        "errors": errors,
    }


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / "fear_greed_dynamic.json"
    payload = collect_fear_greed()

    if len(payload["items"]) < 3:
        previous = load_previous(output_path)
        if previous:
            existing = {item["id"]: item for item in previous.get("items", [])}
            current = {item["id"]: item for item in payload["items"]}
            payload["items"] = list({**existing, **current}.values())
            payload["source"] = f"{payload['source']}-partial-stale-fallback"
            payload["fallback_at"] = datetime.now(timezone.utc).isoformat()

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path} items={len(payload['items'])} errors={len(payload['errors'])}")


if __name__ == "__main__":
    main()
