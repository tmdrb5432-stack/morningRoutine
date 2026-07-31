"""
한국투자증권(KIS) Open API 클라이언트.
접근 토큰 발급/캐싱과 국내주식 현재가(실시간 시세) 조회를 담당합니다.
https://apiportal.koreainvestment.com
"""
import json
import os
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")
IS_VIRTUAL = os.getenv("KIS_ENV", "real").lower() == "virtual"

BASE_URL = (
    "https://openapivts.koreainvestment.com:29443"
    if IS_VIRTUAL
    else "https://openapi.koreainvestment.com:9443"
)
TOKEN_CACHE_FILE = "data/.kis_token.json"

SIGN_LABEL = {"1": "상한", "2": "상승", "3": "보합", "4": "하한", "5": "하락"}


def _load_cached_token() -> str | None:
    if not os.path.exists(TOKEN_CACHE_FILE):
        return None
    with open(TOKEN_CACHE_FILE, encoding="utf-8") as f:
        cached = json.load(f)
    if cached.get("expires_at", 0) - 60 > time.time():
        return cached["access_token"]
    return None


def _save_token_cache(token: str, expires_in: int) -> None:
    os.makedirs("data", exist_ok=True)
    with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"access_token": token, "expires_at": time.time() + expires_in}, f)


def get_access_token() -> str:
    """접근 토큰 발급. KIS는 발급 빈도를 제한하므로 만료 전까지 캐시를 재사용합니다."""
    cached = _load_cached_token()
    if cached:
        return cached

    if not APP_KEY or not APP_SECRET:
        raise RuntimeError("KIS_APP_KEY / KIS_APP_SECRET이 설정되지 않았습니다 (.env 확인).")

    res = requests.post(
        f"{BASE_URL}/oauth2/tokenP",
        json={"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET},
        timeout=10,
    )
    res.raise_for_status()
    data = res.json()
    _save_token_cache(data["access_token"], data.get("expires_in", 86400))
    return data["access_token"]


def get_current_price(ticker: str) -> dict:
    """국내주식 현재가 시세 조회 (tr_id: FHKST01010100)."""
    token = get_access_token()
    res = requests.get(
        f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
        headers={
            "authorization": f"Bearer {token}",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET,
            "tr_id": "FHKST01010100",
            "custtype": "P",
        },
        params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker},
        timeout=10,
    )
    res.raise_for_status()
    body = res.json()
    if body.get("rt_cd") != "0":
        raise RuntimeError(f"KIS API 오류 ({ticker}): {body.get('msg1')}")

    out = body["output"]
    sign = out.get("prdy_vrss_sign", "")
    return {
        "ticker": ticker,
        "name": out.get("hts_kor_isnm", ""),
        "price": int(out.get("stck_prpr", 0)),
        "change": int(out.get("prdy_vrss", 0)),
        "change_rate": float(out.get("prdy_ctrt", 0)),
        "sign": sign,
        "sign_label": SIGN_LABEL.get(sign, ""),
        "volume": int(out.get("acml_vol", 0)),
    }


def get_daily_candles(ticker: str, days: int = 100) -> list[dict]:
    """국내주식 기간별(일봉) 시세 조회 (tr_id: FHKST03010100). 오래된 날짜순으로 반환."""
    token = get_access_token()
    end = datetime.now()
    start = end - timedelta(days=int(days * 1.6) + 10)  # 주말/공휴일 감안한 여유분

    res = requests.get(
        f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
        headers={
            "authorization": f"Bearer {token}",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET,
            "tr_id": "FHKST03010100",
            "custtype": "P",
        },
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker,
            "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0",
        },
        timeout=10,
    )
    res.raise_for_status()
    body = res.json()
    if body.get("rt_cd") != "0":
        raise RuntimeError(f"KIS API 오류 ({ticker} 일봉): {body.get('msg1')}")

    candles = [
        {
            "date": c["stck_bsop_date"],
            "close": int(c["stck_clpr"]),
            "volume": int(c["acml_vol"]),
        }
        for c in body.get("output2", [])
        if c.get("stck_bsop_date")
    ]
    candles.sort(key=lambda c: c["date"])
    return candles[-days:]
