"""
data/ 폴더 관리 유틸리티
- 출력 디렉토리 생성
- 실행 시점 원본 스냅샷 저장 (타임스탬프별)
- meta.json에 중복 없이 누적 저장
"""
import json
import os
from datetime import datetime, timezone


def ensure_dirs(config: dict):
    """output 설정에 정의된 디렉토리를 모두 생성."""
    output = config["output"]
    os.makedirs(output["base_dir"], exist_ok=True)
    os.makedirs(output["scripts_dir"], exist_ok=True)
    os.makedirs(output["assets_dir"], exist_ok=True)
    os.makedirs(os.path.dirname(output["meta_file"]), exist_ok=True)


def save_raw_snapshot(assets_dir: str, subfolder: str, entries: list):
    """실행할 때마다 원본 결과를 타임스탬프 파일로 남겨서 시계열 추적이 가능하게 함."""
    if not entries:
        return
    target_dir = os.path.join(assets_dir, subfolder)
    os.makedirs(target_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(target_dir, f"{timestamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def _load_meta(meta_file: str) -> list:
    if not os.path.exists(meta_file):
        return []
    with open(meta_file, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return []
        return json.loads(content)


def append_entries(meta_file: str, entries: list) -> int:
    """meta.json에 항목을 id 기준으로 중복 없이 누적 저장. 새로 추가된 개수를 반환."""
    existing = _load_meta(meta_file)
    existing_ids = {item.get("id") for item in existing}

    added = 0
    now = datetime.now(timezone.utc).isoformat()
    for entry in entries:
        if entry.get("id") in existing_ids:
            continue
        entry = dict(entry)
        entry["collected_at"] = now
        existing.append(entry)
        existing_ids.add(entry.get("id"))
        added += 1

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    return added
