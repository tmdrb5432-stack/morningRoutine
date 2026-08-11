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
5. `notebooklm_sources.py` - 신규 영상 YouTube 링크만 추출 (`data/notebooklm_new_links.txt`)
6. `notebooklm_grouped_sources.py` - 전체 영상을 월별로 묶은 텍스트 파일 생성 (`data/notebooklm_groups/*.txt`)

## NotebookLM에 소스로 추가하기

NotebookLM(notebook.google.com)은 개인 계정용 공개 API가 없어서 자동 업로드는 지원하지 않습니다.
또한 무료 요금제는 **노트북당 소스 개수가 50개로 제한**되어 있어, 매일 올라오는 영상을
하나씩 링크로 넣으면 1년치(약 300개)를 감당할 수 없습니다. 그래서 상황에 따라 두 방법을
같이 씁니다.

### 방법 A. 대량 과거분(예: 1년치) 넣기 → 월별 묶음 파일 (권장)

`notebooklm_grouped_sources.py`는 `data/transcripts.json`의 모든 영상을 **월 단위 텍스트
파일 하나**로 묶어 `data/notebooklm_groups/2025-08.txt` 처럼 저장합니다. 1년치를 넣어도
소스 12개면 충분해서 무료 한도(50개) 안에 넉넉히 들어옵니다.

1. `python fetch_videos.py && python fetch_transcripts.py && python notebooklm_grouped_sources.py`
   (`DAYS_TO_FETCH=365`가 기본값이라 첫 실행 시 1년치가 모두 포함됩니다)
2. notebook.google.com 노트북에서 **소스 추가 > 파일 업로드**를 선택하고
   `data/notebooklm_groups/` 안의 `.txt` 파일들을 한 번에 드래그해서 업로드

### 방법 B. 그날그날 새로 올라오는 영상만 추가

`notebooklm_sources.py`는 직전 실행 이후 새로 올라온 영상의 **YouTube 링크만** 한 줄씩
`data/notebooklm_new_links.txt`에 정리합니다(NotebookLM의 소스 추가 입력창은 URL만 받으므로
날짜/제목 같은 텍스트는 넣지 않습니다). 하루 1개씩 늘어나는 정도라면 소스 한도에 바로
걸리지 않으니, 개별 링크로 편하게 추가하면 됩니다.

1. `run_all.sh` (또는 `python notebooklm_sources.py`)를 실행
2. `data/notebooklm_new_links.txt` 를 열어 링크 확인
3. notebook.google.com 노트북에서 **소스 추가 > YouTube** 를 선택하고 링크를 하나씩 붙여넣기

이미 뽑아낸 영상은 `data/notebooklm_seen.json` 에 기록되어 다음 실행부터는 제외됩니다.
개별 링크 소스가 쌓여서 한도에 가까워지면, 해당 기간 영상들을 지우고 방법 A의 월별
묶음 파일로 교체하는 걸 권장합니다.

주기적으로 `run_all.sh`를 재실행하면(cron 등) 새 영상만 계속 골라낼 수 있습니다.
