"""
LLM 팩토리 패턴 구현 모듈
OpenAI와 Gemini LLM을 생성하고 폴백 기능을 제공하는 팩토리
"""
import asyncio
import time
from typing import Optional, Any, List, Dict
from abc import ABC, abstractmethod
import json

# OpenAI 관련
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Gemini 관련
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold

from app.core.llm_settings import get_llm_settings
from app.utils.logger import setup_logger


class BaseLLMClient(ABC):
    """LLM 클라이언트 기본 인터페이스"""
    
    def __init__(self, config: dict):
        self.config = config
        self.provider = config.get("provider", "unknown")
        self.logger = setup_logger(f'llm_{self.provider}')
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """텍스트 생성"""
        pass


class OpenAILLMClient(BaseLLMClient):
    """OpenAI LLM 클라이언트"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        try:
            self.client = ChatOpenAI(
                model=config.get("model", "gpt-5-nano"),
                openai_api_key=config["api_key"]
            )
            self.logger.info("OpenAI 클라이언트 초기화 완료")
        except Exception as e:
            self.logger.error(f"OpenAI 클라이언트 초기화 실패: {e}")
            raise
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """텍스트 생성"""
        try:
            self.logger.info("OpenAI 텍스트 생성 시작")
            
            # HumanMessage로 감싸서 전송
            message = HumanMessage(content=prompt)
            response = await self.client.ainvoke([message])
            
            result = response.content
            self.logger.info("OpenAI 텍스트 생성 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"OpenAI 텍스트 생성 실패: {e}")
            raise


class GeminiLLMClient(BaseLLMClient):
    """Gemini LLM 클라이언트"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        try:
            genai.configure(api_key=config["api_key"])
            # Gemini 2.5 Flash Image
            self.model = genai.GenerativeModel('gemini-2.5-flash-image')
            self.logger.info("Gemini 클라이언트 초기화 완료 (gemini-2.5-flash-image)")
        except Exception as e:
            self.logger.error(f"Gemini 클라이언트 초기화 실패: {e}")
            raise
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """텍스트 생성"""
        try:
            self.logger.info("Gemini 텍스트 생성 시작")
            
            response = self.model.generate_content(prompt)
            result = response.text
            
            self.logger.info("Gemini 텍스트 생성 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"Gemini 텍스트 생성 실패: {e}")
            raise


class LLMFactory:
    """LLM 팩토리 클래스 - 폴백 기능 포함"""
    
    def __init__(self):
        self.settings = get_llm_settings()
        self.logger = setup_logger('llm_factory')
        self._clients = {}
        
        # 프롬프트 매니저 초기화
        from app.utils.prompt_manager import PromptManager
        self.prompt_manager = PromptManager()
    
    def create_client(self, provider: str) -> BaseLLMClient:
        """LLM 클라이언트 생성"""
        if provider in self._clients:
            return self._clients[provider]
        
        try:
            if provider == "openai":
                config = self.settings.get_openai_config()
                client = OpenAILLMClient(config)
            elif provider == "gemini":
                config = self.settings.get_gemini_config()
                client = GeminiLLMClient(config)
            else:
                raise ValueError(f"지원하지 않는 LLM 제공자: {provider}")
            
            self._clients[provider] = client
            self.logger.info(f"{provider} 클라이언트 생성 완료")
            return client
            
        except Exception as e:
            self.logger.error(f"{provider} 클라이언트 생성 실패: {e}")
            raise
    
    async def generate_text_with_fallback(self, prompt: str, **kwargs) -> str:
        """폴백 기능이 있는 텍스트 생성 (OpenAI -> Gemini 순서)"""
        fallback_order = self.settings.get_fallback_order()
        
        if not fallback_order:
            raise Exception("사용 가능한 LLM 제공자가 없습니다.")
        
        for provider in fallback_order:
            try:
                self.logger.info(f"{provider}로 텍스트 생성 시도")
                
                client = self.create_client(provider)
                result = await client.generate_text(prompt, **kwargs)
                self.logger.info(f"{provider}로 텍스트 생성 성공")
                return result
                
            except Exception as e:
                self.logger.warning(f"{provider} 텍스트 생성 실패: {e}")
                
                # 마지막 제공자가 아니라면 다음으로 넘어감
                if provider != fallback_order[-1]:
                    self.logger.info(f"다음 제공자로 폴백: {fallback_order[fallback_order.index(provider) + 1]}")
                    await asyncio.sleep(0.1)
                    continue
                else:
                    # 모든 제공자 실패
                    raise Exception(f"모든 LLM 제공자에서 텍스트 생성 실패. 마지막 오류: {e}")
    
    def get_available_providers(self) -> List[str]:
        """사용 가능한 제공자 목록"""
        return self.settings.get_available_providers()
    
    def get_fallback_order(self) -> List[str]:
        """폴백 순서 반환"""
        return self.settings.get_fallback_order()
    
    async def analyze_human_from_image(self, image_path: str) -> Dict[str, str]:
        """
        사람 이미지를 분석하여 헤어스타일과 옷차림을 추출
        
        Args:
            image_path: 분석할 이미지 경로
            
        Returns:
            Dict: {"hairstyle": "...", "outfit": "..."} 형식의 분석 결과
        """
        try:
            self.logger.info("사람 이미지 분석 시작")
            
            # human_explain 프롬프트 로드
            human_prompt = self.prompt_manager.get_human_analysis_prompt()
            
            # 이미지와 함께 분석 요청
            from PIL import Image
            import io
            
            # 이미지 로드
            image = Image.open(image_path)
            
            # 이미지를 바이트로 변환
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Gemini API로 분석 (JSON 모드 사용)
            import google.generativeai as genai
            from google.generativeai.types import HarmCategory, HarmBlockThreshold, GenerationConfig
            
            # JSON 스키마 정의
            response_schema = {
                "type": "object",
                "properties": {
                    "hairstyle": {
                        "type": "string",
                        "description": "Detailed multi-sentence description of the person's hairstyle"
                    },
                    "outfit": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of outfit keywords ordered from top to bottom"
                    }
                },
                "required": ["hairstyle", "outfit"]
            }
            
            # JSON 모드로 모델 생성
            model = genai.GenerativeModel(
                'gemini-2.5-flash-lite-preview-09-2025',
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema
                )
            )
            
            self.logger.info("Gemini API 호출 (JSON 모드)")
            response = model.generate_content(
                [
                    human_prompt,
                    {
                        "mime_type": "image/png",
                        "data": img_byte_arr
                    }
                ],
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
            
            # JSON 응답 파싱 (Gemini JSON 모드는 항상 유효한 JSON 반환)
            analysis_result = json.loads(response.text)
            self.logger.info("JSON 응답 파싱 성공")
            
            # outfit 배열을 문자열로 변환
            processed_result = {
                "hairstyle": analysis_result.get("hairstyle", "unknown"),
                "outfit": " ".join(analysis_result.get("outfit", [])) if isinstance(analysis_result.get("outfit"), list) else str(analysis_result.get("outfit", "unknown"))
            }
            
            self.logger.info(f"사람 이미지 분석 완료: hairstyle={processed_result['hairstyle'][:100]}..., outfit={processed_result['outfit'][:100]}...")
            return processed_result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 실패: {e}, 응답 내용: {response.text[:200] if 'response' in locals() else 'N/A'}")
            return {
                "hairstyle": "unknown",
                "outfit": "unknown"
            }
        except Exception as e:
            self.logger.error(f"사람 이미지 분석 실패: {e}")
            # 기본값 반환
            return {
                "hairstyle": "unknown",
                "outfit": "unknown"
            }
    
    def build_character_edit_prompt(self, character_name: str, human_analysis: Dict[str, str]) -> str:
        """
        캐릭터 편집 프롬프트 생성
        
        Args:
            character_name: 캐릭터 이름
            human_analysis: 사람 분석 결과 {"hairstyle": "...", "face": "...", "outfit": "..."}
            
        Returns:
            str: 완성된 편집 프롬프트
        """
        try:
            # 통합 프롬프트를 분석 결과와 함께 로드
            unified_prompt = self.prompt_manager.get_unified_character_prompt_with_analysis(
                character_name, human_analysis
            )
            
            self.logger.info(f"캐릭터 편집 프롬프트 생성 완료: {character_name}")
            self.logger.debug(f"분석 결과 적용: hairstyle={human_analysis.get('hairstyle', 'unknown')[:50]}..., outfit={human_analysis.get('outfit', 'unknown')[:50]}...")
            
            return unified_prompt
            
        except Exception as e:
            self.logger.error(f"캐릭터 편집 프롬프트 생성 실패: {e}")
            raise


# 전역 팩토리 인스턴스
_llm_factory_instance = None

def get_llm_factory() -> LLMFactory:
    """LLM 팩토리 싱글톤 인스턴스 반환"""
    global _llm_factory_instance
    if _llm_factory_instance is None:
        _llm_factory_instance = LLMFactory()
    return _llm_factory_instance
