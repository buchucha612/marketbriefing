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
    "macro": "시장지표 관련",
    "sector": "섹터/테마",
    "weekly": "금주의 브리핑",
    "schedule": "주요 일정 정리",
    "feargreed": "공포탐욕지수",
    "uncategorized": "미분류",
}

ECONOMIC_EVENTS = [
    {
        "id": "us-pce-2026-08",
        "start": "2026-08-26",
        "title": "미국 PCE 물가·개인소득/지출 발표",
        "region": "미국",
        "category": "물가",
        "impact": "높음",
        "detail": "BEA Personal Income and Outlays, July 2026. 연준이 선호하는 물가 지표라 금리 기대에 민감합니다.",
        "source": "U.S. BEA",
        "source_url": "https://www.bea.gov/news/schedule",
    },
    {
        "id": "us-gdp-2026-q2-second",
        "start": "2026-08-26",
        "title": "미국 2분기 GDP 2차 추정",
        "region": "미국",
        "category": "성장",
        "impact": "중간",
        "detail": "미국 경기 강도와 금리 전망을 같이 흔들 수 있는 성장 지표입니다.",
        "source": "U.S. BEA",
        "source_url": "https://www.bea.gov/news/schedule",
    },
    {
        "id": "bok-interest-rates-2026-07",
        "start": "2026-08-26",
        "title": "한국 7월 시장금리 통계",
        "region": "국내",
        "category": "금리",
        "impact": "중간",
        "detail": "한국은행 통계 공표 일정의 Interest Rates in July 2026입니다.",
        "source": "Bank of Korea",
        "source_url": "https://www.bok.or.kr/eng/stats/statsPublictSchdul/listCldr.do?menuNo=400359",
    },
    {
        "id": "bok-rate-2026-08",
        "start": "2026-08-27",
        "title": "한국은행 금융통화위원회 기준금리 결정",
        "region": "국내",
        "category": "금리",
        "impact": "높음",
        "detail": "기준금리 결정과 경제전망 코멘트가 국내 금리, 환율, 금융주에 영향을 줄 수 있습니다.",
        "source": "Bank of Korea",
        "source_url": "https://www.bok.or.kr/eng/bbs/E0000627/view.do?menuNo=400022&nttId=10094301",
    },
    {
        "id": "jackson-hole-2026",
        "start": "2026-08-27",
        "end": "2026-08-29",
        "title": "잭슨홀 경제정책 심포지엄",
        "region": "미국",
        "category": "중앙은행",
        "impact": "높음",
        "detail": "2026년 주제는 Financial Innovation: Implications for Payments and Policy입니다. 연준 및 주요 중앙은행 발언에 주목합니다.",
        "source": "Federal Reserve Bank of Kansas City",
        "source_url": "https://www.kansascityfed.org/research/jackson-hole-economic-symposium/jackson-hole-faqs/",
    },
    {
        "id": "kr-industrial-2026-07",
        "start": "2026-08-31",
        "title": "한국 7월 산업활동동향",
        "region": "국내",
        "category": "경기",
        "impact": "중간",
        "detail": "생산, 소비, 투자 흐름을 확인하는 국내 경기 지표입니다.",
        "source": "Ministry of Data and Statistics",
        "source_url": "https://mods.go.kr/schdl.es?mid=a20301000000",
    },
    {
        "id": "kr-cpi-2026-08",
        "start": "2026-09-02",
        "title": "한국 8월 소비자물가동향",
        "region": "국내",
        "category": "물가",
        "impact": "높음",
        "detail": "국내 물가 압력과 한국은행 금리 경로 기대에 영향을 줄 수 있습니다.",
        "source": "Ministry of Data and Statistics",
        "source_url": "https://mods.go.kr/cpiOaSchdlView.es?mid=b70203020000",
    },
    {
        "id": "us-fomc-2026-09",
        "start": "2026-09-15",
        "end": "2026-09-16",
        "title": "미국 FOMC 정례회의",
        "region": "미국",
        "category": "금리",
        "impact": "높음",
        "detail": "점도표와 경제전망이 함께 나오는 회의입니다.",
        "source": "Federal Reserve",
        "source_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    },
    {
        "id": "us-pce-2026-09",
        "start": "2026-09-30",
        "title": "미국 PCE 물가·개인소득/지출 발표",
        "region": "미국",
        "category": "물가",
        "impact": "높음",
        "detail": "BEA Personal Income and Outlays, August 2026입니다.",
        "source": "U.S. BEA",
        "source_url": "https://www.bea.gov/news/schedule",
    },
    {
        "id": "bok-rate-2026-10",
        "start": "2026-10-22",
        "title": "한국은행 금융통화위원회 기준금리 결정",
        "region": "국내",
        "category": "금리",
        "impact": "높음",
        "detail": "국내 기준금리와 금융안정 관련 메시지를 확인하는 일정입니다.",
        "source": "Bank of Korea",
        "source_url": "https://www.bok.or.kr/eng/bbs/E0000627/view.do?menuNo=400022&nttId=10094301",
    },
    {
        "id": "us-fomc-2026-10",
        "start": "2026-10-27",
        "end": "2026-10-28",
        "title": "미국 FOMC 정례회의",
        "region": "미국",
        "category": "금리",
        "impact": "높음",
        "detail": "정책금리 결정과 기자회견을 확인하는 일정입니다.",
        "source": "Federal Reserve",
        "source_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    },
    {
        "id": "us-pce-2026-10",
        "start": "2026-10-29",
        "title": "미국 PCE 물가·개인소득/지출 발표",
        "region": "미국",
        "category": "물가",
        "impact": "높음",
        "detail": "BEA Personal Income and Outlays, September 2026입니다.",
        "source": "U.S. BEA",
        "source_url": "https://www.bea.gov/news/schedule",
    },
    {
        "id": "bok-rate-2026-11",
        "start": "2026-11-26",
        "title": "한국은행 금융통화위원회 기준금리 결정",
        "region": "국내",
        "category": "금리",
        "impact": "높음",
        "detail": "연말 국내 금리 경로와 환율 민감도를 점검하는 일정입니다.",
        "source": "Bank of Korea",
        "source_url": "https://www.bok.or.kr/eng/bbs/E0000627/view.do?menuNo=400022&nttId=10094301",
    },
    {
        "id": "us-pce-2026-11",
        "start": "2026-11-25",
        "title": "미국 PCE 물가·개인소득/지출 발표",
        "region": "미국",
        "category": "물가",
        "impact": "높음",
        "detail": "BEA Personal Income and Outlays, October 2026입니다.",
        "source": "U.S. BEA",
        "source_url": "https://www.bea.gov/news/schedule",
    },
    {
        "id": "us-fomc-2026-12",
        "start": "2026-12-08",
        "end": "2026-12-09",
        "title": "미국 FOMC 정례회의",
        "region": "미국",
        "category": "금리",
        "impact": "높음",
        "detail": "점도표와 경제전망이 함께 나오는 연말 회의입니다.",
        "source": "Federal Reserve",
        "source_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    },
    {
        "id": "us-pce-2026-12",
        "start": "2026-12-23",
        "title": "미국 PCE 물가·개인소득/지출 발표",
        "region": "미국",
        "category": "물가",
        "impact": "높음",
        "detail": "BEA Personal Income and Outlays, November 2026입니다.",
        "source": "U.S. BEA",
        "source_url": "https://www.bea.gov/news/schedule",
    },
]

EARNINGS_EVENTS = [
    {
        "id": "earnings-us-pdd-2026-08-24",
        "date": "2026-08-24",
        "region": "미국",
        "ticker": "PDD",
        "company": "PDD Holdings",
        "timing": "시간 미정",
        "importance": "중간",
        "source": "EarningsCountdown",
        "source_url": "https://earningscountdown.com/earnings-calendar/2026-08-24/",
    },
    {
        "id": "earnings-us-xpev-2026-08-24",
        "date": "2026-08-24",
        "region": "미국",
        "ticker": "XPEV",
        "company": "XPeng",
        "timing": "장전",
        "importance": "중간",
        "source": "EarningsCountdown",
        "source_url": "https://earningscountdown.com/earnings-calendar/2026-08-24/",
    },
    {
        "id": "earnings-us-intu-2026-08-25",
        "date": "2026-08-25",
        "region": "미국",
        "ticker": "INTU",
        "company": "Intuit",
        "timing": "장후",
        "importance": "높음",
        "source": "EarningsCountdown",
        "source_url": "https://earningscountdown.com/earnings-calendar/2026-08-24/",
    },
    {
        "id": "earnings-us-nvda-2026-08-26",
        "date": "2026-08-26",
        "region": "미국",
        "ticker": "NVDA",
        "company": "NVIDIA",
        "timing": "장후",
        "importance": "높음",
        "source": "EarningsCountdown",
        "source_url": "https://earningscountdown.com/earnings-calendar/2026-08-24/",
    },
    {
        "id": "earnings-us-crm-2026-08-26",
        "date": "2026-08-26",
        "region": "미국",
        "ticker": "CRM",
        "company": "Salesforce",
        "timing": "장후",
        "importance": "높음",
        "source": "EarningsCountdown",
        "source_url": "https://earningscountdown.com/earnings-calendar/2026-08-24/",
    },
    {
        "id": "earnings-us-crwd-2026-08-26",
        "date": "2026-08-26",
        "region": "미국",
        "ticker": "CRWD",
        "company": "CrowdStrike",
        "timing": "장후",
        "importance": "높음",
        "source": "EarningsCountdown",
        "source_url": "https://earningscountdown.com/earnings-calendar/2026-08-24/",
    },
    {
        "id": "earnings-us-snps-2026-08-26",
        "date": "2026-08-26",
        "region": "미국",
        "ticker": "SNPS",
        "company": "Synopsys",
        "timing": "장후",
        "importance": "중간",
        "source": "EarningsCountdown",
        "source_url": "https://earningscountdown.com/earnings-calendar/2026-08-24/",
    },
    {
        "id": "earnings-us-bby-2026-08-27",
        "date": "2026-08-27",
        "region": "미국",
        "ticker": "BBY",
        "company": "Best Buy",
        "timing": "장전",
        "importance": "중간",
        "source": "EarningsCountdown",
        "source_url": "https://earningscountdown.com/earnings-calendar/2026-08-24/",
    },
    {
        "id": "earnings-us-dltr-2026-08-27",
        "date": "2026-08-27",
        "region": "미국",
        "ticker": "DLTR",
        "company": "Dollar Tree",
        "timing": "장전",
        "importance": "중간",
        "source": "EarningsCountdown",
        "source_url": "https://earningscountdown.com/earnings-calendar/2026-08-24/",
    },
    {
        "id": "earnings-us-adsk-2026-08-27",
        "date": "2026-08-27",
        "region": "미국",
        "ticker": "ADSK",
        "company": "Autodesk",
        "timing": "장후",
        "importance": "중간",
        "source": "EarningsCountdown",
        "source_url": "https://earningscountdown.com/earnings-calendar/2026-08-24/",
    },
    {
        "id": "earnings-us-ulta-2026-08-27",
        "date": "2026-08-27",
        "region": "미국",
        "ticker": "ULTA",
        "company": "Ulta Beauty",
        "timing": "장후",
        "importance": "중간",
        "source": "EarningsCountdown",
        "source_url": "https://earningscountdown.com/earnings-calendar/2026-08-24/",
    },
    {
        "id": "earnings-us-avgo-2026-09-02",
        "date": "2026-09-02",
        "region": "미국",
        "ticker": "AVGO",
        "company": "Broadcom",
        "timing": "장후",
        "importance": "자동",
        "source": "Broadcom IR",
        "source_url": "https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announce-third-quarter-fiscal-year-2026-financial",
    },
]

MAX_WEEKLY_EARNINGS = 15

MAJOR_EARNINGS_COMPANIES = {
    "AAPL": {"tier": 1, "sector": "빅테크", "indexes": ["S&P 500", "Nasdaq 100"]},
    "MSFT": {"tier": 1, "sector": "빅테크", "indexes": ["S&P 500", "Nasdaq 100"]},
    "NVDA": {"tier": 1, "sector": "반도체·AI", "indexes": ["S&P 500", "Nasdaq 100"]},
    "AVGO": {"tier": 1, "sector": "반도체·AI", "indexes": ["S&P 500", "Nasdaq 100"]},
    "AMZN": {"tier": 1, "sector": "빅테크", "indexes": ["S&P 500", "Nasdaq 100"]},
    "GOOGL": {"tier": 1, "sector": "빅테크", "indexes": ["S&P 500", "Nasdaq 100"]},
    "GOOG": {"tier": 1, "sector": "빅테크", "indexes": ["S&P 500", "Nasdaq 100"]},
    "META": {"tier": 1, "sector": "빅테크", "indexes": ["S&P 500", "Nasdaq 100"]},
    "TSLA": {"tier": 1, "sector": "전기차", "indexes": ["S&P 500", "Nasdaq 100"]},
    "CRM": {"tier": 2, "sector": "소프트웨어", "indexes": ["S&P 500"]},
    "ORCL": {"tier": 2, "sector": "소프트웨어", "indexes": ["S&P 500"]},
    "INTU": {"tier": 2, "sector": "소프트웨어", "indexes": ["S&P 500", "Nasdaq 100"]},
    "ADBE": {"tier": 2, "sector": "소프트웨어", "indexes": ["S&P 500", "Nasdaq 100"]},
    "AMD": {"tier": 2, "sector": "반도체·AI", "indexes": ["S&P 500", "Nasdaq 100"]},
    "QCOM": {"tier": 2, "sector": "반도체", "indexes": ["S&P 500", "Nasdaq 100"]},
    "TXN": {"tier": 2, "sector": "반도체", "indexes": ["S&P 500", "Nasdaq 100"]},
    "MU": {"tier": 2, "sector": "반도체", "indexes": ["S&P 500", "Nasdaq 100"]},
    "JPM": {"tier": 2, "sector": "금융", "indexes": ["S&P 500"]},
    "BAC": {"tier": 2, "sector": "금융", "indexes": ["S&P 500"]},
    "GS": {"tier": 2, "sector": "금융", "indexes": ["S&P 500"]},
    "WMT": {"tier": 2, "sector": "소비", "indexes": ["S&P 500"]},
    "COST": {"tier": 2, "sector": "소비", "indexes": ["S&P 500", "Nasdaq 100"]},
    "HD": {"tier": 2, "sector": "소비", "indexes": ["S&P 500"]},
    "UNH": {"tier": 2, "sector": "헬스케어", "indexes": ["S&P 500"]},
    "LLY": {"tier": 2, "sector": "헬스케어", "indexes": ["S&P 500"]},
    "JNJ": {"tier": 2, "sector": "헬스케어", "indexes": ["S&P 500"]},
    "XOM": {"tier": 2, "sector": "에너지", "indexes": ["S&P 500"]},
    "CVX": {"tier": 2, "sector": "에너지", "indexes": ["S&P 500"]},
    "CRWD": {"tier": 3, "sector": "사이버보안", "indexes": ["Nasdaq 100"]},
    "SNPS": {"tier": 3, "sector": "반도체 설계", "indexes": ["S&P 500", "Nasdaq 100"]},
    "ADSK": {"tier": 3, "sector": "소프트웨어", "indexes": ["S&P 500", "Nasdaq 100"]},
    "PDD": {"tier": 3, "sector": "중국 플랫폼", "indexes": ["Nasdaq 100"]},
}

MAJOR_DOMESTIC_EARNINGS_COMPANIES = {
    "005930": {"tier": 1, "sector": "반도체·IT", "indexes": ["KOSPI 200"]},
    "000660": {"tier": 1, "sector": "반도체·AI", "indexes": ["KOSPI 200"]},
    "373220": {"tier": 1, "sector": "2차전지", "indexes": ["KOSPI 200"]},
    "207940": {"tier": 1, "sector": "바이오", "indexes": ["KOSPI 200"]},
    "005380": {"tier": 1, "sector": "자동차", "indexes": ["KOSPI 200"]},
    "000270": {"tier": 1, "sector": "자동차", "indexes": ["KOSPI 200"]},
    "035420": {"tier": 1, "sector": "인터넷", "indexes": ["KOSPI 200"]},
    "035720": {"tier": 1, "sector": "인터넷", "indexes": ["KOSPI 200"]},
    "006400": {"tier": 2, "sector": "2차전지", "indexes": ["KOSPI 200"]},
    "051910": {"tier": 2, "sector": "화학·2차전지", "indexes": ["KOSPI 200"]},
    "068270": {"tier": 2, "sector": "바이오", "indexes": ["KOSPI 200"]},
    "028260": {"tier": 2, "sector": "지주·건설", "indexes": ["KOSPI 200"]},
    "012330": {"tier": 2, "sector": "자동차부품", "indexes": ["KOSPI 200"]},
    "105560": {"tier": 2, "sector": "금융", "indexes": ["KOSPI 200"]},
    "055550": {"tier": 2, "sector": "금융", "indexes": ["KOSPI 200"]},
    "086790": {"tier": 2, "sector": "금융", "indexes": ["KOSPI 200"]},
    "032830": {"tier": 2, "sector": "보험", "indexes": ["KOSPI 200"]},
    "003550": {"tier": 2, "sector": "지주", "indexes": ["KOSPI 200"]},
    "034730": {"tier": 2, "sector": "지주·에너지", "indexes": ["KOSPI 200"]},
    "096770": {"tier": 2, "sector": "에너지", "indexes": ["KOSPI 200"]},
    "009540": {"tier": 2, "sector": "조선", "indexes": ["KOSPI 200"]},
    "042660": {"tier": 2, "sector": "조선", "indexes": ["KOSPI 200"]},
    "329180": {"tier": 2, "sector": "조선", "indexes": ["KOSPI 200"]},
    "012450": {"tier": 2, "sector": "방산", "indexes": ["KOSPI 200"]},
    "047810": {"tier": 2, "sector": "방산", "indexes": ["KOSPI 200"]},
    "352820": {"tier": 2, "sector": "엔터", "indexes": ["KOSPI 200"]},
    "247540": {"tier": 2, "sector": "2차전지", "indexes": ["KOSDAQ 150"]},
    "086520": {"tier": 2, "sector": "2차전지", "indexes": ["KOSDAQ 150"]},
    "196170": {"tier": 2, "sector": "바이오", "indexes": ["KOSDAQ 150"]},
    "141080": {"tier": 2, "sector": "바이오", "indexes": ["KOSDAQ 150"]},
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
            "Dow Jones",
            "Dow futures",
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

FOCUS_GROUPS = [
    ("samsung_electronics", ["삼성전자", "samsung electronics"]),
    ("sk_hynix", ["sk하이닉스", "sk hynix", "하이닉스"]),
    ("hyundai_motor", ["현대차", "기아", "hyundai motor", "kia"]),
    ("kakao_naver", ["네이버", "카카오", "naver", "kakao"]),
    ("korea_rates", ["한은", "한국은행", "기준금리", "금리 인상", "금리하락", "금리 하락"]),
    ("korea_flows", ["외국인", "기관", "개인투자자", "수급"]),
    ("nvidia", ["엔비디아", "nvidia", "nvda"]),
    ("tesla", ["테슬라", "tesla", "tsla"]),
    ("apple", ["애플", "apple", "aapl"]),
    ("microsoft", ["마이크로소프트", "microsoft", "msft"]),
    ("meta", ["메타", "meta"]),
    ("alphabet", ["알파벳", "구글", "alphabet", "google", "goog", "googl"]),
    ("amazon", ["아마존", "amazon", "amzn"]),
    ("semiconductor", ["반도체", "hbm", "마이크론", "micron", "amd", "sk하이닉스", "삼성전자"]),
    ("ai", [" ai ", "인공지능", "피지컬 ai", "생성형 ai"]),
    ("rates", ["금리", "fed", "fomc", "국채", "yield", "treasury"]),
]


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


def current_week_window(now: datetime) -> tuple[date, date]:
    today = now.astimezone(KST).date()
    days_since_sunday = (today.weekday() + 1) % 7
    start_date = today - timedelta(days=days_since_sunday)
    return start_date, start_date + timedelta(days=6)


def parse_event_date(value: str) -> date:
    return date.fromisoformat(value)


def normalize_event(event: dict) -> dict:
    start_date = parse_event_date(event["start"])
    end_date = parse_event_date(event.get("end", event["start"]))
    normalized = dict(event)
    normalized["start"] = start_date.isoformat()
    normalized["end"] = end_date.isoformat()
    normalized["date_label"] = (
        format_korean_date(start_date)
        if start_date == end_date
        else f"{format_korean_date(start_date)}~{format_korean_date(end_date)}"
    )
    return normalized


def event_overlaps(event: dict, start_date: date, end_date: date) -> bool:
    event_start = parse_event_date(event["start"])
    event_end = parse_event_date(event.get("end", event["start"]))
    return event_start <= end_date and event_end >= start_date


def normalize_earnings_event(event: dict) -> dict:
    normalized = dict(event)
    ticker = normalized.get("ticker", "").upper()
    if normalized.get("region") == "국내":
        profile = MAJOR_DOMESTIC_EARNINGS_COMPANIES.get(ticker)
        method = "major_domestic_company_universe"
    else:
        profile = MAJOR_EARNINGS_COMPANIES.get(ticker)
        method = "major_us_company_universe"
    if profile:
        normalized["importance"] = "높음"
        normalized["importance_basis"] = {
            "method": method,
            "tier": profile["tier"],
            "sector": profile["sector"],
            "indexes": profile["indexes"],
        }
    else:
        normalized["importance_basis"] = {
            "method": "manual_importance",
        }
    return normalized


def is_major_earnings_event(event: dict) -> bool:
    ticker = event.get("ticker", "").upper()
    if event.get("region") == "국내":
        return event.get("importance") == "높음" or ticker in MAJOR_DOMESTIC_EARNINGS_COMPANIES
    return event.get("importance") == "높음" or ticker in MAJOR_EARNINGS_COMPANIES


def limit_week_earnings_by_region(events: list[dict]) -> dict[str, list[dict]]:
    grouped = {
        "domestic": [event for event in events if event["region"] == "국내"],
        "us": [event for event in events if event["region"] == "미국"],
    }
    return {
        region: sorted(
            rows,
            key=lambda row: (
                row.get("importance_basis", {}).get("tier", 9),
                row["date"],
                row["ticker"],
            ),
        )[:MAX_WEEKLY_EARNINGS]
        for region, rows in grouped.items()
    }


def events_on_date(events: list[dict], target: date) -> list[dict]:
    return [
        event
        for event in events
        if parse_event_date(event["start"]) <= target <= parse_event_date(event.get("end", event["start"]))
    ]


def build_calendar_days(events: list[dict], month_start: date, today: date) -> list[dict]:
    next_month = month_start.replace(day=28) + timedelta(days=4)
    month_end = next_month - timedelta(days=next_month.day)
    grid_start = month_start - timedelta(days=(month_start.weekday() + 1) % 7)
    grid_end = month_end + timedelta(days=(5 - month_end.weekday()) % 7)

    days = []
    cursor = grid_start
    while cursor <= grid_end:
        day_events = events_on_date(events, cursor)
        days.append(
            {
                "date": cursor.isoformat(),
                "day": cursor.day,
                "in_month": cursor.month == month_start.month,
                "is_today": cursor == today,
                "event_count": len(day_events),
                "has_high_impact": any(event.get("impact") == "높음" for event in day_events),
            }
        )
        cursor += timedelta(days=1)
    return days


def build_calendar_month(events: list[dict], month_start: date, today: date) -> dict:
    return {
        "month": month_start.isoformat()[:7],
        "month_label": f"{month_start.year}년 {month_start.month}월",
        "days": build_calendar_days(events, month_start, today),
    }


def build_schedule_section(generated_at: datetime) -> dict:
    local_today = generated_at.astimezone(KST).date()
    month_start = local_today.replace(day=1)
    week_start, week_end = current_week_window(generated_at)
    events = sorted((normalize_event(event) for event in ECONOMIC_EVENTS), key=lambda row: (row["start"], row["title"]))
    week_events = [event for event in events if event_overlaps(event, week_start, week_end)]
    earnings = sorted(
        (normalize_earnings_event(event) for event in EARNINGS_EVENTS),
        key=lambda row: (row["date"], row["region"], row["ticker"]),
    )
    week_earnings = [
        event
        for event in earnings
        if week_start <= parse_event_date(event["date"]) <= week_end
        and is_major_earnings_event(event)
    ]
    week_earnings_by_region = limit_week_earnings_by_region(week_earnings)
    event_months = sorted({event["start"][:7] for event in events} | {month_start.isoformat()[:7]})
    calendar_months = [
        build_calendar_month(events, date.fromisoformat(f"{month}-01"), local_today)
        for month in event_months
    ]

    return {
        "id": "schedule",
        "title": "주요 일정 정리",
        "summary": f"{format_korean_date(week_start)}~{format_korean_date(week_end)} 주요 매크로·정책 일정을 달력과 리스트로 정리했습니다.",
        "prices": [],
        "articles": [],
        "article_count": len(week_events),
        "calendar": {
            "month": month_start.isoformat()[:7],
            "month_label": f"{month_start.year}년 {month_start.month}월",
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "week_label": f"{format_korean_date(week_start)}~{format_korean_date(week_end)}",
            "days": build_calendar_days(events, month_start, local_today),
            "months": calendar_months,
        },
        "events": events,
        "week_events": week_events,
        "earnings": earnings,
        "week_earnings": {
            "domestic": week_earnings_by_region["domestic"],
            "us": week_earnings_by_region["us"],
            "note": "국내 주요 기업 실적발표 일정은 공식 IR 캘린더에서 확인되는 범위만 표시합니다.",
        },
        "month_events": [event for event in events if event["start"].startswith(month_start.isoformat()[:7])],
        "empty_message": "이번 주에 등록된 주요 일정이 없습니다.",
    }


def build_fear_greed_section(fear_greed_payload: dict) -> dict:
    items = fear_greed_payload.get("items", [])
    return {
        "id": "feargreed",
        "title": SECTION_LABELS["feargreed"],
        "summary": "미국 주식시장, 코스피, 암호화폐의 투자심리 지표를 한 화면에 모았습니다.",
        "prices": [],
        "articles": [],
        "article_count": len(items),
        "indicators": items,
        "empty_message": "공포탐욕지수 데이터가 아직 수집되지 않았습니다.",
    }


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


def article_url_key(item: dict) -> str:
    url = item.get("url", "")
    if not url:
        return ""
    return re.sub(r"([?&](utm_[^=&]+|oc|ved|usg)=[^&]+)", "", url).strip().lower()


def article_title_key(title: str) -> str:
    title = normalize_text(title or "")
    title = re.sub(r"\s+-\s+[^-]{2,80}$", "", title)
    title = re.sub(r"[^0-9a-z가-힣]+", " ", title.lower())
    return re.sub(r"\s+", " ", title).strip()


def article_tokens(title: str) -> set[str]:
    normalized = article_title_key(title)
    tokens = set(re.findall(r"[0-9a-z가-힣]{2,}", normalized))
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "after",
        "from",
        "over",
        "증시",
        "시장",
        "주식",
        "기자",
    }
    return tokens - stopwords


def is_similar_article(item: dict, previous: dict) -> bool:
    current_titles = [
        item.get("title_original", ""),
        item.get("title", ""),
    ]
    previous_titles = [
        previous.get("title_original", ""),
        previous.get("title", ""),
    ]
    for current_title in current_titles:
        current_tokens = article_tokens(current_title)
        if len(current_tokens) < 4:
            continue
        for previous_title in previous_titles:
            previous_tokens = article_tokens(previous_title)
            if len(previous_tokens) < 4:
                continue
            overlap = current_tokens & previous_tokens
            similarity = len(overlap) / max(len(current_tokens), len(previous_tokens))
            if similarity >= 0.72:
                return True
    return False


def dedupe_news(items: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for item in sorted(items, key=lambda row: row.get("published_at", ""), reverse=True):
        if not item.get("title"):
            continue
        candidate_keys = {
            article_url_key(item),
            article_title_key(item.get("title_original", "")),
            article_title_key(item.get("title", "")),
        }
        candidate_keys = {key for key in candidate_keys if key}
        if candidate_keys & seen:
            continue
        if any(is_similar_article(item, previous) for previous in deduped):
            continue
        seen.update(candidate_keys)
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
    unit = item.get("unit", "")
    value = f'{item["close"]:,.2f}'
    if unit == "%":
        value = f'{item["close"]:.2f}%'
    elif unit == "USD":
        value = f'${item["close"]:,.2f}'
    elif unit == "KRW":
        value = f'{item["close"]:,.2f}원'
    if change is None:
        return f'{item["name"]}: {value}'
    direction = "상승" if change > 0 else "하락" if change < 0 else "보합"
    return (
        f'{item["name"]}: {value} '
        f'(전일 대비 {abs(change):.2f}% {direction}, {item.get("as_of", "확인 전")} 기준)'
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


def stock_flow_reference(item: dict) -> dict:
    change = item.get("weekly_change_pct", 0)
    direction = "상승" if change > 0 else "하락" if change < 0 else "보합"
    text = (
        f'{item.get("name", "종목명 없음")} ({item.get("market", "시장 미상")}): '
        f'최근 5거래일 {abs(change):.2f}% {direction}, '
        f'거래량 {item.get("volume_ratio", 0):.2f}배, '
        f'평균 거래대금 {format_turnover(item.get("avg_turnover", 0))}'
    )
    return {
        "type": "stock_flow",
        "text": text,
        "url": item.get("source_url", ""),
        "name": item.get("name", "종목명 없음"),
        "market": item.get("market", "시장 미상"),
        "weekly_change_pct": round(change, 2),
        "direction": direction,
        "volume_ratio": item.get("volume_ratio", 0),
        "avg_turnover_label": format_turnover(item.get("avg_turnover", 0)),
        "as_of": item.get("as_of", ""),
    }


def format_turnover(value: float | int) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "확인 불가"
    if amount >= 1_000_000_000_000:
        return f"{amount / 1_000_000_000_000:.2f}조"
    if amount >= 100_000_000:
        return f"{amount / 100_000_000:.0f}억"
    return f"{amount:,.0f}"


def build_weekly_blocks(news: list[dict], stock_flow_payload: dict) -> list[dict]:
    stock_flows = stock_flow_payload.get("items", [])
    catalysts = filter_by_keywords(news, CATALYST_KEYWORDS, 5) or news[:5]
    risks = filter_by_keywords(news, RISK_KEYWORDS, 5)

    stock_flow_items = [stock_flow_reference(item) for item in stock_flows[:8]]
    if not stock_flow_items:
        stock_flow_items = ["해당 주 증권 데이터에서 수급 강도 후보 종목이 아직 수집되지 않았습니다."]

    catalyst_items = [linked_article_reference(item) for item in catalysts]
    if not catalyst_items:
        catalyst_items = ["해당 주 기사 데이터 안에서 뉴스·정책·수급 촉매로 분류할 재료가 부족합니다."]

    schedule_items = [linked_article_reference(item) for item in risks]
    if not schedule_items:
        schedule_items = [
            "수집 기사에서 다음 주 일정이 직접 확인되지 않았습니다. 금리, 환율, 유가, 원자재 지표 변화와 미국 주요 경제지표 발표 여부를 우선 점검하세요."
        ]

    return [
        {"title": "한 주간 수급 관심이 강했던 종목", "items": stock_flow_items},
        {"title": "주요 뉴스·정책·수급과 상승 촉매", "items": catalyst_items},
        {"title": "다음 주 주요 일정과 위험 요인", "items": schedule_items},
    ]


def build_weekly_section(news_items: list[dict], stock_flow_payload: dict, generated_at: datetime) -> dict:
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
        "weekly_blocks": build_weekly_blocks(weekly_news, stock_flow_payload),
        "empty_message": "해당 주간 구간에 포함되는 수집 기사가 아직 없습니다.",
    }


def summarize_section(topic: str, news: list[dict], prices: list[dict]) -> str:
    if news:
        lead = news[0]["title"]
        return f"{SECTION_LABELS[topic]} 핵심 기사: {lead}"
    if prices:
        return f"{SECTION_LABELS[topic]} 가격 데이터 {len(prices)}건이 수집되었습니다."
    return f"{SECTION_LABELS[topic]}에 배치된 기사가 없습니다."


def article_focus_groups(item: dict) -> set[str]:
    text = normalize_text(
        f'{item.get("title", "")} '
        f'{item.get("title_ko", "")} '
        f'{item.get("title_original", "")} '
        f'{item.get("description", "")}'
    )
    padded = f" {text.lower()} "
    groups = set()
    for group_name, keywords in FOCUS_GROUPS:
        if any(keyword.lower() in padded for keyword in keywords):
            groups.add(group_name)
    return groups


def focus_limit(topic: str, group: str) -> int:
    if topic == "domestic":
        return {
            "korea_rates": 3,
            "rates": 3,
            "nvidia": 2,
            "semiconductor": 3,
        }.get(group, 3)
    return 3


def diversify_articles(topic: str, news: list[dict], limit: int = 8) -> list[dict]:
    selected = []
    focus_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    for item in news:
        groups = article_focus_groups(item)
        source = item.get("source", "")
        if source and source_counts[source] >= 2:
            continue
        if groups and any(focus_counts[group] >= focus_limit(topic, group) for group in groups):
            continue
        selected.append(item)
        if source:
            source_counts[source] += 1
        for group in groups:
            focus_counts[group] += 1
        if len(selected) >= limit:
            return selected

    return selected


def is_relevant_section_article(topic: str, item: dict) -> bool:
    if topic != "us":
        return True
    text = normalize_text(
        f'{item.get("title", "")} '
        f'{item.get("title_ko", "")} '
        f'{item.get("title_original", "")} '
        f'{item.get("description", "")}'
    ).lower()
    market_terms = [
        "stock",
        "stocks",
        "equity",
        "equities",
        "market",
        "markets",
        "futures",
        "earnings",
        "shares",
        "s&p",
        "nasdaq",
        "증시",
        "주식",
        "선물",
        "실적",
        "나스닥",
        "다우존스",
        "엔비디아",
        "월스트리트",
    ]
    exclude_terms = [
        "not wall street",
        "월스트리트가 아닌",
        "chase mitchell dow",
        "north shore journal",
        "two harbors",
        "lake superior",
        "체이스 미첼 다우",
        "노스 쇼어 저널",
        "두 개의 항구",
        "슈피리어 호수",
        "cia",
        "nato",
        "crypto index",
        "암호화폐 지수",
    ]
    if any(term in text for term in exclude_terms):
        return False
    return any(term in text for term in market_terms)


def build_section(topic: str, prices: list[dict], news: list[dict]) -> dict:
    original_news_count = len(news)
    if topic == "us":
        news = [
            item
            for item in news
            if item.get("title_ko")
            and "미국 증시 헤드라인:" not in item.get("title_ko", "")
            and len(re.findall(r"[가-힣]", item.get("title_ko", ""))) >= 8
        ]
    news = [item for item in news if is_relevant_section_article(topic, item)]
    selected_news = diversify_articles(topic, news, 8)
    cards = [
        {
            "title": item.get("title_ko") or item["title"],
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "published_at": item.get("published_at", ""),
            "primary_topic": item.get("primary_topic", ""),
            "secondary_topics": item.get("secondary_topics", []),
        }
        for item in selected_news
    ]
    return {
        "id": topic,
        "title": SECTION_LABELS.get(topic, topic),
        "summary": summarize_section(topic, news, prices),
        "prices": [price_line(item) for item in prices],
        "articles": cards,
        "article_count": len(news) if topic != "us" else original_news_count,
        "empty_message": empty_section_message(topic, original_news_count) if not cards else "",
    }


def empty_section_message(topic: str, original_news_count: int = 0) -> str:
    if topic == "us" and original_news_count:
        return "한글 번역이 완료된 미국 증시 기사가 아직 없습니다. 다음 자동 갱신 때 다시 확인합니다."
    if topic == "us":
        return "아직 수집된 미국 증시 기사가 없습니다."
    if topic == "macro":
        return "아직 수집된 시장지표 관련 기사가 없습니다."
    if topic == "sector":
        return "아직 수집된 섹터/테마 기사가 없습니다."
    if topic == "domestic":
        return "아직 수집된 국내 증시 기사가 없습니다."
    return "아직 이 섹션에 표시할 기사가 없습니다."


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


def build_briefing(
    prices_payload: dict,
    news_payload: dict,
    fear_greed_payload: dict,
    stock_flow_payload: dict,
) -> dict:
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

    if len(us_news) < 8:
        us_news = us_news + [
            item
            for item in news_items
            if "us" in item.get("topic_hints", [])
            and item.get("primary_topic") == "us"
            and item not in us_news
        ]

    sections = {
        "domestic": build_section("domestic", price_groups.get("domestic", []), domestic_news),
        "us": build_section("us", price_groups.get("us", []), us_news),
        "macro": build_section("macro", price_groups.get("macro", []), macro_news),
        "sector": build_section("sector", [], sector_news),
        "weekly": build_weekly_section(news_items, stock_flow_payload, generated_dt),
        "schedule": build_schedule_section(generated_dt),
        "feargreed": build_fear_greed_section(fear_greed_payload),
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
        "schedule": sections["schedule"],
        "feargreed": sections["feargreed"],
        "uncategorized": sections["uncategorized"],
        "classification_summary": classification_summary(news_items),
        "collection_status": {
            "news_source": news_payload.get("source"),
            "price_source": prices_payload.get("source"),
            "fear_greed_source": fear_greed_payload.get("source"),
            "stock_flow_source": stock_flow_payload.get("source"),
            "news_query_counts": news_payload.get("query_counts", {}),
            "news_errors": news_payload.get("errors", []),
            "price_errors": prices_payload.get("errors", []),
            "fear_greed_errors": fear_greed_payload.get("errors", []),
            "stock_flow_errors": stock_flow_payload.get("errors", []),
        },
        "meta": {
            "mode": "dynamic-content-classified-us-market",
            "disclaimer": "기사는 공개 RSS를 통해 동적으로 수집한 결과입니다. 분류는 제목/설명 키워드 점수 기반입니다.",
        },
    }


def main() -> None:
    prices = load_json(RAW_DIR / "prices_dynamic.json", {"source": "not-collected", "items": [], "errors": []})
    news = load_json(RAW_DIR / "news_dynamic.json", {"source": "not-collected", "items": [], "errors": []})
    fear_greed = load_json(RAW_DIR / "fear_greed_dynamic.json", {"source": "not-collected", "items": [], "errors": []})
    stock_flows = load_json(RAW_DIR / "stock_flows_dynamic.json", {"source": "not-collected", "items": [], "errors": []})
    briefing = build_briefing(prices, news, fear_greed, stock_flows)

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
