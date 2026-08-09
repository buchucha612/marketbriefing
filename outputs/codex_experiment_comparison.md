# Codex 자율 작업 실험 비교 리포트

## 실험 개요

거의 동일한 프롬프트로 각자 Codex를 사용해 “매일 국내/미국 증시 시황을 보여주는 웹페이지”를 만들었다.  
하지만 최종 결과물은 꽤 달라졌다. 핵심 차이는 프롬프트 자체보다, 각 에이전트가 작업 중에 어떤 기준을 고정하고 어떤 방향으로 요구사항을 해석했는지에서 발생했다.

비교 대상:

- 내 프로젝트: 현재 작업 폴더의 `collectors / processing / serving / outputs` 구조
- 친구 프로젝트: `news-dashboard.zip`
- 친구 대화 요약: `EXPERIMENT_CONVERSATION_SUMMARY.md`

## 최종 결과물이 달라진 이유

| 차이 지점 | 친구 프로젝트 | 내 프로젝트 | 최종 결과 차이 |
|---|---|---|---|
| 작업 기준 | `python scripts/generate_report.py` 하나를 계속 통과시키는 “runnable invariant” 중심 | 대화 중 요구사항을 계속 반영하며 `collectors -> processing -> serving` 구조로 확장 | 친구 쪽은 안정적인 생성 파이프라인, 내 쪽은 더 제품형 UI/데이터 구조 |
| 데이터 범위 | `domestic / overseas` 2분류 | `domestic / us / macro / sector` 내용 기반 분류 | 내 쪽이 더 세분화됐고, 해외가 아니라 미국 증시로 범위가 좁혀짐 |
| 데이터 소스 | 명시적 RSS 설정 파일: 연합뉴스, Investing.com | Google News RSS 검색 + 미국 영어 RSS + 헤드라인 번역 + Yahoo chart 시도 | 친구 쪽은 소스가 명료하고 재현 쉬움, 내 쪽은 더 동적이지만 외부 의존성이 큼 |
| UI 방향 | 단순 정적 헤드라인 카드 | `The Daily Markets Brief` 느낌의 리포트형 탭 UI | 내 쪽이 서비스 화면에 더 가까움 |
| 문서 운영 | `PROJECT_PLAN.md`, `TASKS.md`, `DECISIONS.md`, `IMPLEMENTATION_LOG.md` 유지 | `PROJECT_PLAN.md`, `README.md` 중심, 대화 기반 변경이 많음 | 친구 쪽은 작업 추적성이 좋음 |
| 요구사항 변화 반영 | “LLM 요약 불필요, 헤드라인만”을 강하게 고정 | 시황/분류/번역/UI를 계속 바꿔가며 반영 | 친구 쪽은 범위 안정, 내 쪽은 사용자 취향 반영이 큼 |
| 실패 대응 | RSS 실패는 warning, fallback으로 항상 HTML 생성 | 가격 API 실패 시 fake price 금지, 오류 기록 | 둘 다 방어적이지만 친구 쪽이 더 단순하고 테스트 쉬움 |
| 인코딩 대응 | Windows 한글 깨짐을 의식해 유니코드 이스케이프 활용 | 여러 차례 한국어 UI/코드 편집을 직접 수행 | 친구 쪽이 Windows 유지보수 관점에서 더 조심스러움 |

## 구조 비교

| 항목 | 친구 프로젝트 | 내 프로젝트 |
|---|---|---|
| 실행 단위 | 단일 스크립트 `scripts/generate_report.py` | 수집기 2개 + 빌더 1개 |
| 주요 흐름 | RSS/config -> report JSON -> static HTML | RSS/chart 수집 -> raw JSON -> 분류 JSON -> static HTML |
| 출력 위치 | `data/reports/YYYY-MM-DD.json`, `public/index.html` | `storage/daily/daily_market_briefing.json`, `outputs/market-briefing-mvp/index.html` |
| 설정 방식 | `config/sources.json` 중심 | 현재는 코드 내 query config 중심 |
| UI 성격 | 헤드라인 리스트 | 브리핑 리더 |
| 분류 방식 | 소스 설정의 `market` 값 | 기사 내용 키워드 점수 + topic hint |
| 미국 뉴스 처리 | Investing.com 해외 RSS | 미국 영어 RSS 참고, 헤드라인만 한국어 번역 |

## 내가 배우면 좋은 점

