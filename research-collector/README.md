# 숏폼 리서치 수집기

유튜브 쇼츠 + 틱톡 트렌드/후킹 문구/경쟁 채널 성과를 자동 수집해서
`data/meta.json` 하나로 누적 관리합니다. 이 파일을 트랙 B(자동화)에서
스크립트 초안 생성의 입력값으로 그대로 재사용합니다.

## 1. 설치

```bash
cd research-collector
pip install -r requirements.txt
```

## 2. 유튜브 API 키 발급 (5분)

1. https://console.cloud.google.com 접속 → 새 프로젝트 생성
2. "API 및 서비스" → "라이브러리" → "YouTube Data API v3" 검색 → 사용 설정
3. "사용자 인증 정보" → API 키 발급
4. `config.yaml`의 `youtube.api_key`에 붙여넣기

**쿼터 주의**: 하루 10,000 유닛 무료 제공. `search.list` 1회 = 100유닛 소모라
키워드 5개 정도면 하루 몇 번 안 돌립니다. 처음엔 키워드 3~5개로 시작하세요.

**보안 주의**: `config.yaml`에 API 키를 직접 넣으면 실수로 git에 커밋되기 쉽습니다.
저장소를 공개하거나 공유할 계획이라면 키를 환경 변수로 분리하는 것을 권장합니다.

## 3. 니치 설정

`config.yaml`을 열어서:
- `niche.keywords`: 검색할 키워드 3~5개
- `youtube.competitor_channel_ids`: 벤치마킹할 경쟁 채널 ID (선택)
  - 채널 ID 찾는 법: 채널 페이지 → 정보 → 공유 → 채널 ID 복사

## 4. 실행

```bash
python main.py
```

`data/meta.json`에 결과가 누적됩니다. 여러 번 실행해도 중복 저장되지 않습니다.
`data/assets/`에는 실행할 때마다 원본 스냅샷이 타임스탬프로 쌓여서
나중에 "이 키워드가 시간이 지나며 어떻게 변했는지" 추적할 수 있습니다.

## 5. 틱톡 데이터 수집 옵션

틱톡은 유튜브처럼 개인이 바로 쓸 수 있는 공식 검색 API가 없습니다. 세 가지 선택지:

| 방법 | 비용 | 난이도 | 비고 |
|---|---|---|---|
| **수동 입력 (기본)** | 무료 | 낮음 | 틱톡 크리에이티브 센터(ads.tiktok.com/business/creativecenter)에서 눈으로 트렌드 보고 CSV에 기록 |
| **Apify / RapidAPI 등 유료 API** | 월 몇만원대 | 중간 | `tiktok_collector.py`의 `fetch_via_api()`에 연동 코드 추가 필요 |
| **틱톡 공식 Research API** | 무료 | 승인 어려움 | 학술/연구 목적 승인제라 개인 사업자는 사실상 어려움 |

처음엔 **수동 모드**로 시작하는 걸 권장합니다. `python main.py` 실행하면
`data/tiktok_manual_input.csv` 템플릿이 자동 생성되니, 크리에이티브 센터에서
본 인기 영상을 여기에 채워 넣고 다시 실행하면 meta.json에 합쳐집니다.

나중에 물량이 늘어나서 자동화가 필요해지면 `config.yaml`의
`tiktok.provider`를 `apify` 또는 `rapidapi`로 바꾸고, 선택한 서비스의
API 키를 발급받아 `fetch_via_api()` 함수 안을 채우면 됩니다.

## 6. 폴더 구조

```
data/
  meta.json              # 마스터 인덱스 — 모든 수집 결과 (트랙B가 여기서 읽음)
  assets/
    youtube_search/       # 키워드 검색 스냅샷 (타임스탬프별)
    youtube_competitors/  # 경쟁 채널 스냅샷
  scripts/                # (비어있음, 다음 단계에서 스크립트 초안 생성기가 채움)
  tiktok_manual_input.csv # 틱톡 수동 입력용
```

## 다음 단계

`meta.json`이 어느 정도 쌓이면, 이 데이터를 읽어서
"조회수 상위 후킹 문구 패턴 → 새 스크립트 초안" 생성기를 붙일 차례입니다.
이건 클로드 코드로 다음에 이어서 만들면 됩니다.

## 7. 벤치마킹 & 분석 일지 템플릿 (templates/)

`templates/benchmark_100.csv` — 떡상 영상 100개를 뜯어보는 정성 분석용.
`meta.json`에서 조회수 상위 항목을 여기로 옮겨와 "왜 떡상했는가" 가설을 직접
써보는 게 핵심입니다. 데이터만 모으고 분석을 안 하면 의미가 없습니다.

`templates/analysis_log.csv` — 본인이 업로드한 영상의 24시간/7일 성과를
기록하는 일지. 특히 "이탈구간" 컬럼이 훅과 구조의 문제를 알려주는
가장 중요한 데이터입니다.

두 템플릿 다 엑셀/구글시트로 열어서 쓰시면 됩니다. 매일 이걸 채우는 습관이
편집 실력보다 훨씬 크게 성과를 좌우합니다.
