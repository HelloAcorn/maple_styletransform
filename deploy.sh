#!/bin/bash

# Google Cloud Run 배포 스크립트
# 사용법: ./deploy.sh [PROJECT_ID] [REGION]

set -e

# 기본값 설정
PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"asia-northeast3"}  # 서울 리전
SERVICE_NAME="maple-styletransform"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 메이플 스타일 트랜스폼 앱을 Cloud Run에 배포합니다..."
echo "프로젝트 ID: $PROJECT_ID"
echo "리전: $REGION"
echo "서비스명: $SERVICE_NAME"

# Google Cloud 프로젝트 설정
echo "📋 Google Cloud 프로젝트 설정 중..."
gcloud config set project $PROJECT_ID

# Docker 이미지 빌드
echo "🔨 Docker 이미지 빌드 중..."
docker build -t $IMAGE_NAME:latest .

# Container Registry에 이미지 푸시
echo "📤 Container Registry에 이미지 푸시 중..."
docker push $IMAGE_NAME:latest

# Cloud Run에 배포
echo "🌐 Cloud Run에 배포 중..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 80 \
  --max-instances 10 \
  --set-env-vars "STREAMLIT_SERVER_HEADLESS=true,STREAMLIT_SERVER_PORT=8080"

echo "✅ 배포 완료!"
echo "🔗 서비스 URL을 확인하려면 다음 명령어를 실행하세요:"
echo "gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)'"
