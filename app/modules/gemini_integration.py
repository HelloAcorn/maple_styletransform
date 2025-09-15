"""
Gemini 2.0 Flash Image API 통합 모듈
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


class GeminiImageProcessor:
    """Gemini 2.0 Flash Image 모델을 사용한 이미지 처리 클래스"""
    
    def __init__(self, api_key: str):
        """
        Gemini API 클라이언트 초기화
        
        Args:
            api_key (str): Google AI Studio API 키
        """
        self.logger = setup_logger('gemini_integration')
        self.api_key = api_key
        
        log_function_call(self.logger, "GeminiImageProcessor.__init__", api_key_length=len(api_key) if api_key else 0)
        
        try:
            genai.configure(api_key=api_key)
            # Gemini 2.0 Flash 모델 (이미지 생성 지원)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            self.logger.info("Gemini API 클라이언트 초기화 완료")
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
    
    def merge_images(self, image1: Union[str, Image.Image], image2: Union[str, Image.Image], 
                    prompt: str = "이 두 이미지를 자연스럽게 하나로 합쳐주세요. 두 이미지의 요소들이 조화롭게 어우러지도록 해주세요.") -> Optional[Image.Image]:
        """
        두 이미지를 Gemini 2.0 Flash 모델을 사용하여 하나로 합침
        
        Args:
            image1: 첫 번째 이미지
            image2: 두 번째 이미지
            prompt: 이미지 합성을 위한 프롬프트
            
        Returns:
            PIL.Image.Image: 합성된 이미지 또는 None (실패 시)
        """
        log_function_call(self.logger, "merge_images", 
                         image1_type=type(image1).__name__, 
                         image2_type=type(image2).__name__,
                         prompt_length=len(prompt))
        
        try:
            self.logger.info("이미지 합성 시작")
            
            # 이미지를 API 형태로 변환
            self.logger.debug("이미지를 API 형태로 변환 중")
            image1_part = self._image_to_parts(image1)
            image2_part = self._image_to_parts(image2)
            
            # Gemini API 호출
            log_api_request(self.logger, "Gemini", "generate_content", "요청 시작")
            response = self.model.generate_content(
                [
                    prompt,
                    image1_part,
                    image2_part
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
                self.logger.info(f"응답에서 {len(response.parts)}개의 파트 발견")
                for i, part in enumerate(response.parts):
                    if hasattr(part, 'inline_data') and part.inline_data:
                        self.logger.info(f"파트 {i}에서 이미지 데이터 추출 성공")
                        image_data = part.inline_data.data
                        result_image = Image.open(io.BytesIO(image_data))
                        self.logger.info(f"합성된 이미지 크기: {result_image.size}")
                        return result_image
            
            self.logger.warning("응답에서 이미지 데이터를 찾을 수 없음")
            return None
            
        except Exception as e:
            log_error(self.logger, e, "이미지 합성")
            return None
    
    def create_artistic_merge(self, image1: Union[str, Image.Image], image2: Union[str, Image.Image], 
                            style: str = "natural") -> Optional[Image.Image]:
        """
        특정 스타일로 두 이미지를 예술적으로 합성
        
        Args:
            image1: 첫 번째 이미지
            image2: 두 번째 이미지
            style: 합성 스타일 ("natural", "artistic", "seamless", "collage")
            
        Returns:
            PIL.Image.Image: 합성된 이미지 또는 None (실패 시)
        """
        style_prompts = {
            "natural": "이 두 이미지를 자연스럽고 현실적으로 하나로 합쳐주세요.",
            "artistic": "이 두 이미지를 예술적이고 창의적으로 합성하여 하나의 작품으로 만들어주세요.",
            "seamless": "이 두 이미지를 경계가 보이지 않게 완전히 자연스럽게 합쳐주세요.",
            "collage": "이 두 이미지를 콜라주 스타일로 조화롭게 배치하여 하나의 이미지로 만들어주세요."
        }
        
        prompt = style_prompts.get(style, style_prompts["natural"])
        return self.merge_images(image1, image2, prompt)
