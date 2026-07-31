# morningRoutine

유튜브 '모닝루틴' 채널 자막을 분석해 투자 리포트를 만들고, 한국투자증권(KIS) API로 실시간 시세를 붙이는 파이프라인입니다.

## 1. 리포트 파이프라인 (배치)

```bash
cp .env.example .env   # API 키 입력
bash run_all.sh
```

`fetch_videos.py` → `fetch_transcripts.py` → `analyze.py` → `report.py` → `fetch_realtime.py` 순으로 실행되어 `data/investment_report.md`를 생성합니다.

## 2. 로컬 실시간 시세 대시보드 (Mac에서 상시 실행)

`server.py`는 KIS API를 몇 초 간격으로 폴링해 브라우저에 실시간으로 보여주는 로컬 서버입니다.

```bash
pip install -r requirements.txt
# .env에 KIS_APP_KEY / KIS_APP_SECRET / WATCHLIST / DASHBOARD_USER / DASHBOARD_PASS 설정
python server.py
```

`http://localhost:8080` 접속 시 실시간 시세가 보입니다. `WATCHLIST`(콤마로 구분된 6자리 종목코드)로 볼 종목을 지정하고, `data/summary.json`이 있으면 리포트 상위 언급 종목도 자동으로 함께 표시됩니다.

### 다른 곳(회사 등)에서 브라우저만으로 접속하기 — Tailscale Funnel

로컬 Mac 외부에서 별도 프로그램 설치 없이 접속하려면 [Tailscale](https://tailscale.com) Funnel을 사용합니다.

```bash
brew install tailscale
sudo tailscale up
tailscale funnel 8080
```

명령 실행 후 나오는 `https://<기기이름>.<tailnet>.ts.net` 주소를 아무 브라우저에서 열면 됩니다(로그인 불필요, 설치도 불필요 — 접속하는 쪽은 링크만 있으면 됨). 인터넷에 공개되는 주소이므로 **반드시 `.env`의 `DASHBOARD_USER` / `DASHBOARD_PASS`를 설정**해 기본 인증을 걸어두세요.

`tailscale funnel 8080`을 켜둔 상태로 `python server.py`를 계속 실행 중이면 됩니다. 둘 다 터미널을 닫으면 꺼지므로, 상시로 두려면 `caffeinate -i python server.py`로 절전 방지하거나 launchd/tmux로 백그라운드 등록하세요.

## 3. 매매 전략 알림

`server.py`는 3초마다 시세를 갱신하면서, `strategy.py`의 조건을 하나라도 만족하면(같은 종목·같은 조건은 하루 1회만) 알림을 띄웁니다.

- **골든크로스 / 데드크로스**: `MA_SHORT`일선이 `MA_LONG`일선을 상/하향 돌파
- **RSI 과매수 / 과매도**: RSI가 `RSI_OVERBOUGHT` 이상 / `RSI_OVERSOLD` 이하
- **급등락**: 전일대비 `PRICE_CHANGE_ALERT_PCT`% 이상 변동
- **거래량 급증**: 20일 평균 거래량 대비 `VOLUME_SPIKE_MULT`배 이상

`.env`에서 임계값을 조정할 수 있습니다. 알림은 3곳에 동시에 뜹니다:

1. **대시보드 배너** — 페이지 하단 "전략 알림" 영역에 항상 표시
2. **브라우저 알림** — 대시보드 탭을 열어둔 채로(회사에서도) 데스크톱 알림으로 표시. 최초 접속 시 알림 권한을 허용해야 함
3. **이메일 / 카카오톡** — 탭을 안 열어놔도 받고 싶을 때

### 이메일 알림 설정

Gmail 기준, [구글 계정 2단계 인증](https://myaccount.google.com/security)을 켠 뒤 [앱 비밀번호](https://myaccount.google.com/apppasswords)를 발급받아 `.env`의 `SMTP_USER`(내 Gmail 주소) / `SMTP_APP_PASSWORD`(발급받은 16자리)에 입력하고 `EMAIL_ENABLED=true`로 설정하세요.

### 카카오톡 '나에게 보내기' 알림 설정

1. [Kakao Developers](https://developers.kakao.com)에서 앱 생성 → REST API 키를 `.env`의 `KAKAO_REST_API_KEY`에 입력
2. 앱 설정 > 플랫폼 > Web에 `KAKAO_REDIRECT_URI`(기본값 `https://localhost.com`, `.env`와 동일해야 함) 등록
3. 카카오 로그인 > 동의항목에서 "카카오톡 메시지 전송(talk_message)" 활성화
4. `python kakao_auth.py` 실행 → 안내되는 주소를 브라우저에서 열어 로그인/동의 → 리다이렉트된 주소창의 `code=` 값을 터미널에 붙여넣기 → 토큰 저장됨
5. `.env`에서 `KAKAO_ENABLED=true`로 설정

카카오 access token은 몇 시간 뒤 만료되지만 `notifier.py`가 refresh token으로 자동 갱신합니다. refresh token 자체가 만료되면(약 2개월) `kakao_auth.py`를 다시 실행하세요.
