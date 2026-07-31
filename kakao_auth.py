"""
카카오톡 '나에게 보내기' 알림을 쓰기 위한 최초 1회 인증 스크립트.
Kakao Developers(developers.kakao.com)에서 앱을 만들고
- REST API 키를 .env의 KAKAO_REST_API_KEY 에 입력
- 플랫폼 > Web에 KAKAO_REDIRECT_URI(.env, 기본 https://localhost.com) 등록
- 카카오 로그인 > 동의항목에서 "카카오톡 메시지 전송(talk_message)" 활성화
한 뒤 이 스크립트를 실행하세요. 브라우저에서 로그인/동의 후 리다이렉트된 주소창의
code= 값을 복사해 붙여넣으면 토큰을 발급받아 data/.kakao_token.json에 저장합니다.
"""
import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI", "https://localhost.com")
TOKEN_FILE = "data/.kakao_token.json"


def main():
    if not KAKAO_REST_API_KEY:
        print("[kakao_auth] .env에 KAKAO_REST_API_KEY를 먼저 설정하세요.")
        return

    authorize_url = (
        "https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_REST_API_KEY}&redirect_uri={KAKAO_REDIRECT_URI}"
        "&response_type=code&scope=talk_message"
    )
    print("1) 아래 주소를 브라우저에서 열고 로그인/동의하세요:\n")
    print(f"   {authorize_url}\n")
    print("2) 리다이렉트된 후 주소창의 '...?code=' 뒤에 붙은 값을 복사하세요.\n")
    code = input("code 값 입력: ").strip()

    res = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": KAKAO_REST_API_KEY,
            "redirect_uri": KAKAO_REDIRECT_URI,
            "code": code,
        },
        timeout=10,
    )
    if res.status_code != 200:
        print(f"[kakao_auth] 토큰 발급 실패: {res.status_code} {res.text}")
        return

    data = res.json()
    os.makedirs("data", exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump({"access_token": data["access_token"], "refresh_token": data["refresh_token"]}, f)

    print(f"[kakao_auth] 완료 -> {TOKEN_FILE} 저장. .env에서 KAKAO_ENABLED=true로 설정하세요.")


if __name__ == "__main__":
    main()
