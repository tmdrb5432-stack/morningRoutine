# 모닝루틴 유튜브 분석 파이프라인

유튜브 채널(기본값: `임현우의 모닝루틴`, `.env`의 `CHANNEL_ID`)의 영상을 수집해
종목/시장 분석 리포트를 생성하고, NotebookLM에 소스로 넣기 좋은 형태로 정리합니다.

## 설정

```bash
cp .env.example .env
# .env 에 YOUTUBE_API_KEY, GROQ_API_KEY, CHANNEL_ID 입력
```

## 실행

```bash
./run_all.sh
```

1. `fetch_videos.py` - 채널의 최근 영상 목록 수집 (`data/videos.json`)
2. `fetch_transcripts.py` - 영상별 자막 수집 (`data/transcripts.json`)
3. `analyze.py` - Groq LLM으로 영상별 종목/지수/섹터 분석 (`data/analyzed.json`)
4. `report.py` - 집계 후 투자 리포트 생성 (`data/investment_report.md`)
5. `notebooklm_sources.py` - 신규 영상 링크만 추출 (`data/notebooklm_new_links.txt`)

## NotebookLM에 소스로 추가하기

NotebookLM(notebook.google.com)은 개인 계정용 공개 API가 없어서 자동 업로드는 지원하지 않습니다.
대신 5단계에서 생성되는 `data/notebooklm_new_links.txt` 에는 **직전 실행 이후 새로 올라온 영상의
YouTube 링크만** 날짜/제목과 함께 정리되어 있습니다.

사용법:
1. `run_all.sh` (또는 `python notebooklm_sources.py`)를 실행
2. `data/notebooklm_new_links.txt` 를 열어 링크 확인
3. notebook.google.com 노트북에서 **소스 추가 > YouTube** 를 선택하고 링크를 하나씩 붙여넣기
   (NotebookLM이 자막을 자동으로 읽어 소스로 등록합니다)

이미 뽑아낸 영상은 `data/notebooklm_seen.json` 에 기록되어 다음 실행부터는 제외됩니다.
주기적으로 `run_all.sh`를 재실행하면(cron 등) 새 영상만 계속 골라낼 수 있습니다.
