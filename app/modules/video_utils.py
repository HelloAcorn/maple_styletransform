"""
동영상 처리 유틸리티 모듈
"""
import os
import uuid
from datetime import datetime
from typing import Optional, Tuple
import streamlit as st

from app.utils.logger import setup_logger, log_function_call, log_error


class VideoUtils:
    """동영상 처리 관련 유틸리티 클래스"""
    
    logger = setup_logger('video_utils')
    
    @staticmethod
    def create_video_directories():
        """동영상 저장을 위한 디렉토리 생성"""
        directories = [
            "app/static/videos"
        ]
        
        log_function_call(VideoUtils.logger, "create_video_directories")
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            VideoUtils.logger.debug(f"동영상 디렉토리 생성/확인: {directory}")
    
    @staticmethod
    def get_video_save_path(filename: Optional[str] = None) -> str:
        """
        동영상 저장 경로 생성
        
        Args:
            filename: 파일명 (None인 경우 자동 생성)
            
        Returns:
            str: 동영상 저장 경로
        """
        VideoUtils.create_video_directories()
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_video_{timestamp}_{uuid.uuid4().hex[:8]}.mp4"
        
        return os.path.join("app/static/videos", filename)
    
    @staticmethod
    def get_video_info(video_path: str) -> dict:
        """
        동영상 정보 추출
        
        Args:
            video_path: 동영상 파일 경로
            
        Returns:
            dict: 동영상 정보
        """
        try:
            if not os.path.exists(video_path):
                return {"error": "파일이 존재하지 않습니다."}
            
            file_size = os.path.getsize(video_path)
            file_size_mb = file_size / (1024 * 1024)
            
            return {
                "path": video_path,
                "size_bytes": file_size,
                "size_mb": round(file_size_mb, 2),
                "exists": True
            }
        except Exception as e:
            return {"error": f"정보 추출 실패: {str(e)}"}
    
    @staticmethod
    def cleanup_old_videos(directory: str = "app/static/videos", max_files: int = 20):
        """
        오래된 동영상 파일들을 정리
        
        Args:
            directory: 정리할 디렉토리
            max_files: 유지할 최대 파일 수
        """
        if not os.path.exists(directory):
            return
            
        files = []
        for filename in os.listdir(directory):
            if filename.endswith('.mp4'):
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
                    print(f"오래된 동영상 파일 삭제: {file_path}")
                except Exception as e:
                    print(f"파일 삭제 실패: {file_path}, 오류: {str(e)}")
    
    @staticmethod
    def validate_video_settings(duration: int, resolution: str) -> Tuple[bool, str]:
        """
        동영상 설정 유효성 검사
        
        Args:
            duration: 동영상 길이
            resolution: 해상도
            
        Returns:
            Tuple[bool, str]: (유효성, 오류 메시지)
        """
        # 길이 검사
        if duration < 2 or duration > 10:
            return False, "동영상 길이는 2-10초 사이여야 합니다."
        
        # 해상도 검사
        supported_resolutions = [
            "1024x576", "576x1024", "768x768", 
            "1280x720", "720x1280"
        ]
        
        if resolution not in supported_resolutions:
            return False, f"지원되지 않는 해상도입니다. 지원 해상도: {', '.join(supported_resolutions)}"
        
        return True, ""


def display_video_info(video_path: str, title: str = "동영상 정보"):
    """
    Streamlit에서 동영상 정보를 표시하는 헬퍼 함수
    
    Args:
        video_path: 동영상 파일 경로
        title: 표시할 제목
    """
    info = VideoUtils.get_video_info(video_path)
    
    if "error" in info:
        st.error(f"❌ {info['error']}")
        return
    
    st.subheader(title)
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**파일 크기:** {info['size_mb']} MB")
    
    with col2:
        st.write(f"**형식:** MP4")


def display_video_generation_progress(current_step: int, total_steps: int, 
                                    step_description: str):
    """
    동영상 생성 진행 상황을 표시하는 헬퍼 함수
    
    Args:
        current_step: 현재 단계
        total_steps: 전체 단계 수
        step_description: 현재 단계 설명
    """
    progress = current_step / total_steps
    st.progress(progress)
    st.text(f"🎬 {step_description} ({current_step}/{total_steps})")


def create_video_generation_prompt_templates() -> dict:
    """동영상 생성을 위한 프롬프트 템플릿 반환"""
    return {
        "natural": "자연스럽고 부드러운 움직임으로 생동감 있는 동영상을 만들어주세요.",
        "cinematic": "영화적이고 드라마틱한 분위기로 동영상을 생성해주세요.",
        "smooth": "매우 부드럽고 유연한 움직임으로 동영상을 만들어주세요.",
        "dynamic": "역동적이고 활기찬 움직임으로 동영상을 생성해주세요.",
        "artistic": "예술적이고 창의적인 표현으로 동영상을 만들어주세요.",
        "realistic": "현실적이고 자연스러운 움직임으로 동영상을 생성해주세요."
    }
