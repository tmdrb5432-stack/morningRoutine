"""
analyzed.json을 집계하여 1년간 최다 언급 종목, 섹터, 시장 동향을 분석하고
Groq LLM으로 최적 투자처 리포트를 생성합니다.
"""
import json
import os
from collections import defaultdict
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

INPUT_FILE = "data/analyzed.json"
OUTPUT_FILE = "data/investment_report.md"

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def aggregate(videos: list[dict]) -> dict:
    stock_mentions: dict[str, dict] = {}
    index_mentions: dict[str, dict] = defaultdict(lambda: {"up": 0, "down": 0, "sideways": 0, "total": 0})
    sector_sentiment: dict[str, dict] = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})
    market_mood = {"bullish": 0, "bearish": 0, "mixed": 0}
    all_events: list[str] = []

    for v in videos:
        a = v.get("analysis", {})
        if not a or "error" in a:
            continue

        for s in a.get("stocks", []):
            key = s.get("ticker") or s.get("name", "?")
            if key not in stock_mentions:
                stock_mentions[key] = {"name": s.get("name", key), "ticker": key,
                                       "positive": 0, "negative": 0, "neutral": 0, "total": 0}
            sentiment = s.get("sentiment", "neutral")
            count = s.get("mentions", 1)
            stock_mentions[key][sentiment] += count
            stock_mentions[key]["total"] += count

        for idx in a.get("indices", []):
            name = idx.get("name", "?")
            direction = idx.get("direction", "sideways")
            index_mentions[name][direction] += idx.get("mentions", 1)
            index_mentions[name]["total"] += idx.get("mentions", 1)

        for sec in a.get("sectors", []):
            name = sec.get("name", "?")
            sentiment = sec.get("sentiment", "neutral")
            sector_sentiment[name][sentiment] += 1

        mood = a.get("overall_market", "mixed")
        if mood in market_mood:
            market_mood[mood] += 1

        all_events.extend(a.get("key_events", []))

    top_stocks = sorted(stock_mentions.values(), key=lambda x: x["total"], reverse=True)[:30]
    top_sectors = sorted(sector_sentiment.items(),
                         key=lambda x: x[1]["positive"] - x[1]["negative"], reverse=True)

    return {
        "total_videos": len(videos),
        "date_range": {
            "from": min((v.get("date", "9999") for v in videos if v.get("date")), default=""),
            "to": max((v.get("date", "0000") for v in videos if v.get("date")), default=""),
        },
        "market_mood": market_mood,
        "top_stocks": top_stocks,
        "index_summary": dict(index_mentions),
        "sector_ranking": [(k, v) for k, v in top_sectors],
        "event_sample": list(set(all_events))[:50],
    }


def generate_report(summary: dict) -> str:
    prompt = f"""다음은 유튜브 '임현우의 모닝루틴' 채널의 1년치({summary['date_range']['from']} ~ {summary['date_range']['to']}) 데이터 집계 결과입니다.
총 {summary['total_videos']}개 영상을 분석했습니다.

== 시장 분위기 ==
{json.dumps(summary['market_mood'], ensure_ascii=False)}

== 상위 30개 언급 종목 ==
{json.dumps(summary['top_stocks'], ensure_ascii=False, indent=2)}

== 지수 동향 ==
{json.dumps(summary['index_summary'], ensure_ascii=False, indent=2)}

== 섹터 순위 (긍정-부정 기준) ==
{json.dumps(summary['sector_ranking'][:15], ensure_ascii=False, indent=2)}

== 주요 이벤트 샘플 ==
{json.dumps(summary['event_sample'], ensure_ascii=False, indent=2)}

위 데이터를 바탕으로 다음 항목을 포함한 투자 리포트를 한국어 마크다운으로 작성해주세요:

1. **1년간 시장 총평** - 전반적인 시장 분위기와 주요 트렌드
2. **최고 주목 종목 TOP 10** - 언급 빈도와 긍/부정 비율, 투자 매력도 분석
3. **유망 섹터** - 지속적으로 긍정 언급된 섹터와 이유
4. **주의 종목/섹터** - 부정 언급이 많은 것들과 리스크
5. **최적 투자 포트폴리오 제안** - 구체적인 비중 제안 (공격형 / 안정형)
6. **향후 리스크 요인** - 주의해야 할 거시경제 이벤트

※ 이 리포트는 투자 참고용이며 실제 투자 결정은 본인 책임입니다."""

    completion = client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content


def main():
    os.makedirs("data", exist_ok=True)

    with open(INPUT_FILE, encoding="utf-8") as f:
        videos = json.load(f)

    print(f"[report] {len(videos)}개 영상 데이터 집계 중...")
    summary = aggregate(videos)

    with open("data/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("[report] 집계 완료 -> data/summary.json")

    print("[report] Groq LLM으로 투자 리포트 생성 중...")
    report = generate_report(summary)

    header = f"""# 유튜브 모닝루틴 기반 주식 투자 분석 리포트

> 분석 기간: {summary['date_range']['from']} ~ {summary['date_range']['to']}
> 분석 영상 수: {summary['total_videos']}개
> 생성일: {datetime.now().strftime('%Y-%m-%d')}

---

"""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(header + report)

    print(f"\n[report] 완료 -> {OUTPUT_FILE}")
    print("=" * 60)
    print((header + report)[:3000])
    print("\n... (전체 내용은 data/investment_report.md 참조)")


if __name__ == "__main__":
    main()
