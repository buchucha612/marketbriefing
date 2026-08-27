"""Collect weekly stock flow candidates from public market data."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "storage" / "raw"

STOCK_UNIVERSE = [
    {"symbol": "005930.KS", "name": "삼성전자", "market": "국내"},
    {"symbol": "000660.KS", "name": "SK하이닉스", "market": "국내"},
    {"symbol": "042700.KS", "name": "한미반도체", "market": "국내"},
    {"symbol": "373220.KS", "name": "LG에너지솔루션", "market": "국내"},
    {"symbol": "005380.KS", "name": "현대차", "market": "국내"},
    {"symbol": "000270.KS", "name": "기아", "market": "국내"},
    {"symbol": "035420.KS", "name": "NAVER", "market": "국내"},
    {"symbol": "035720.KS", "name": "카카오", "market": "국내"},
    {"symbol": "207940.KS", "name": "삼성바이오로직스", "market": "국내"},
    {"symbol": "068270.KS", "name": "셀트리온", "market": "국내"},
    {"symbol": "329180.KS", "name": "HD현대중공업", "market": "국내"},
    {"symbol": "042660.KS", "name": "한화오션", "market": "국내"},
    {"symbol": "034020.KS", "name": "두산에너빌리티", "market": "국내"},
    {"symbol": "012450.KS", "name": "한화에어로스페이스", "market": "국내"},
    {"symbol": "NVDA", "name": "엔비디아", "market": "미국"},
    {"symbol": "MSFT", "name": "마이크로소프트", "market": "미국"},
    {"symbol": "AAPL", "name": "애플", "market": "미국"},
    {"symbol": "GOOGL", "name": "알파벳", "market": "미국"},
    {"symbol": "AMZN", "name": "아마존", "market": "미국"},
    {"symbol": "META", "name": "메타", "market": "미국"},
    {"symbol": "TSLA", "name": "테슬라", "market": "미국"},
    {"symbol": "AMD", "name": "AMD", "market": "미국"},
    {"symbol": "AVGO", "name": "브로드컴", "market": "미국"},
    {"symbol": "PLTR", "name": "팔란티어", "market": "미국"},
    {"symbol": "CRWD", "name": "크라우드스트라이크", "market": "미국"},
]


def fetch_yahoo_chart(symbol: str) -> dict:
    encoded = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=3mo&interval=1d"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 market-briefing-mvp",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0


def parse_stock_flow(config: dict, payload: dict) -> dict:
    result = payload["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    rows = [
        {
            "close": close,
            "volume": volume,
        }
        for close, volume in zip(quote.get("close", []), quote.get("volume", []))
        if close is not None and volume is not None and volume > 0
    ]
    if len(rows) < 10:
        raise ValueError("not enough close/volume values")

    recent = rows[-5:]
    baseline = rows[-25:-5] if len(rows) >= 25 else rows[:-5]
    latest = recent[-1]
    first = recent[0]
    weekly_change_pct = ((latest["close"] / first["close"]) - 1) * 100
    recent_avg_volume = mean([row["volume"] for row in recent])
    baseline_avg_volume = mean([row["volume"] for row in baseline])
    volume_ratio = recent_avg_volume / baseline_avg_volume if baseline_avg_volume else 0
    avg_turnover = mean([row["close"] * row["volume"] for row in recent])
    score = volume_ratio * 45 + max(weekly_change_pct, 0) * 4 + min(avg_turnover / 1_000_000_000, 35)

    timestamps = result.get("timestamp", [])
    as_of = datetime.fromtimestamp(timestamps[-1], timezone.utc).date().isoformat() if timestamps else ""
    return {
        "symbol": config["symbol"],
        "name": config["name"],
        "market": config["market"],
        "weekly_change_pct": round(weekly_change_pct, 2),
        "volume_ratio": round(volume_ratio, 2),
        "avg_volume": round(recent_avg_volume),
        "avg_turnover": round(avg_turnover),
        "score": round(score, 2),
        "as_of": as_of,
        "source_name": "Yahoo Finance chart API",
        "source_url": "https://finance.yahoo.com/quote/" + urllib.parse.quote(config["symbol"], safe=""),
    }


def collect_stock_flows() -> dict:
    collected_at = datetime.now(timezone.utc).isoformat()
    items = []
    errors = []

    for config in STOCK_UNIVERSE:
        try:
            items.append(parse_stock_flow(config, fetch_yahoo_chart(config["symbol"])))
        except Exception as exc:
            errors.append({"symbol": config["symbol"], "name": config["name"], "error": str(exc)})

    ranked = sorted(items, key=lambda item: (-item["score"], -item["avg_turnover"], item["name"]))
    return {
        "collected_at": collected_at,
        "source": "dynamic-public-stock-flow",
        "items": ranked,
        "errors": errors,
        "method": "최근 5거래일 평균 거래대금, 직전 구간 대비 거래량 증가율, 주간 등락률 기반",
    }


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / "stock_flows_dynamic.json"
    payload = collect_stock_flows()
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path} items={len(payload['items'])} errors={len(payload['errors'])}")


if __name__ == "__main__":
    main()
