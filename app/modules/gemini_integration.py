"""
Gemini 2.5 Flash Image Preview API 통합 모듈
"""
import os
import io
import base64
from typing import Optional, Union
from PIL import Image
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.core.config import APIConfig
from app.utils.logger import setup_logger, log_function_call, log_api_request, log_error
from app.utils.prompt_manager import PromptManager


class GeminiImageProcessor:
    """Gemini 2.5 Flash Image Preview 모델을 사용한 이미지 처리 클래스"""
    
    def __init__(self, api_key: str):
        """
        Gemini API 클라이언트 초기화
        
        Args:
            api_key (str): Google AI Studio API 키
        """
        self.logger = setup_logger('gemini_integration')
        self.api_key = api_key
        self.prompt_manager = PromptManager()
        
        log_function_call(self.logger, "GeminiImageProcessor.__init__", api_key_length=len(api_key) if api_key else 0)
        
        try:
            genai.configure(api_key=api_key)
            # Gemini 2.5 Flash Image Preview 모델 (이미지 생성 지원)
            self.model = genai.GenerativeModel('gemini-2.5-flash-image-preview')
        except Exception as e:
            log_error(self.logger, e, "Gemini API 클라이언트 초기화")
        
    def _image_to_parts(self, image: Union[str, Image.Image]) -> dict:
        """
        이미지를 Gemini API에서 사용할 수 있는 형태로 변환
        
        Args:
            image: 이미지 파일 경로 또는 PIL Image 객체
            
        Returns:
            dict: Gemini API용 이미지 파트
        """
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
    
    def merge_images(self, base_character: Union[str, Image.Image], reference_photo: Union[str, Image.Image], 
                    style: str = "natural", character_name: str = None) -> Optional[Image.Image]:
        """
        픽셀 아트 캐릭터를 참고 사진의 스타일로 편집
        
        Args:
            base_character: 기본 픽셀 아트 캐릭터 이미지
            reference_photo: 스타일 참고용 사진
            style: 편집 스타일 (현재는 사용하지 않음, 프롬프트 고정)
            character_name: 캐릭터 이름 (프롬프트 선택용)
            
        Returns:
            PIL.Image.Image: 편집된 픽셀 아트 캐릭터 또는 None (실패 시)
        """
        log_function_call(self.logger, "merge_images", 
                         base_character_type=type(base_character).__name__, 
                         reference_photo_type=type(reference_photo).__name__,
                         style=style)
        
        try:
            self.logger.info("픽셀 아트 캐릭터 편집 시작")
            
            # 이미지를 API 형태로 변환
            self.logger.debug("이미지를 API 형태로 변환 중")
            base_character_part = self._image_to_parts(base_character)
            reference_photo_part = self._image_to_parts(reference_photo)
            
            # YAML에서 픽셀 아트 편집 프롬프트 로드 (캐릭터 정보 전달)
            prompt = self.prompt_manager.get_pixel_art_prompt(character_name)
            
            # Gemini API 호출
            log_api_request(self.logger, "Gemini", "generate_content", "픽셀 아트 편집 요청 시작")  
            response = self.model.generate_content(
                [
                    prompt,
                    base_character_part,
                    reference_photo_part
                ],
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                }
            )
            log_api_request(self.logger, "Gemini", "generate_content", "응답 수신")
            
            # 응답에서 이미지 추출
            if response.parts:
                for i, part in enumerate(response.parts):
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        result_image = Image.open(io.BytesIO(image_data))
                        return result_image
                    elif hasattr(part, 'text'):
                        self.logger.debug(f"파트 {i}에서 텍스트 응답: {part.text[:100]}...")
            
            self.logger.warning("응답에서 이미지 데이터를 찾을 수 없음")
            return None
            
        except Exception as e:
            log_error(self.logger, e, "픽셀 아트 캐릭터 편집")
            return None
    
    def create_artistic_merge(self, base_character: Union[str, Image.Image], reference_photo: Union[str, Image.Image], 
                            style: str = "natural", character_name: str = None) -> Optional[Image.Image]:
        """
        픽셀 아트 캐릭터를 참고 사진의 스타일로 예술적으로 편집
        
        Args:
            base_character: 기본 픽셀 아트 캐릭터 이미지
            reference_photo: 스타일 참고용 사진
            style: 편집 스타일 (현재는 사용하지 않음, 프롬프트 고정)
            character_name: 캐릭터 이름 (프롬프트 선택용)
            
        Returns:
            PIL.Image.Image: 편집된 픽셀 아트 캐릭터 또는 None (실패 시)
        """
        # merge_images 메서드를 직접 호출 (동일한 기능)
        return self.merge_images(base_character, reference_photo, style, character_name)
