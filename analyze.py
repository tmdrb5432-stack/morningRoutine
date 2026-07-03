"""
영상 제목에서 날짜를 추출하고 Groq LLM으로 해당 날짜의
한국경제신문 주요 이슈를 추론하여 종목/시장 데이터를 생성합니다.
"""
import json
import os
import re
import time
from groq import Groq
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

INPUT_FILE = "data/videos.json"
OUTPUT_FILE = "data/analyzed.json"

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """당신은 한국 주식/금융 시장 전문가입니다.
한국경제신문 모닝루틴은 매일 아침 한국경제신문 주요 기사를 브리핑하는 채널입니다.
주어진 날짜를 보고, 그 시기의 한국 및 글로벌 경제 상황을 바탕으로
해당 날짜 방송에서 다루었을 법한 종목, 지수, 섹터, 이슈를 JSON으로만 답하세요.
반드시 아래 형식의 JSON만 출력하세요. 설명이나 다른 텍스트는 절대 포함하지 마세요.

{"stocks":[{"ticker":"005930","name":"삼성전자","sentiment":"positive","mentions":3}],"indices":[{"name":"코스피","direction":"up","mentions":2}],"sectors":[{"name":"반도체","sentiment":"positive"}],"key_events":["이벤트1"],"overall_market":"bullish"}

한국 주식은 종목코드(숫자 6자리), 미국 주식은 영문 티커 사용. 없는 항목은 빈 배열."""


def extract_date(title: str) -> str:
    m = re.search(r"(\d{8})", title)
    if m:
        d = m.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return ""


def analyze_episode(video: dict) -> dict:
    date = extract_date(video["title"])
    prompt = f"날짜: {date}\n영상 제목: {video['title']}\n\n이 날짜 한국경제신문 모닝루틴 주요 종목/지수/섹터/이슈를 JSON으로만 출력하세요."

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            max_tokens=512,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw = completion.choices[0].message.content.strip()
        start = raw.find("{")
        if start > 0:
            raw = raw[start:]
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rstrip("`").strip()
        analysis = json.loads(raw)
    except Exception as e:
        analysis = {"error": str(e), "stocks": [], "indices": [], "sectors": [], "key_events": [], "overall_market": "mixed"}

    return {**video, "date": date, "analysis": analysis}


def main():
    os.makedirs("data", exist_ok=True)

    with open(INPUT_FILE, encoding="utf-8") as f:
        videos = json.load(f)

    morning_videos = [v for v in videos if extract_date(v["title"])]
    print(f"[analyze] 모닝루틴 영상: {len(morning_videos)}/{len(videos)}개")

    done_ids = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            existing = json.load(f)
        done = [v for v in existing if "error" not in v.get("analysis", {"error": True})]
        done_ids = {v["video_id"] for v in done}
        results = done
    else:
        results = []

    remaining = [v for v in morning_videos if v["video_id"] not in done_ids]
    print(f"[analyze] {len(remaining)}개 분석 시작 (완료: {len(done_ids)}개)...")

    for video in tqdm(remaining):
        analyzed = analyze_episode(video)
        results.append(analyzed)
        if len(results) % 20 == 0:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        time.sleep(0.1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[analyze] 완료 -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
