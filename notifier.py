"""
전략 신호를 이메일 / 카카오톡(나에게 보내기)으로 전송합니다.
설정되지 않은 채널은 조용히 건너뜁니다.
"""
import json
import os
import smtplib
import time
from email.mime.text import MIMEText

import requests
from dotenv import load_dotenv

load_dotenv()

EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")
EMAIL_TO = os.getenv("EMAIL_TO", SMTP_USER)

KAKAO_ENABLED = os.getenv("KAKAO_ENABLED", "false").lower() == "true"
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_TOKEN_FILE = "data/.kakao_token.json"


def send_email(subject: str, body: str) -> None:
    if not EMAIL_ENABLED:
        return
    if not SMTP_USER or not SMTP_APP_PASSWORD:
        print("[notifier] EMAIL_ENABLED=true 이지만 SMTP_USER/SMTP_APP_PASSWORD 미설정 - 건너뜀")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_USER, [EMAIL_TO], msg.as_string())
    except Exception as e:
        print(f"[notifier] 이메일 전송 실패: {e}")


def _load_kakao_tokens() -> dict | None:
    if not os.path.exists(KAKAO_TOKEN_FILE):
        return None
    with open(KAKAO_TOKEN_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_kakao_tokens(tokens: dict) -> None:
    os.makedirs("data", exist_ok=True)
    tokens["saved_at"] = time.time()
    with open(KAKAO_TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f)


def _refresh_kakao_token(tokens: dict) -> str | None:
    try:
        res = requests.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": KAKAO_REST_API_KEY,
                "refresh_token": tokens["refresh_token"],
            },
            timeout=10,
        )
        res.raise_for_status()
        data = res.json()
        tokens["access_token"] = data["access_token"]
        if "refresh_token" in data:
            tokens["refresh_token"] = data["refresh_token"]
        _save_kakao_tokens(tokens)
        return tokens["access_token"]
    except Exception as e:
        print(f"[notifier] 카카오 토큰 갱신 실패: {e} (kakao_auth.py를 다시 실행해 재인증 필요)")
        return None


def send_kakao(text: str) -> None:
    if not KAKAO_ENABLED:
        return
    tokens = _load_kakao_tokens()
    if not tokens:
        print("[notifier] KAKAO_ENABLED=true 이지만 토큰이 없습니다 - 먼저 `python kakao_auth.py`를 실행하세요")
        return

    template = {"object_type": "text", "text": text, "link": {}}
    res = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=10,
    )
    if res.status_code == 401:
        new_token = _refresh_kakao_token(tokens)
        if not new_token:
            return
        res = requests.post(
            "https://kapi.kakao.com/v2/api/talk/memo/default/send",
            headers={"Authorization": f"Bearer {new_token}"},
            data={"template_object": json.dumps(template, ensure_ascii=False)},
            timeout=10,
        )
    if res.status_code != 200:
        print(f"[notifier] 카카오 전송 실패: {res.status_code} {res.text}")


def notify(signal_messages: list[str]) -> None:
    if not signal_messages:
        return
    body = "\n".join(signal_messages)
    send_email("[모닝루틴] 매매 신호 알림", body)
    for msg in signal_messages:
        send_kakao(msg)
