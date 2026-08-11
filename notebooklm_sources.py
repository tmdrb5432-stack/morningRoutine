"""
새로 올라온 영상의 YouTube 링크를 NotebookLM 소스로 추가하기 좋은 형태로 뽑아냅니다.
NotebookLM(notebook.google.com)은 공개 API가 없어 자동 업로드는 불가능하므로,
이 스크립트는 링크만 한 줄씩 생성합니다(NotebookLM의 '소스 추가 > YouTube'는
URL만 받으므로 날짜/제목 같은 부가 텍스트는 넣지 않습니다). notebook.google.com
에서 링크를 하나씩 붙여넣으면 자막을 자동으로 읽어들입니다.

이전 실행에서 이미 뽑아낸 영상은 다시 출력하지 않습니다 (data/notebooklm_seen.json 로 추적).
"""
import json
import os

VIDEOS_FILE = "data/videos.json"
SEEN_FILE = "data/notebooklm_seen.json"
OUTPUT_FILE = "data/notebooklm_new_links.txt"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(VIDEOS_FILE):
        print(f"[notebooklm_sources] {VIDEOS_FILE} 이 없습니다. 먼저 fetch_videos.py 를 실행하세요.")
        return

    videos = load_json(VIDEOS_FILE, [])
    seen_ids = set(load_json(SEEN_FILE, []))

    new_videos = [v for v in videos if v["video_id"] not in seen_ids]
    new_videos.sort(key=lambda v: v["published_at"])

    if not new_videos:
        print("[notebooklm_sources] 새로 추가할 영상이 없습니다.")
        open(OUTPUT_FILE, "w", encoding="utf-8").close()
        return

    urls = [f"https://www.youtube.com/watch?v={v['video_id']}" for v in new_videos]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(urls) + "\n")

    seen_ids.update(v["video_id"] for v in new_videos)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen_ids), f, ensure_ascii=False, indent=2)

    print(f"[notebooklm_sources] 새 영상 {len(new_videos)}개 -> {OUTPUT_FILE}")
    print("  notebook.google.com 에서 '소스 추가 > YouTube' 로 위 링크를 하나씩 붙여넣으세요.")


if __name__ == "__main__":
    main()
