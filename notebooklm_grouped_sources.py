"""
transcripts.json 의 영상들을 월 단위로 묶어서 NotebookLM에 파일로 업로드하기 좋은
텍스트 소스를 만듭니다.

NotebookLM 무료 요금제는 노트북당 소스 개수가 제한되어 있어(2026년 기준 50개),
매일 올라오는 영상을 하나하나 소스로 넣으면 1년치(약 300개)를 감당할 수 없습니다.
대신 월별로 영상들을 하나의 텍스트 파일로 묶어 소스 개수를 크게 줄입니다.
(소스 1개당 글자 수 제한은 매우 넉넉해서, 한 달치 자막을 합쳐도 충분히 여유 있습니다.)
"""
import json
import os
from collections import defaultdict

INPUT_FILE = "data/transcripts.json"
OUTPUT_DIR = "data/notebooklm_groups"


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[notebooklm_grouped_sources] {INPUT_FILE} 이 없습니다. 먼저 fetch_transcripts.py 를 실행하세요.")
        return

    with open(INPUT_FILE, encoding="utf-8") as f:
        videos = json.load(f)

    groups: dict[str, list[dict]] = defaultdict(list)
    for v in videos:
        month = v["published_at"][:7]  # YYYY-MM
        groups[month].append(v)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for month, vids in sorted(groups.items()):
        vids.sort(key=lambda v: v["published_at"])
        parts = [f"# {month} 모닝루틴 영상 모음 ({len(vids)}개)\n"]
        for v in vids:
            url = f"https://www.youtube.com/watch?v={v['video_id']}"
            body = v.get("transcript") or v.get("description") or "(자막/설명 없음)"
            parts.append(
                "=" * 70
                + f"\n날짜: {v['published_at'][:10]}\n제목: {v['title']}\n링크: {url}\n"
                + "-" * 70
                + f"\n{body}\n"
            )
        text = "\n".join(parts)
        path = os.path.join(OUTPUT_DIR, f"{month}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[notebooklm_grouped_sources] {month}: {len(vids)}개 영상, {len(text):,}자 -> {path}")

    print(f"\n[notebooklm_grouped_sources] 총 {len(groups)}개 파일 생성 (NotebookLM 소스 {len(groups)}개 사용)")
    print("  notebook.google.com 에서 '소스 추가 > 파일 업로드' 로")
    print(f"  {OUTPUT_DIR}/ 안의 .txt 파일들을 올리세요.")


if __name__ == "__main__":
    main()
