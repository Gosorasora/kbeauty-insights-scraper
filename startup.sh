#!/bin/bash

# Azure App Service 시작 스크립트
# Flask 웹 애플리케이션 실행

echo "K-Beauty RAG AI 애플리케이션 시작..."

# 환경 변수 확인
if [ -z "$AZURE_OPENAI_ENDPOINT" ]; then
    echo "❌ AZURE_OPENAI_ENDPOINT 환경 변수가 설정되지 않았습니다."
    exit 1
fi

echo "✓ 환경 변수 확인 완료"

# Flask 웹 애플리케이션 실행
echo "🌐 Flask 웹 애플리케이션 시작..."
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 app:app