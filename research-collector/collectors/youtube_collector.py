"""
유튜브 쇼츠 리서치 수집기
- 키워드 기반 인기 영상 검색 → 제목/후킹문구/조회수 수집
- 경쟁 채널의 최근 업로드 성과 추적

필요한 것: YouTube Data API v3 키 (Google Cloud Console에서 무료 발급, 일일 쿼터 있음)
"""
from googleapiclient.discovery import build


def _parse_duration_seconds(duration_iso: str) -> int:
    """ISO 8601 duration (PT1M3S 등)을 초로 변환. 외부 라이브러리 없이 직접 파싱."""
    import re
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_iso)
    if not match:
        return 0
    h, m, s = (int(x) if x else 0 for x in match.groups())
    return h * 3600 + m * 60 + s


def search_trending_by_keyword(api_key: str, keyword: str, region_code: str, max_results: int) -> list:
    """키워드로 검색 후, 60초 이하(쇼츠 추정) 영상만 걸러서 반환."""
    youtube = build("youtube", "v3", developerKey=api_key)

    search_resp = youtube.search().list(
        q=keyword,
        part="id",
        type="video",
        order="viewCount",
        regionCode=region_code,
        videoDuration="short",  # 4분 미만 (쇼츠 포함 상위 필터)
        maxResults=max_results,
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
    if not video_ids:
        return []

    stats_resp = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids),
    ).execute()

    results = []
    for item in stats_resp.get("items", []):
        duration_sec = _parse_duration_seconds(item["contentDetails"]["duration"])
        if duration_sec > 60:  # 진짜 쇼츠만 남김
            continue
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        results.append({
            "id": f"yt_{item['id']}",
            "platform": "youtube_shorts",
            "keyword": keyword,
            "title": snippet.get("title"),
            "hook_text": snippet.get("title", "")[:40],  # 제목 앞부분 = 썸네일/후킹 문구 근사치
            "channel_title": snippet.get("channelTitle"),
            "published_at": snippet.get("publishedAt"),
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
            "duration_sec": duration_sec,
            "url": f"https://www.youtube.com/watch?v={item['id']}",
        })

    results.sort(key=lambda x: x["view_count"], reverse=True)
    return results


def track_competitor_channels(api_key: str, channel_ids: list, max_per_channel: int = 10) -> list:
    """경쟁 채널의 최근 업로드 성과를 수집 (조회수 추이 파악용)."""
    youtube = build("youtube", "v3", developerKey=api_key)
    all_results = []

    for channel_id in channel_ids:
        ch_resp = youtube.channels().list(part="contentDetails,snippet", id=channel_id).execute()
        items = ch_resp.get("items", [])
        if not items:
            continue

        channel_name = items[0]["snippet"]["title"]
        uploads_playlist = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        pl_resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist,
            maxResults=max_per_channel,
        ).execute()
        video_ids = [i["contentDetails"]["videoId"] for i in pl_resp.get("items", [])]
        if not video_ids:
            continue

        stats_resp = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids),
        ).execute()

        for item in stats_resp.get("items", []):
            duration_sec = _parse_duration_seconds(item["contentDetails"]["duration"])
            stats = item.get("statistics", {})
            all_results.append({
                "id": f"competitor_{item['id']}",
                "platform": "youtube_shorts",
                "channel_id": channel_id,
                "channel_title": channel_name,
                "title": item["snippet"].get("title"),
                "hook_text": item["snippet"].get("title", "")[:40],
                "published_at": item["snippet"].get("publishedAt"),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "duration_sec": duration_sec,
                "url": f"https://www.youtube.com/watch?v={item['id']}",
            })

    return all_results
