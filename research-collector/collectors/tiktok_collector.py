"""
틱톡 리서치 수집기

⚠️ 틱톡은 유튜브와 달리 '검색/트렌드'를 조회하는 공식 공개 API가 없습니다.
    (틱톡 공식 Research API는 학술기관 승인제라 개인 사업 용도로는 발급이 어렵습니다.)

이 파일은 3가지 모드를 지원합니다. config.yaml의 tiktok.provider 값으로 전환하세요.

1) manual  (기본값, 바로 사용 가능)
   - 틱톡 크리에이티브 센터(ads.tiktok.com/business/creativecenter) 트렌드 페이지에서
     인기 해시태그/사운드를 눈으로 보고 data/tiktok_manual_input.csv 에 직접 기록
   - 이 스크립트가 그 CSV를 읽어서 meta.json 형식으로 변환

2) apify / rapidapi
   - 틱톡 데이터를 합법적으로 제공하는 유료 API 마켓플레이스를 쓰는 경우
   - 계정 만들고 API 키를 config.yaml에 넣으면 fetch_via_api() 함수 안에서 호출
   - 사용할 프로바이더가 정해지면 해당 프로바이더 문서를 보고 fetch_via_api 내부만 채우면 됨
     (이 함수는 지금은 뼈대만 있고, 실제 엔드포인트 호출부는 프로바이더 선택 후 채워야 합니다)
"""
import csv
import os


MANUAL_CSV_HEADERS = ["title", "hook_text", "author", "view_count", "like_count", "url"]


def ensure_manual_csv_template(path: str):
    """수동 입력용 CSV 템플릿이 없으면 생성."""
    if os.path.exists(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(MANUAL_CSV_HEADERS)
        writer.writerow([
            "예시: 3초만에 이렇게 하세요",
            "3초만에 이렇게",
            "예시채널",
            "1200000",
            "45000",
            "https://www.tiktok.com/@example/video/123456789",
        ])


def load_manual_entries(csv_path: str) -> list:
    """수동으로 기록한 CSV를 meta.json 엔트리 형식으로 변환."""
    if not os.path.exists(csv_path):
        return []

    results = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if not row.get("title") or row["title"].startswith("예시"):
                continue
            results.append({
                "id": f"tt_manual_{i}_{hash(row.get('url', ''))}",
                "platform": "tiktok",
                "title": row.get("title"),
                "hook_text": row.get("hook_text") or row.get("title", "")[:40],
                "channel_title": row.get("author"),
                "view_count": int(row.get("view_count") or 0),
                "like_count": int(row.get("like_count") or 0),
                "url": row.get("url"),
            })
    return results


def fetch_via_api(api_key: str, keywords: list) -> list:
    """
    유료 API 프로바이더(Apify, RapidAPI 등)를 쓰기로 정하면 여기를 채우세요.
    프로바이더마다 요청 형식이 달라서 지금은 뼈대만 제공합니다.
    """
    raise NotImplementedError(
        "config.yaml의 tiktok.provider를 'apify' 또는 'rapidapi'로 바꿨다면, "
        "선택한 프로바이더의 API 문서를 참고해서 이 함수 내부에 실제 요청 코드를 채워야 합니다."
    )
