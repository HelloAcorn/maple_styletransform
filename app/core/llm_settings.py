"""
LLM 설정 관리 모듈
OpenAI와 Gemini API 키를 불러와서 설정하는 모듈
"""
import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

from app.utils.logger import setup_logger

class LLMSettings:
    """LLM API 키 및 설정 관리 클래스"""
    
    def __init__(self):
        """LLM 설정 초기화"""
        self.logger = setup_logger('llm_settings')
        
        # 환경 변수 로드
        load_dotenv()
        
        # API 키들
        self.OPENAI_API_KEY: Optional[str] = None
        self.GOOGLE_API_KEY: Optional[str] = None
        
        # 설정 로드
        self.load_api_keys()
        
        # 기본 모델 설정
        self.DEFAULT_OPENAI_MODEL = "gpt-4o"
        self.DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
        
        # 폴백 설정
        self.RETRY_DELAY_SECONDS = 1.0
        
        self.logger.info("LLM 설정 초기화 완료")
    
    def load_api_keys(self):
        """환경 변수와 파일에서 API 키 로드"""
        # 1. 환경 변수에서 먼저 시도
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
        
        # 환경 변수에서 로드되었으면 바로 리턴
        if self.OPENAI_API_KEY and self.GOOGLE_API_KEY:
            self.logger.info("✅ 환경 변수에서 모든 API 키 로드 완료")
            return
        
        # 2. 환경 변수에 없으면 파일에서 로드 (로컬 개발용)
        # app/core에서 같은 폴더의 .api_key 파일 참조
        api_key_file = Path(__file__).parent / '.api_key'
        
        if api_key_file.exists():
            try:
                with open(api_key_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                
                                if key == 'OPENAI_API_KEY' and not self.OPENAI_API_KEY:
                                    self.OPENAI_API_KEY = value
                                elif key == 'GOOGLE_API_KEY' and not self.GOOGLE_API_KEY:
                                    self.GOOGLE_API_KEY = value
                
                self.logger.info("✅ 파일에서 API 키 로드 완료")
            except Exception as e:
                self.logger.error(f"⚠️ API 키 파일 로드 중 오류 발생: {e}")
        else:
            self.logger.warning("⚠️ API 키 파일을 찾을 수 없습니다.")
        
        # 로드 결과 확인
        self._validate_api_keys()
    
    def _validate_api_keys(self):
        """API 키 유효성 검사"""
        validation_result = {
            "openai": self.OPENAI_API_KEY is not None and len(self.OPENAI_API_KEY) > 10,
            "gemini": self.GOOGLE_API_KEY is not None and len(self.GOOGLE_API_KEY) > 10
        }
        
        for provider, is_valid in validation_result.items():
            if is_valid:
                self.logger.info(f"✅ {provider.upper()} API 키 유효")
            else:
                self.logger.warning(f"❌ {provider.upper()} API 키 없음 또는 유효하지 않음")
        
        if not any(validation_result.values()):
            self.logger.error("❌ 사용 가능한 API 키가 없습니다!")
    
    def get_openai_config(self) -> dict:
        """OpenAI 설정 반환"""
        if not self.OPENAI_API_KEY:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        
        return {
            "api_key": self.OPENAI_API_KEY,
            "model": self.DEFAULT_OPENAI_MODEL,
            "provider": "openai"
        }
    
    def get_gemini_config(self) -> dict:
        """Gemini 설정 반환"""
        if not self.GOOGLE_API_KEY:
            raise ValueError("Google API 키가 설정되지 않았습니다.")
        
        return {
            "api_key": self.GOOGLE_API_KEY,
            "model": self.DEFAULT_GEMINI_MODEL,
            "provider": "gemini"
        }
    
    def is_openai_available(self) -> bool:
        """OpenAI 사용 가능 여부"""
        return self.OPENAI_API_KEY is not None and len(self.OPENAI_API_KEY) > 10
    
    def is_gemini_available(self) -> bool:
        """Gemini 사용 가능 여부"""
        return self.GOOGLE_API_KEY is not None and len(self.GOOGLE_API_KEY) > 10
    
    def get_available_providers(self) -> list:
        """사용 가능한 LLM 제공자 목록"""
        providers = []
        if self.is_openai_available():
            providers.append("openai")
        if self.is_gemini_available():
            providers.append("gemini")
        return providers
    
    def get_fallback_order(self) -> list:
        """폴백 순서 반환 (OpenAI -> Gemini)"""
        fallback_order = []
        if self.is_openai_available():
            fallback_order.append("openai")
        if self.is_gemini_available():
            fallback_order.append("gemini")
        return fallback_order


# 전역 설정 인스턴스
_llm_settings_instance = None

def get_llm_settings() -> LLMSettings:
    """LLM 설정 싱글톤 인스턴스 반환"""
    global _llm_settings_instance
    if _llm_settings_instance is None:
        _llm_settings_instance = LLMSettings()
    return _llm_settings_instance

