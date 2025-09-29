"""
LLM 팩토리 패턴 구현 모듈
OpenAI와 Gemini LLM을 생성하고 폴백 기능을 제공하는 팩토리
"""
import asyncio
import time
from typing import Optional, Any, Union, List
from abc import ABC, abstractmethod
from PIL import Image
import io

# OpenAI 관련
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Gemini 관련
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

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
    
    @abstractmethod
    async def generate_image_edit(self, prompt: str, base_image: Image.Image, 
                                reference_image: Optional[Image.Image] = None, **kwargs) -> Optional[Image.Image]:
        """이미지 편집"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """클라이언트 사용 가능 여부"""
        pass


class OpenAILLMClient(BaseLLMClient):
    """OpenAI LLM 클라이언트"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        try:
            self.client = ChatOpenAI(
                model=config.get("model", "gpt-4o"),
                openai_api_key=config["api_key"],
                temperature=0.7
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
    
    async def generate_image_edit(self, prompt: str, base_image: Image.Image, 
                                reference_image: Optional[Image.Image] = None, **kwargs) -> Optional[Image.Image]:
        """이미지 편집 (OpenAI는 현재 미지원)"""
        self.logger.warning("OpenAI는 현재 이미지 편집을 지원하지 않습니다.")
        raise NotImplementedError("OpenAI 이미지 편집은 현재 미지원")
    
    def is_available(self) -> bool:
        """클라이언트 사용 가능 여부"""
        return hasattr(self, 'client') and self.client is not None


class GeminiLLMClient(BaseLLMClient):
    """Gemini LLM 클라이언트"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        try:
            genai.configure(api_key=config["api_key"])
            self.model = genai.GenerativeModel('gemini-2.5-flash-image-preview')
            self.logger.info("Gemini 클라이언트 초기화 완료")
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
    
    async def generate_image_edit(self, prompt: str, base_image: Image.Image, 
                                reference_image: Optional[Image.Image] = None, **kwargs) -> Optional[Image.Image]:
        """이미지 편집"""
        try:
            self.logger.info("Gemini 이미지 편집 시작")
            
            # 이미지를 API 형태로 변환
            base_image_part = self._image_to_parts(base_image)
            parts = [prompt, base_image_part]
            
            # 참고 이미지가 있는 경우 추가
            if reference_image:
                reference_image_part = self._image_to_parts(reference_image)
                parts.append(reference_image_part)
            
            # Gemini API 호출
            response = self.model.generate_content(
                parts,
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                }
            )
            
            # 응답에서 이미지 추출
            if response.parts:
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        result_image = Image.open(io.BytesIO(image_data))
                        self.logger.info("Gemini 이미지 편집 완료")
                        return result_image
            
            self.logger.warning("Gemini 응답에서 이미지 데이터를 찾을 수 없음")
            return None
            
        except Exception as e:
            self.logger.error(f"Gemini 이미지 편집 실패: {e}")
            raise
    
    def _image_to_parts(self, image: Union[str, Image.Image]) -> dict:
        """이미지를 Gemini API에서 사용할 수 있는 형태로 변환"""
        if isinstance(image, str):
            # 파일 경로인 경우
            with open(image, 'rb') as img_file:
                image_data = img_file.read()
        elif isinstance(image, Image.Image):
            # PIL Image 객체인 경우
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            image_data = img_byte_arr.getvalue()
        else:
            raise ValueError("이미지는 파일 경로 또는 PIL Image 객체여야 합니다.")
            
        return {
            "mime_type": "image/png",
            "data": image_data
        }
    
    def is_available(self) -> bool:
        """클라이언트 사용 가능 여부"""
        return hasattr(self, 'model') and self.model is not None


class LLMFactory:
    """LLM 팩토리 클래스 - 폴백 기능 포함"""
    
    def __init__(self):
        self.settings = get_llm_settings()
        self.logger = setup_logger('llm_factory')
        self._clients = {}
    
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
                if not client.is_available():
                    continue
                
                result = await client.generate_text(prompt, **kwargs)
                self.logger.info(f"{provider}로 텍스트 생성 성공")
                return result
                
            except Exception as e:
                self.logger.warning(f"{provider} 텍스트 생성 실패: {e}")
                
                # 마지막 제공자가 아니라면 다음으로 넘어감
                if provider != fallback_order[-1]:
                    self.logger.info(f"다음 제공자로 폴백: {fallback_order[fallback_order.index(provider) + 1]}")
                    await asyncio.sleep(self.settings.RETRY_DELAY_SECONDS)
                    continue
                else:
                    # 모든 제공자 실패
                    raise Exception(f"모든 LLM 제공자에서 텍스트 생성 실패. 마지막 오류: {e}")
    
    async def generate_image_edit_with_fallback(self, prompt: str, base_image: Image.Image, 
                                              reference_image: Optional[Image.Image] = None, **kwargs) -> Optional[Image.Image]:
        """폴백 기능이 있는 이미지 편집 (OpenAI -> Gemini 순서, 하지만 실제로는 Gemini만 지원)"""
        fallback_order = self.settings.get_fallback_order()
        
        if not fallback_order:
            raise Exception("사용 가능한 LLM 제공자가 없습니다.")
        
        for provider in fallback_order:
            try:
                self.logger.info(f"{provider}로 이미지 편집 시도")
                
                client = self.create_client(provider)
                if not client.is_available():
                    continue
                
                # OpenAI는 이미지 편집을 지원하지 않으므로 건너뛰기
                if provider == "openai":
                    self.logger.info("OpenAI는 이미지 편집을 지원하지 않음, 다음 제공자로 이동")
                    continue
                
                result = await client.generate_image_edit(prompt, base_image, reference_image, **kwargs)
                if result:
                    self.logger.info(f"{provider}로 이미지 편집 성공")
                    return result
                
            except NotImplementedError:
                # 지원하지 않는 기능인 경우 다음 제공자로
                self.logger.info(f"{provider}는 이미지 편집을 지원하지 않음")
                continue
                
            except Exception as e:
                self.logger.warning(f"{provider} 이미지 편집 실패: {e}")
                
                # 마지막 제공자가 아니라면 다음으로 넘어감
                if provider != fallback_order[-1]:
                    self.logger.info(f"다음 제공자로 폴백: {fallback_order[fallback_order.index(provider) + 1]}")
                    await asyncio.sleep(self.settings.RETRY_DELAY_SECONDS)
                    continue
                else:
                    # 모든 제공자 실패
                    raise Exception(f"모든 LLM 제공자에서 이미지 편집 실패. 마지막 오류: {e}")
        
        raise Exception("이미지 편집을 지원하는 LLM 제공자가 없습니다.")
    
    def get_available_providers(self) -> List[str]:
        """사용 가능한 제공자 목록"""
        return self.settings.get_available_providers()
    
    def get_fallback_order(self) -> List[str]:
        """폴백 순서 반환"""
        return self.settings.get_fallback_order()


# 전역 팩토리 인스턴스
_llm_factory_instance = None

def get_llm_factory() -> LLMFactory:
    """LLM 팩토리 싱글톤 인스턴스 반환"""
    global _llm_factory_instance
    if _llm_factory_instance is None:
        _llm_factory_instance = LLMFactory()
    return _llm_factory_instance
