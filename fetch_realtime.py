"""
data/summary.json의 상위 언급 종목(top_stocks) 중 국내주식(6자리 티커)에 대해
한국투자증권(KIS) Open API로 실시간 현재가를 조회하고,
data/investment_report.md 끝에 실시간 시세 표를 추가합니다.
"""
import json
import os
import re
import time

from tqdm import tqdm

from kis_client import get_current_price

INPUT_FILE = "data/summary.json"
OUTPUT_FILE = "data/realtime_prices.json"
REPORT_FILE = "data/investment_report.md"
KR_TICKER = re.compile(r"^\d{6}$")


def main():
    os.makedirs("data", exist_ok=True)

    with open(INPUT_FILE, encoding="utf-8") as f:
        summary = json.load(f)

    tickers = [s["ticker"] for s in summary.get("top_stocks", []) if KR_TICKER.match(s.get("ticker", ""))]
    print(f"[fetch_realtime] 국내 종목 {len(tickers)}개 실시간 시세 조회 중 (한국투자증권 API)...")

    results = []
    for ticker in tqdm(tickers):
        try:
            results.append(get_current_price(ticker))
        except Exception as e:
            print(f"[fetch_realtime] {ticker} 조회 실패: {e}")
        time.sleep(0.2)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[fetch_realtime] {len(results)}개 시세 저장 -> {OUTPUT_FILE}")

    if results and os.path.exists(REPORT_FILE):
        rows = "\n".join(
            f"| {r['name']} | {r['ticker']} | {r['price']:,}원 | "
            f"{r['change']:+,} ({r['change_rate']:+.2f}%) | {r['sign_label']} |"
            for r in results
        )
        section = (
            "\n\n---\n\n## 실시간 시세 (한국투자증권 API)\n\n"
            "| 종목명 | 티커 | 현재가 | 전일대비 | 상태 |\n"
            "|---|---|---|---|---|\n"
            f"{rows}\n"
        )
        with open(REPORT_FILE, "a", encoding="utf-8") as f:
            f.write(section)
        print(f"[fetch_realtime] 실시간 시세 표를 {REPORT_FILE} 에 추가했습니다.")


if __name__ == "__main__":
    main()
