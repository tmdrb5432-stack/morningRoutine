"""
로컬(Mac)에서 상시 실행하는 실시간 시세 서버.
백그라운드 스레드가 KIS API를 주기적으로 폴링해 메모리에 최신 시세를 보관하고,
/api/prices로 제공합니다. static/dashboard.html이 이를 주기적으로 fetch해 화면을 갱신합니다.

Tailscale Funnel 등으로 외부에 노출할 경우를 대비해 기본 인증(Basic Auth)을 지원합니다.
"""
import json
import os
import re
import threading
import time
from datetime import date
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory

import notifier
import strategy
from kis_client import get_current_price, get_daily_candles

load_dotenv()

WATCHLIST_ENV = os.getenv("WATCHLIST", "005930,000660")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "3"))
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "")
PORT = int(os.getenv("PORT", "8080"))
CANDLE_REFRESH_SEC = 6 * 3600  # 일봉은 장중 바뀌지 않으므로 몇 시간에 한 번만 갱신

KR_TICKER = re.compile(r"^\d{6}$")

app = Flask(__name__, static_folder="static")

state = {"prices": {}, "errors": {}, "updated_at": None, "alerts": []}
state_lock = threading.Lock()
candle_cache: dict[str, dict] = {}  # ticker -> {"candles": [...], "fetched_at": ts}
fired_keys: set[str] = set()  # "{ticker}:{signal_type}:{date}" 중복 알림 방지


def load_watchlist() -> list[str]:
    tickers = dict.fromkeys(t.strip() for t in WATCHLIST_ENV.split(",") if KR_TICKER.match(t.strip()))
    if os.path.exists("data/summary.json"):
        with open("data/summary.json", encoding="utf-8") as f:
            summary = json.load(f)
        for s in summary.get("top_stocks", []):
            ticker = s.get("ticker", "")
            if KR_TICKER.match(ticker):
                tickers.setdefault(ticker, None)
    return list(tickers.keys())[:20]


def get_candles_cached(ticker: str) -> list[dict]:
    cached = candle_cache.get(ticker)
    if cached and time.time() - cached["fetched_at"] < CANDLE_REFRESH_SEC:
        return cached["candles"]
    candles = get_daily_candles(ticker, days=max(strategy.MA_LONG, strategy.RSI_PERIOD) + 20)
    candle_cache[ticker] = {"candles": candles, "fetched_at": time.time()}
    return candles


def poll_loop():
    while True:
        prices, errors = {}, {}
        new_alerts = []
        today = date.today().isoformat()

        for ticker in load_watchlist():
            try:
                current = get_current_price(ticker)
                prices[ticker] = current
            except Exception as e:
                errors[ticker] = str(e)
                continue

            try:
                candles = get_candles_cached(ticker)
                signals = strategy.evaluate(current.get("name", ticker), ticker, candles, current)
            except Exception as e:
                print(f"[server] {ticker} 전략 평가 실패: {e}")
                signals = []

            for sig in signals:
                key = f"{ticker}:{sig['type']}:{today}"
                if key in fired_keys:
                    continue
                fired_keys.add(key)
                alert = {**sig, "ticker": ticker, "fired_at": time.time()}
                new_alerts.append(alert)

            time.sleep(0.2)

        with state_lock:
            state["prices"] = prices
            state["errors"] = errors
            state["updated_at"] = time.time()
            if new_alerts:
                state["alerts"] = (new_alerts + state["alerts"])[:50]

        if new_alerts:
            notifier.notify([a["message"] for a in new_alerts])

        time.sleep(max(POLL_INTERVAL, 1))


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if DASHBOARD_USER and DASHBOARD_PASS:
            auth = request.authorization
            if not auth or auth.username != DASHBOARD_USER or auth.password != DASHBOARD_PASS:
                return Response(
                    "Authentication required", 401, {"WWW-Authenticate": 'Basic realm="dashboard"'}
                )
        return f(*args, **kwargs)

    return wrapper


@app.route("/")
@require_auth
def index():
    return send_from_directory("static", "dashboard.html")


@app.route("/api/prices")
@require_auth
def api_prices():
    with state_lock:
        return jsonify(
            {
                "prices": list(state["prices"].values()),
                "errors": state["errors"],
                "updated_at": state["updated_at"],
                "poll_interval": POLL_INTERVAL,
            }
        )


@app.route("/api/alerts")
@require_auth
def api_alerts():
    with state_lock:
        return jsonify({"alerts": state["alerts"]})


if __name__ == "__main__":
    if not DASHBOARD_USER or not DASHBOARD_PASS:
        print(
            "[server] 경고: DASHBOARD_USER / DASHBOARD_PASS가 설정되지 않았습니다. "
            "인증 없이 열려있는 상태입니다 - 외부(Tailscale Funnel 등)에 노출하기 전에 .env에 설정하세요."
        )
    threading.Thread(target=poll_loop, daemon=True).start()
    print(f"[server] http://0.0.0.0:{PORT} 에서 실행 중 (watchlist: {load_watchlist()})")
    app.run(host="0.0.0.0", port=PORT)
