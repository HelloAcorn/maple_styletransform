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
    
    # API 키들 (파일에서 로드)
    BYTEPLUS_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # BytePlus ModelArk API 설정
    BYTEPLUS_BASE_URL = "https://ark.ap-southeast.bytepluses.com"
    BYTEPLUS_REGION = "ap-southeast"
    
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
    def load_api_keys(cls):
        """API 키 파일에서 로드"""
        api_key_file = os.path.join(os.path.dirname(__file__), '.api_key')
        
        if os.path.exists(api_key_file):
            try:
                with open(api_key_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                
                                if key == 'BYTEPLUS_API_KEY':
                                    cls.BYTEPLUS_API_KEY = value
                                elif key == 'GOOGLE_API_KEY':
                                    cls.GEMINI_API_KEY = value
                                    
            except Exception as e:
                print(f"API 키 파일 로드 중 오류 발생: {e}")
        else:
            print(f"API 키 파일을 찾을 수 없습니다: {api_key_file}")
    
    @classmethod
    def set_gemini_api_key(cls, api_key: str):
        """Gemini API 키 설정"""
        cls.GEMINI_API_KEY = api_key
    
    @classmethod
    def get_gemini_api_key(cls) -> Optional[str]:
        """Gemini API 키 반환"""
        return cls.GEMINI_API_KEY
    
    @classmethod
    def get_byteplus_api_key(cls) -> Optional[str]:
        """BytePlus API 키 반환"""
        return cls.BYTEPLUS_API_KEY
    
    @classmethod
    def get_byteplus_headers(cls) -> dict:
        """BytePlus API 요청 헤더 생성"""
        if not cls.BYTEPLUS_API_KEY:
            cls.load_api_keys()
        
        # API 키가 여전히 없으면 오류 발생
        if not cls.BYTEPLUS_API_KEY:
            raise ValueError("BytePlus API 키를 찾을 수 없습니다. .api_key 파일을 확인해주세요.")
        
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
