"""Dynamic price collector.

The collector attempts public chart endpoints and never writes fake prices.
Failures are captured in the output errors array.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "storage" / "raw"

SYMBOLS = [
    {"symbol": "^KS11", "name": "코스피", "market": "domestic"},
    {"symbol": "^KQ11", "name": "코스닥", "market": "domestic"},
    {"symbol": "^GSPC", "name": "S&P 500", "market": "us"},
    {"symbol": "^IXIC", "name": "나스닥 종합", "market": "us"},
    {"symbol": "^DJI", "name": "다우존스", "market": "us"},
    {"symbol": "KRW=X", "name": "원/달러 환율", "market": "macro", "unit": "KRW"},
    {"symbol": "JPYKRW=X", "name": "원/엔 환율(100엔)", "market": "macro", "scale": 100, "unit": "KRW"},
    {"symbol": "CL=F", "name": "WTI 원유", "market": "macro"},
    {"symbol": "BZ=F", "name": "브렌트유", "market": "macro"},
    {"symbol": "GC=F", "name": "금", "market": "macro"},
    {"symbol": "SI=F", "name": "은", "market": "macro"},
    {"symbol": "HG=F", "name": "구리", "market": "macro"},
    {"symbol": "NG=F", "name": "천연가스", "market": "macro"},
    {"symbol": "^TNX", "name": "미국채 10년물 금리", "market": "macro", "unit": "%"},
    {"symbol": "^TYX", "name": "미국채 30년물 금리", "market": "macro", "unit": "%"},
    {"symbol": "BTC-USD", "name": "비트코인", "market": "macro", "unit": "USD"},
    {"symbol": "ETH-USD", "name": "이더리움", "market": "macro", "unit": "USD"},
]


def fetch_yahoo_chart(symbol: str) -> dict:
    encoded = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=5d&interval=1d"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 market-briefing-mvp",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_chart(config: dict, payload: dict) -> dict:
    result = payload["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    closes = [value for value in quote["close"] if value is not None]
    timestamps = result["timestamp"]
    if len(closes) < 2:
        raise ValueError("not enough close values")
    scale = config.get("scale", 1)
    close = closes[-1] * scale
    previous = closes[-2] * scale
    change_pct = ((close - previous) / previous) * 100
    return {
        "symbol": config["symbol"],
        "name": config["name"],
        "market": config["market"],
        "close": round(close, 2),
        "change_pct": round(change_pct, 2),
        "unit": config.get("unit", ""),
        "as_of": datetime.fromtimestamp(timestamps[-1], timezone.utc).date().isoformat(),
        "source_name": "Yahoo Finance chart API",
        "source_url": "https://finance.yahoo.com/quote/" + urllib.parse.quote(config["symbol"], safe=""),
    }


def collect_prices() -> dict:
    collected_at = datetime.now(timezone.utc).isoformat()
    items: list[dict] = []
    errors: list[dict] = []

    for config in SYMBOLS:
        try:
            items.append(parse_chart(config, fetch_yahoo_chart(config["symbol"])))
        except Exception as exc:
            errors.append({"symbol": config["symbol"], "name": config["name"], "error": str(exc)})

    return {
        "collected_at": collected_at,
        "source": "dynamic-public-chart",
        "items": items,
        "errors": errors,
    }


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / "prices_dynamic.json"
    payload = collect_prices()
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {output_path} items={len(payload['items'])} errors={len(payload['errors'])}")


if __name__ == "__main__":
    main()
