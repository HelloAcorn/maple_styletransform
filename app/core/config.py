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
        """환경 변수에서 우선 로드, 없으면 파일에서 로드"""
        # 1. 환경 변수에서 먼저 시도
        cls.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        cls.BYTEPLUS_API_KEY = os.getenv('BYTEPLUS_API_KEY')
        
        # 환경 변수에서 로드되었으면 바로 리턴
        if cls.GEMINI_API_KEY and cls.BYTEPLUS_API_KEY:
            print("✅ 환경 변수에서 API 키 로드 완료")
            return
        
        # 2. 환경 변수에 없으면 파일에서 로드 (로컬 개발용)
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
                                
                                if key == 'BYTEPLUS_API_KEY' and not cls.BYTEPLUS_API_KEY:
                                    cls.BYTEPLUS_API_KEY = value
                                elif key == 'GOOGLE_API_KEY' and not cls.GEMINI_API_KEY:
                                    cls.GEMINI_API_KEY = value
                print("✅ 파일에서 API 키 로드 완료")
            except Exception as e:
                print(f"⚠️ API 키 파일 로드 중 오류 발생: {e}")
        else:
            # 클라우드 환경에서는 파일이 없어도 정상
            if not cls.GEMINI_API_KEY and not cls.BYTEPLUS_API_KEY:
                print("⚠️ API 키를 환경 변수나 파일에서 찾을 수 없습니다.")
    
    @classmethod
    def set_gemini_api_key(cls, api_key: str):
        """Gemini API 키 설정"""
        cls.GEMINI_API_KEY = api_key
    
    @classmethod
    def get_gemini_api_key(cls) -> Optional[str]:
        """Gemini API 키 반환"""
        # API 키가 없으면 환경 변수에서 다시 확인
        if not cls.GEMINI_API_KEY:
            cls.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        return cls.GEMINI_API_KEY
    
    @classmethod
    def get_byteplus_api_key(cls) -> Optional[str]:
        """BytePlus API 키 반환"""
        # API 키가 없으면 환경 변수에서 다시 확인
        if not cls.BYTEPLUS_API_KEY:
            cls.BYTEPLUS_API_KEY = os.getenv('BYTEPLUS_API_KEY')
        return cls.BYTEPLUS_API_KEY
    
    @classmethod
    def get_byteplus_headers(cls) -> dict:
        """BytePlus API 요청 헤더 생성"""
        # API 키가 없으면 로드 시도
        if not cls.BYTEPLUS_API_KEY:
            cls.load_api_keys()
        
        # API 키가 여전히 없으면 더 자세한 오류 메시지
        if not cls.BYTEPLUS_API_KEY:
            error_msg = "BytePlus API 키를 찾을 수 없습니다.\n"
            error_msg += "1. Cloud Run 환경 변수에 BYTEPLUS_API_KEY를 설정하거나\n"
            error_msg += "2. 로컬 개발 환경에서는 app/core/.api_key 파일을 확인해주세요."
            raise ValueError(error_msg)
        
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
