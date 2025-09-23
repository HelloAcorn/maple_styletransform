# Python 3.10 slim 이미지 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 종속성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# Python 경로 설정
ENV PYTHONPATH=/app

# 필요한 디렉토리 생성
RUN mkdir -p logs files/uploads files/merged_images

# 포트 8080 노출 (Cloud Run 기본 포트)
EXPOSE 8080

# Streamlit 서버 실행을 위한 헬스체크
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# Streamlit 실행
CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true", "--server.fileWatcherType=none"]
