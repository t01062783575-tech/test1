"""
리서치 수집기 실행 진입점

사용법:
    python main.py

config.yaml의 niche.keywords 와 youtube.competitor_channel_ids 를 먼저 채운 뒤 실행하세요.
결과는 data/meta.json에 누적 저장됩니다 (중복 제거됨).
"""
import os
import sys

import yaml

from collectors import youtube_collector, tiktok_collector
from utils import storage


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run():
    config = load_config()
    storage.ensure_dirs(config)

    all_new_entries = []

    # ---- 유튜브 쇼츠 수집 ----
    yt_key = config["youtube"]["api_key"]
    if not yt_key or yt_key == "YOUR_YOUTUBE_DATA_API_KEY":
        print("[경고] youtube.api_key가 설정되지 않아 유튜브 수집을 건너뜁니다.")
    else:
        for keyword in config["niche"]["keywords"]:
            print(f"[유튜브] '{keyword}' 검색 중...")
            entries = youtube_collector.search_trending_by_keyword(
                api_key=yt_key,
                keyword=keyword,
                region_code=config["youtube"]["region_code"],
                max_results=config["youtube"]["max_results_per_keyword"],
            )
            print(f"  -> {len(entries)}개 쇼츠 발견")
            all_new_entries.extend(entries)
            storage.save_raw_snapshot(config["output"]["assets_dir"], "youtube_search", entries)

        competitor_ids = config["youtube"].get("competitor_channel_ids", [])
        if competitor_ids and competitor_ids[0].startswith("UCxxxx") is False:
            print(f"[유튜브] 경쟁 채널 {len(competitor_ids)}개 추적 중...")
            comp_entries = youtube_collector.track_competitor_channels(yt_key, competitor_ids)
            print(f"  -> {len(comp_entries)}개 영상 수집")
            all_new_entries.extend(comp_entries)
            storage.save_raw_snapshot(config["output"]["assets_dir"], "youtube_competitors", comp_entries)

    # ---- 틱톡 수집 ----
    if config["tiktok"]["enabled"]:
        provider = config["tiktok"]["provider"]
        if provider == "manual":
            csv_path = os.path.join(config["output"]["base_dir"], "tiktok_manual_input.csv")
            tiktok_collector.ensure_manual_csv_template(csv_path)
            tt_entries = tiktok_collector.load_manual_entries(csv_path)
            print(f"[틱톡-수동] {len(tt_entries)}개 항목 로드 (CSV: {csv_path})")
            all_new_entries.extend(tt_entries)
        else:
            try:
                tt_entries = tiktok_collector.fetch_via_api(
                    config["tiktok"]["api_key"], config["niche"]["keywords"]
                )
                all_new_entries.extend(tt_entries)
            except NotImplementedError as e:
                print(f"[틱톡] {e}")
    else:
        print("[틱톡] config.yaml에서 tiktok.enabled: true로 바꾸면 수집됩니다.")

    # ---- meta.json에 누적 저장 ----
    added = storage.append_entries(config["output"]["meta_file"], all_new_entries)
    print(f"\n완료: 신규 {added}개 항목을 {config['output']['meta_file']}에 저장했습니다.")
    print(f"총 수집: {len(all_new_entries)}개 (중복 제외 후 {added}개 신규)")


if __name__ == "__main__":
    try:
        run()
    except FileNotFoundError:
        print("config.yaml을 찾을 수 없습니다. research-collector 폴더 안에서 실행하세요.")
        sys.exit(1)
