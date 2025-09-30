"""
LLM 기반 이미지 처리 통합 모듈
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


class LLMImageProcessor:
    """LLM 기반 이미지 처리 클래스"""
    
    def __init__(self):
        """
        LLM 기반 이미지 처리 클라이언트 초기화
        """
        self.logger = setup_logger('image_integration')
        self.prompt_manager = PromptManager()
        
        log_function_call(self.logger, "LLMImageProcessor.__init__")
        
        try:
            # LLM Settings에서 API 키 가져오기
            from app.core.llm_settings import get_llm_settings
            settings = get_llm_settings()
            
            if not settings.is_gemini_available():
                raise ValueError("Gemini API 키가 설정되지 않았습니다.")
            
            self.api_key = settings.GOOGLE_API_KEY
            genai.configure(api_key=self.api_key)
            
            # Gemini 2.5 Flash Image Preview 모델 (이미지 생성 지원)
            self.model = genai.GenerativeModel('gemini-2.5-flash-image-preview')
            self.logger.info("LLM 이미지 프로세서 초기화 완료")
        except Exception as e:
            log_error(self.logger, e, "LLM 이미지 프로세서 초기화")
        
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
    
    async def analyze_and_merge_images(self, base_character: Union[str, Image.Image], 
                                      reference_photo: Union[str, Image.Image], 
                                      character_name: str = None) -> Optional[Image.Image]:
        """
        사람 이미지를 분석하고 캐릭터를 편집하는 통합 메소드
        
        Args:
            base_character: 기본 픽셀 아트 캐릭터 이미지
            reference_photo: 사람의 셀카 이미지
            character_name: 캐릭터 이름
            
        Returns:
            PIL.Image.Image: 편집된 픽셀 아트 캐릭터 또는 None (실패 시)
        """
        try:
            from app.modules.llm_factory import get_llm_factory
            import asyncio
            
            self.logger.info("통합 이미지 처리 시작")
            
            # 이미지 경로 처리
            if isinstance(reference_photo, Image.Image):
                # PIL Image를 임시 파일로 저장
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    reference_photo.save(tmp.name)
                    reference_photo_path = tmp.name
            else:
                reference_photo_path = reference_photo
            
            # LLM Factory 인스턴스 가져오기
            factory = get_llm_factory()
            
            # 1단계: 사람 이미지 분석
            self.logger.info("사람 이미지 분석 중...")
            human_analysis = await factory.analyze_human_from_image(reference_photo_path)
            self.logger.info(f"분석 결과: {human_analysis}")
            
            # 2단계: 캐릭터 편집 프롬프트 생성
            self.logger.info("캐릭터 편집 프롬프트 생성 중...")
            edit_prompt = factory.build_character_edit_prompt(character_name, human_analysis)
            
            # 3단계: 이미지 편집 실행
            self.logger.info("이미지 편집 실행 중...")
            
            # 이미지 로드
            if isinstance(base_character, str):
                base_character = Image.open(base_character)
            if isinstance(reference_photo, str):
                reference_photo = Image.open(reference_photo)
            
            # Gemini API로 직접 편집
            base_character_part = self._image_to_parts(base_character)
            reference_photo_part = self._image_to_parts(reference_photo)
            
            # 강화된 편집 프롬프트 생성
            enhanced_edit_prompt = f"""🚨 EDITING MODE: Modify the PROVIDED PIXEL SPRITE (first image) using reference from the human photo (second image).

            {edit_prompt}

            🎯 IMAGE ROLES:
            - FIRST IMAGE (Pixel Sprite): This is your BASE - EDIT this sprite ONLY
            - SECOND IMAGE (Human Photo): This is REFERENCE ONLY - do not recreate this person as a new character

            🚨 CRITICAL: Edit the pixel sprite (first image) by applying changes from the reference (second image). Do NOT generate a new character."""

            response = self.model.generate_content(
                [
                    enhanced_edit_prompt,
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
            
            # 응답에서 이미지 추출
            if response.parts:
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        result_image = Image.open(io.BytesIO(image_data))
                        self.logger.info("통합 이미지 처리 성공")
                        
                        # 임시 파일 정리
                        if 'reference_photo_path' in locals() and reference_photo_path != reference_photo:
                            import os
                            os.unlink(reference_photo_path)
                        
                        return result_image
            
            self.logger.warning("응답에서 이미지를 찾을 수 없음")
            return None
            
        except Exception as e:
            log_error(self.logger, e, "통합 이미지 처리")
            return None
    
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
            # 이미지 로드
            if isinstance(base_character, str):
                base_character = Image.open(base_character)
            if isinstance(reference_photo, str):
                reference_photo = Image.open(reference_photo)
            
            # 기존 방식으로 이미지 편집 수행
            return self._legacy_merge_images(base_character, reference_photo, character_name)
                
        except Exception as e:
            log_error(self.logger, e, "이미지 편집")
            return None
    
    def _legacy_merge_images(self, base_character: Image.Image, reference_photo: Image.Image, character_name: str = None) -> Optional[Image.Image]:
        """기존 방식의 이미지 편집 (폴백용)"""
        try:
            self.logger.info("기존 방식으로 픽셀 아트 캐릭터 편집 시작")
            
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
            log_error(self.logger, e, "기존 방식 픽셀 아트 캐릭터 편집")
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
