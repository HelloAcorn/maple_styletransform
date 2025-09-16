"""
Asset 이미지 관리 모듈
동적으로 디렉토리의 이미지들을 관리하는 범용 모듈입니다.
"""
import os
import glob
from typing import List, Dict, Optional, Union
from PIL import Image
import streamlit as st

from app.utils.logger import setup_logger


class AssetManager:
    """Asset 이미지 관리 클래스 - 범용 디렉토리 기반"""
    
    def __init__(self):
        """AssetManager 초기화"""
        self.logger = setup_logger('asset_manager')
        
        # 지원하는 이미지 확장자
        self.supported_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
        
        # 캐시된 이미지 목록 (성능 최적화)
        self._cached_images = {}
    
    def get_images_from_directory(self, directory: str, use_cache: bool = True) -> Dict[str, str]:
        """
        지정된 디렉토리에서 이미지 파일들을 가져옵니다.
        
        Args:
            directory: 이미지 디렉토리 경로
            use_cache: 캐시 사용 여부
        
        Returns:
            Dict[str, str]: {파일명(확장자 제외): 파일 경로} 형태의 딕셔너리
        """
        # 캐시 확인
        if use_cache and directory in self._cached_images:
            return self._cached_images[directory]
        
        images = {}
        
        if not os.path.exists(directory):
            self.logger.warning(f"디렉토리가 존재하지 않습니다: {directory}")
            return images
        
        # 지원하는 이미지 파일들 검색
        for ext in self.supported_extensions:
            pattern = os.path.join(directory, f"*{ext}")
            for file_path in glob.glob(pattern):
                filename = os.path.basename(file_path)
                name_without_ext = os.path.splitext(filename)[0]
                images[name_without_ext] = file_path
        
        # 캐시에 저장
        if use_cache:
            self._cached_images[directory] = images
        
        self.logger.info(f"디렉토리 {directory}에서 {len(images)}개의 이미지를 발견했습니다.")
        return images
    
    def get_options_from_directory(self, directory: str) -> List[str]:
        """
        디렉토리에서 이미지 선택 옵션 리스트를 반환합니다.
        
        Args:
            directory: 이미지 디렉토리 경로
        
        Returns:
            List[str]: 이미지 이름 리스트
        """
        images = self.get_images_from_directory(directory)
        return list(images.keys())
    
    def get_asset(self, directory: str, asset_name: str, output_type: str = "path") -> Union[str, Image.Image, None]:
        """
        지정된 디렉토리에서 asset을 가져옵니다.
        
        Args:
            directory: 이미지 디렉토리 경로
            asset_name: asset 이름
            output_type: 출력 타입 ("path" 또는 "image")
        
        Returns:
            Union[str, Image.Image, None]: 경로 문자열, PIL Image 객체, 또는 None
        """
        images = self.get_images_from_directory(directory)
        image_path = images.get(asset_name)
        
        if not image_path or not os.path.exists(image_path):
            self.logger.warning(f"asset을 찾을 수 없습니다: {asset_name} in {directory}")
            return None
        
        if output_type == "path":
            return image_path
        elif output_type == "image":
            try:
                image = Image.open(image_path)
                self.logger.info(f"asset 이미지 로드 성공: {asset_name}")
                return image
            except Exception as e:
                self.logger.error(f"asset 이미지 로드 실패 ({asset_name}): {str(e)}")
                return None
        else:
            raise ValueError(f"지원하지 않는 output_type: {output_type}. 'path' 또는 'image'를 사용하세요.")
    
    def display_selector(self, directory: str, label: str, key: str, help_text: str = None) -> Optional[str]:
        """
        범용 Streamlit 선택기를 표시합니다.
        
        Args:
            directory: 이미지 디렉토리 경로
            label: 선택기 라벨
            key: Streamlit 위젯 키
            help_text: 도움말 텍스트
            
        Returns:
            Optional[str]: 선택된 이미지 이름 또는 None
        """
        options = self.get_options_from_directory(directory)
        
        if not options:
            st.warning(f"⚠️ {directory}에서 사용 가능한 이미지가 없습니다.")
            return None
        
        # 선택 옵션에 "선택하세요" 추가
        display_options = ["선택하세요"] + options
        
        selected = st.selectbox(
            label,
            options=display_options,
            key=key,
            help=help_text or f"{directory}에서 이미지를 선택하세요."
        )
        
        if selected == "선택하세요":
            return None
        
        return selected
    
    def display_preview(self, directory: str, asset_name: str, caption: str = "선택된 이미지") -> None:
        """
        범용 이미지 미리보기를 표시합니다.
        
        Args:
            directory: 이미지 디렉토리 경로
            asset_name: asset 이름
            caption: 이미지 캡션
        """
        image = self.get_asset(directory, asset_name, output_type="image")
        
        if image:
            st.image(image, caption=caption, use_container_width=True)
            
            # 이미지 정보 표시
            st.caption(f"📝 **{asset_name}** - {image.size[0]}×{image.size[1]} 픽셀")
        else:
            st.error(f"❌ 이미지를 불러올 수 없습니다: {asset_name}")
    
    # 편의 메서드들 (기존 호환성 유지)
    def display_character_selector(self, key: str = "character_selector") -> Optional[str]:
        """캐릭터 선택기 (호환성 유지)"""
        return self.display_selector("files/character_image", "캐릭터를 선택하세요:", key, "미리 준비된 캐릭터 중에서 선택하세요.")
    
    def display_character_preview(self, character_name: str, caption: str = "선택된 캐릭터") -> None:
        """캐릭터 미리보기 (호환성 유지)"""
        self.display_preview("files/character_image", character_name, caption)
    
    def display_face_selector(self, key: str = "face_selector") -> Optional[str]:
        """얼굴 모양 선택기 (호환성 유지)"""
        return self.display_selector("files/face_image", "얼굴 모양을 선택하세요:", key, "미리 준비된 얼굴 모양 중에서 선택하세요.")
    
    def display_face_preview(self, face_name: str, caption: str = "선택된 얼굴 모양") -> None:
        """얼굴 모양 미리보기 (호환성 유지)"""
        self.display_preview("files/face_image", face_name, caption)
    
    # 편의 메서드들 (경로 기반)
    def get_character_options(self) -> List[str]:
        """캐릭터 옵션 (호환성 유지)"""
        return self.get_options_from_directory("files/character_image")
    
    def get_face_options(self) -> List[str]:
        """얼굴 모양 옵션 (호환성 유지)"""
        return self.get_options_from_directory("files/face_image")
    
    def load_character_image(self, character_name: str) -> Optional[Image.Image]:
        """캐릭터 이미지 로드 (호환성 유지)"""
        return self.get_asset("files/character_image", character_name, output_type="image")
    
    def load_face_image(self, face_name: str) -> Optional[Image.Image]:
        """얼굴 모양 이미지 로드 (호환성 유지)"""
        return self.get_asset("files/face_image", face_name, output_type="image")
    
    def clear_cache(self, directory: str = None) -> None:
        """
        캐시를 지웁니다.
        
        Args:
            directory: 특정 디렉토리 캐시만 지우기 (None이면 전체 캐시 지우기)
        """
        if directory:
            self._cached_images.pop(directory, None)
            self.logger.info(f"디렉토리 {directory}의 캐시를 지웠습니다.")
        else:
            self._cached_images.clear()
            self.logger.info("전체 캐시를 지웠습니다.")


# 전역 인스턴스 (싱글톤 패턴)
_asset_manager_instance = None

def get_asset_manager() -> AssetManager:
    """AssetManager 싱글톤 인스턴스 반환"""
    global _asset_manager_instance
    if _asset_manager_instance is None:
        _asset_manager_instance = AssetManager()
    return _asset_manager_instance
