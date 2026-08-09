# 데일리 증시 시황 MVP 계획

## 목표

국내/미국 증시 시황 웹페이지를 만들기 위한 최소 동작 구조를 만든다.

중요 원칙은 고정 샘플 문구를 사이트 데이터로 사용하지 않는 것이다. 화면에 보이는 기사, 출처, 시각, 가격 라인은 실행 시점에 수집된 데이터에서만 만든다.

두 번째 버전부터는 수집 쿼리 이름으로 국내/미국/금리·환율·유가를 나누지 않는다. 기사 제목과 설명의 키워드 점수를 계산해 `primary_topic`과 `secondary_topics`를 부여한다.

미국 증시 섹션은 미국권 영어 뉴스 RSS를 참고하고, 화면에는 헤드라인만 한국어로 번역해 표시한다.

## 범위

- 공개 RSS에서 실제 시황 기사 메타데이터 수집
- 공개 차트 API에서 시세 데이터 수집 시도
- 수집 결과를 raw JSON으로 보존
- raw JSON에서 내용 기반 주제 분류 후 일일 브리핑 JSON 생성
- 웹페이지는 브리핑 JSON만 읽어서 렌더링
- 가격 API 실패 시 가짜 숫자 대신 오류 상태 보존

## 제외 범위

- 유료 벤더 데이터 계약
- 기사 전문 저장/재배포
- 실시간 스트리밍
- 사용자 계정/알림
- 매매 신호 생성

## 구조

```text
collectors/
  news.py            # Google News RSS 동적 수집, matched_queries만 보존
  prices.py          # 공개 chart API 동적 수집 시도

storage/
  raw/               # 수집 원본 JSON
  daily/             # 브리핑 JSON

processing/
  build_briefing.py  # 기사 내용 기반 primary/secondary topic 분류

serving/
  index.html
  styles.css
  app.js
  daily_market_briefing.json
  briefing-data.js
```

## 완료 상태

- [x] 동적 뉴스 수집기 구현
- [x] 동적 가격 수집기 구현
- [x] 샘플/가짜 기사 문구 제거
- [x] 브리핑 생성기를 동적 raw JSON 기반으로 변경
- [x] 웹페이지를 실제 기사 카드 중심으로 변경
- [x] 직접 파일 열기용 `briefing-data.js` 생성
- [x] `outputs/market-briefing-mvp` 산출물 갱신
- [x] 검색 쿼리 기반 분류에서 기사 내용 기반 분류로 변경
- [x] 각 기사 카드에 분류 이유와 보조 주제 표시

## 검증

- `collectors/news.py` 실행 성공
- `collectors/prices.py` 실행 성공
- `processing/build_briefing.py` 실행 성공
- Python JSON 파싱 기준 브리핑 파일 정상
- Python compile 검증 통과
- 생성 모드: `dynamic-content-classified`
- 생성 결과: 국내 6개, 해외 6개, 매크로 6개, 섹터 6개, 미분류 1개 표시
