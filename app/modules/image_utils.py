"""
이미지 업로드 및 처리 유틸리티 모듈
"""
import os
import uuid
from datetime import datetime
from typing import Optional, Tuple
from PIL import Image
import streamlit as st

from app.utils.logger import setup_logger, log_function_call, log_error


class ImageUtils:
    """이미지 처리 관련 유틸리티 클래스"""
    
    logger = setup_logger('image_utils')
    
    @staticmethod
    def create_directories():
        """필요한 디렉토리 생성"""
        directories = [
            "files/uploads",
            "files/merged_images"
        ]
        
        log_function_call(ImageUtils.logger, "create_directories")
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            ImageUtils.logger.debug(f"디렉토리 생성/확인: {directory}")
    
    @staticmethod
    def save_uploaded_file(uploaded_file, save_dir: str = "files/uploads") -> str:
        """
        업로드된 파일을 저장
        
        Args:
            uploaded_file: Streamlit 업로드 파일 객체
            save_dir: 저장할 디렉토리 경로
            
        Returns:
            str: 저장된 파일의 경로
        """
        os.makedirs(save_dir, exist_ok=True)
        
        # 고유한 파일명 생성
        file_extension = uploaded_file.name.split('.')[-1]
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        file_path = os.path.join(save_dir, unique_filename)
        
        # 파일 저장
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        return file_path
    
    @staticmethod
    def save_pil_image(image: Image.Image, save_dir: str = "files/merged_images", 
                      filename: Optional[str] = None) -> str:
        """
        PIL Image 객체를 파일로 저장
        
        Args:
            image: PIL Image 객체
            save_dir: 저장할 디렉토리 경로
            filename: 파일명 (None인 경우 자동 생성)
            
        Returns:
            str: 저장된 파일의 경로
        """
        os.makedirs(save_dir, exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"merged_image_{timestamp}_{uuid.uuid4().hex[:8]}.png"
        
        file_path = os.path.join(save_dir, filename)
        image.save(file_path, "PNG", quality=95)
        
        return file_path
    
    @staticmethod
    def validate_image_file(uploaded_file) -> bool:
        """
        업로드된 파일이 유효한 이미지인지 검증
        
        Args:
            uploaded_file: Streamlit 업로드 파일 객체
            
        Returns:
            bool: 유효한 이미지 파일 여부
        """
        if uploaded_file is None:
            return False
            
        # 파일 확장자 검사
        allowed_extensions = ['jpg', 'jpeg', 'png', 'bmp', 'gif', 'webp']
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            return False
        
        # 파일 크기 검사 (10MB 제한)
        max_size = 10 * 1024 * 1024  # 10MB
        if uploaded_file.size > max_size:
            return False
            
        return True
    
    @staticmethod
    def get_image_info(image: Image.Image) -> dict:
        """
        이미지 정보 추출
        
        Args:
            image: PIL Image 객체
            
        Returns:
            dict: 이미지 정보 (크기, 모드, 포맷 등)
        """
        return {
            "size": image.size,
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": image.format
        }
    
    @staticmethod
    def resize_image_if_needed(image: Image.Image, max_dimension: int = 1024) -> Image.Image:
        """
        이미지가 너무 큰 경우 리사이즈
        
        Args:
            image: PIL Image 객체
            max_dimension: 최대 가로/세로 크기
            
        Returns:
            PIL.Image.Image: 리사이즈된 이미지
        """
        width, height = image.size
        
        if width <= max_dimension and height <= max_dimension:
            return image
        
        # 비율을 유지하면서 리사이즈
        if width > height:
            new_width = max_dimension
            new_height = int(height * (max_dimension / width))
        else:
            new_height = max_dimension
            new_width = int(width * (max_dimension / height))
        
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    @staticmethod
    def cleanup_old_files(directory: str, max_files: int = 50):
        """
        오래된 파일들을 정리
        
        Args:
            directory: 정리할 디렉토리
            max_files: 유지할 최대 파일 수
        """
        if not os.path.exists(directory):
            return
            
        files = []
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                files.append((file_path, os.path.getctime(file_path)))
        
        # 생성 시간 기준으로 정렬
        files.sort(key=lambda x: x[1])
        
        # 오래된 파일들 삭제
        if len(files) > max_files:
            files_to_delete = files[:-max_files]
            for file_path, _ in files_to_delete:
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"파일 삭제 실패: {file_path}, 오류: {str(e)}")


