"""
애플리케이션 설정 및 API 키 관리 모듈
"""
import os
from typing import Optional
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class APIConfig:
    """API 설정 관리 클래스"""
    
    # BytePlus ModelArk API 설정
    BYTEPLUS_API_KEY = "df6cf3b8-6eeb-41b5-8f2b-fbef64f41eb4"
    BYTEPLUS_BASE_URL = "https://ark.cn-beijing.volces.com"
    BYTEPLUS_REGION = "cn-beijing"
    
    # Gemini API 설정 (기존)
    GEMINI_API_KEY: Optional[str] = None
    
    # 애플리케이션 설정
    MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", "10485760"))  # 10MB
    DEFAULT_MAX_DIMENSION = int(os.getenv("DEFAULT_MAX_DIMENSION", "1024"))
    CLEANUP_MAX_FILES = int(os.getenv("CLEANUP_MAX_FILES", "50"))
    
    # 동영상 생성 설정
    VIDEO_OUTPUT_FORMAT = "mp4"
    VIDEO_QUALITY = "high"
    VIDEO_DURATION_MIN = 2  # 최소 2초
    VIDEO_DURATION_MAX = 10  # 최대 10초
    
    @classmethod
    def set_gemini_api_key(cls, api_key: str):
        """Gemini API 키 설정"""
        cls.GEMINI_API_KEY = api_key
    
    @classmethod
    def get_gemini_api_key(cls) -> Optional[str]:
        """Gemini API 키 반환"""
        return cls.GEMINI_API_KEY
    
    @classmethod
    def get_byteplus_headers(cls) -> dict:
        """BytePlus API 요청 헤더 생성"""
        return {
            "Authorization": f"Bearer {cls.BYTEPLUS_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    @classmethod
    def validate_api_keys(cls) -> dict:
        """API 키 유효성 검사"""
        return {
            "gemini": cls.GEMINI_API_KEY is not None and len(cls.GEMINI_API_KEY) > 10,
            "byteplus": cls.BYTEPLUS_API_KEY is not None and len(cls.BYTEPLUS_API_KEY) > 10
        }
