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