| 배울 점 | 왜 좋은가 | 내 프로젝트에 적용하면 |
|---|---|---|
| 항상 실행되는 단일 명령을 정하기 | 에이전트가 길게 작업해도 기준점이 안 흔들림 | `python collectors/news.py && python collectors/prices.py && python processing/build_briefing.py` 같은 표준 실행 명령을 README 상단에 고정 |
| `TASKS.md`, `DECISIONS.md`, `IMPLEMENTATION_LOG.md` 유지 | 왜 이런 구조가 됐는지 나중에 추적 가능 | 다음 에이전트에게 맡겨도 맥락 손실이 줄어듦 |
| 외부 데이터 실패를 non-fatal로 처리 | RSS/API는 자주 실패하므로 페이지 생성 자체는 살아 있어야 함 | 현재 방식 유지: 실패 시 가짜 데이터 넣지 말고 상태만 기록 |
| 설정 파일로 소스 분리 | 코드 수정 없이 뉴스 소스를 교체 가능 | Google News 쿼리도 `config/queries.json` 또는 `config/sources.json`으로 빼기 |
| 단계별로 “얇은 수직 슬라이스” 구현 | 기능 하나가 끝날 때마다 실행 가능한 결과물이 생김 | 수집 -> 분류 -> UI를 한꺼번에 크게 바꾸지 말고 작은 기능 단위로 검증 |
| 검증 명령을 문서에 남기기 | 나중에 다시 열었을 때 신뢰 가능한 상태인지 빠르게 확인 가능 | `py_compile`, JSON 생성, output 갱신 명령을 RUNBOOK에 기록 |

## 친구 workflow에서 그대로 배우지 않는 게 좋은 점

| 조심할 점 | 이유 | 더 나은 방식 |
|---|---|---|
| UI를 너무 늦게 다루는 것 | 기능은 안정적인데 최종물이 “도구”처럼 보일 수 있음 | MVP라도 초반부터 실제 사용 화면을 같이 다듬기 |
| `domestic / overseas` 같은 큰 분류를 오래 유지 | 사용자가 나중에 “미국 증시만”처럼 좁히면 구조 변경이 커짐 | 처음부터 `market_scope`를 명확히: 국내, 미국, 금리·환율·유가 |
| fallback headline을 오래 남기는 것 | 사용자는 실제 데이터인지 샘플인지 헷갈릴 수 있음 | fake data는 화면에 표시하지 않고 “데이터 없음” 상태로 처리 |
| 문서가 너무 많아지는 것 | 작은 MVP에서는 문서 관리 자체가 일이 될 수 있음 | `PROJECT_PLAN.md`, `DECISIONS.md`, `RUNBOOK.md` 정도만 유지 |
| 안정성만 보고 제품 감각을 미루는 것 | 자율 에이전트는 “작동함”을 “좋음”으로 착각할 때가 있음 | 레퍼런스와 사용자 취향을 중간중간 명시적으로 반영 |

## 자율 코딩 에이전트를 더 잘 쓰기 위한 실전 프롬프트 패턴

### 1. 작업 기준 고정

```text
이 프로젝트의 runnable invariant는 아래 명령이다.

python collectors/news.py
python collectors/prices.py
python processing/build_briefing.py

모든 변경 후 이 명령들이 통과해야 한다.
```

### 2. 의사결정 기록 요구

```text
중요한 구현 결정을 할 때마다 DECISIONS.md에 기록해라.
기록에는 선택한 방식, 버린 방식, 이유를 포함해라.
```

### 3. 과설계 방지

```text
MVP 범위 밖의 기능은 구현하지 말고 PROJECT_PLAN.md의 Out of Scope에 적어라.
필요하면 나중에 확장 포인트로만 남겨라.
```

### 4. 실제 데이터와 샘플 데이터 구분

```text
화면에 fake/sample 데이터를 표시하지 마라.
외부 데이터 수집이 실패하면 가짜 값을 넣지 말고 데이터 없음 또는 오류 상태를 보여줘라.
```

### 5. UI 취향 반영

```text
기능 구현만 하지 말고, 현재 코드베이스의 데이터 구조에 맞는 UI 레퍼런스를 보고 화면 구조를 제안해라.
단, 구현 전에 왜 그 레이아웃이 현재 데이터 구조에 맞는지 설명해라.
```

## 결론

친구 프로젝트는 **운영 안정성과 작업 추적성**이 강하다.  
내 프로젝트는 **요구사항 변화 반영, 제품형 UI, 데이터 분류 방향성**이 강하다.

앞으로 자율 코딩 에이전트를 더 잘 쓰려면 두 방식을 섞는 것이 좋다.

| 가져올 것 | 버릴 것 |
|---|---|
| 친구 쪽의 runnable invariant | 너무 늦은 UI 고민 |
| 친구 쪽의 결정 기록 습관 | 오래 유지되는 fallback/sample 데이터 |
| 친구 쪽의 config 기반 소스 관리 | 지나치게 단순한 국내/해외 이분법 |
| 내 쪽의 빠른 취향 반영 | 대화만 믿고 문서 기록을 생략하는 방식 |
| 내 쪽의 제품형 UI 실험 | 코드 안에 쿼리/소스가 너무 많이 박히는 방식 |

요약하면, **친구 쪽의 작업 운영 방식 + 내 쪽의 제품 감각 반영 방식**을 합치는 것이 가장 좋은 다음 실험 방향이다.
