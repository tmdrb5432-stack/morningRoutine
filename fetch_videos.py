"""
YouTube 채널에서 지난 N일간의 영상 목록을 가져옵니다.
"""
import os
import json
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")
DAYS_TO_FETCH = int(os.getenv("DAYS_TO_FETCH", "365"))
OUTPUT_FILE = "data/videos.json"


def resolve_channel_id(youtube, channel_id_or_handle: str) -> str:
    handle = channel_id_or_handle.lstrip("@")
    if channel_id_or_handle.startswith("UC"):
        return channel_id_or_handle
    res = youtube.channels().list(part="id", forHandle=handle).execute()
    items = res.get("items", [])
    if not items:
        raise ValueError(f"채널을 찾을 수 없습니다: {channel_id_or_handle}")
    return items[0]["id"]


def get_channel_uploads_playlist(youtube, channel_id: str) -> str:
    res = youtube.channels().list(part="contentDetails", id=channel_id).execute()
    return res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def fetch_videos_from_playlist(youtube, playlist_id: str, since: datetime) -> list[dict]:
    videos = []
    next_page = None

    while True:
        res = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page,
        ).execute()

        for item in res["items"]:
            snippet = item["snippet"]
            published_at = datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            )
            if published_at < since:
                return videos
            videos.append({
                "video_id": snippet["resourceId"]["videoId"],
                "title": snippet["title"],
                "published_at": snippet["publishedAt"],
                "description": snippet["description"][:500],
            })

        next_page = res.get("nextPageToken")
        if not next_page:
            break

    return videos


def main():
    os.makedirs("data", exist_ok=True)
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    since = datetime.now(timezone.utc) - timedelta(days=DAYS_TO_FETCH)

    channel_id = resolve_channel_id(youtube, CHANNEL_ID)
    print(f"[fetch_videos] 채널 {CHANNEL_ID} ({channel_id}) 에서 {DAYS_TO_FETCH}일치 영상 수집 중...")

    playlist_id = get_channel_uploads_playlist(youtube, channel_id)
    videos = fetch_videos_from_playlist(youtube, playlist_id, since)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    print(f"[fetch_videos] {len(videos)}개 영상 저장 -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
