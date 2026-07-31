#!/bin/bash
# 전체 파이프라인 실행 스크립트
set -e

echo "======================================"
echo " 유튜브 모닝루틴 주식 분석 파이프라인"
echo "======================================"

pip install -r requirements.txt -q

if [ ! -f .env ]; then
    echo "[오류] .env 파일이 없습니다. .env.example을 복사하고 API 키를 입력하세요."
    echo "  cp .env.example .env"
    exit 1
fi

echo ""
echo "[1/5] 유튜브 영상 목록 수집..."
python fetch_videos.py

echo ""
echo "[2/5] 자막(트랜스크립트) 수집..."
python fetch_transcripts.py

echo ""
echo "[3/5] Groq AI로 종목/시장 분석..."
python analyze.py

echo ""
echo "[4/5] 투자 리포트 생성..."
python report.py

echo ""
echo "[5/5] 한국투자증권 API로 실시간 시세 조회..."
KIS_APP_KEY_SET=$(grep -E '^KIS_APP_KEY=' .env | cut -d= -f2-)
if [ -n "$KIS_APP_KEY_SET" ] && [ "$KIS_APP_KEY_SET" != "your_kis_app_key_here" ]; then
    python fetch_realtime.py
else
    echo "  (KIS_APP_KEY 미설정 - 실시간 시세 조회 건너뜀)"
fi

echo ""
echo "======================================"
echo " 완료! data/investment_report.md 확인"
echo "======================================"
