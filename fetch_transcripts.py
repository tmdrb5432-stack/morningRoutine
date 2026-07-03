"""
videos.json에서 각 영상의 자막(트랜스크립트)을 가져옵니다.
자막이 없는 영상은 title + description으로 대체합니다.
"""
import json
import os
import time
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from tqdm import tqdm

INPUT_FILE = "data/videos.json"
OUTPUT_FILE = "data/transcripts.json"
PREFERRED_LANGS = ["ko", "en"]


def get_transcript(video_id: str) -> tuple[str, str]:
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            t = transcript_list.find_transcript(PREFERRED_LANGS)
        except Exception:
            t = transcript_list.find_generated_transcript(PREFERRED_LANGS)
        entries = t.fetch()
        text = " ".join(e.text for e in entries)
        return text, "transcript"
    except (NoTranscriptFound, TranscriptsDisabled):
        return "", "none"
    except Exception:
        return "", "none"


def main():
    os.makedirs("data", exist_ok=True)

    with open(INPUT_FILE, encoding="utf-8") as f:
        videos = json.load(f)

    results = []
    print(f"[fetch_transcripts] {len(videos)}개 영상 자막 수집 중...")

    for video in tqdm(videos):
        transcript, source = get_transcript(video["video_id"])
        results.append({
            **video,
            "transcript": transcript,
            "transcript_source": source,
        })
        time.sleep(0.5)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    has_transcript = sum(1 for r in results if r["transcript_source"] == "transcript")
    print(f"[fetch_transcripts] 완료. 자막 있음: {has_transcript}/{len(results)} -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
