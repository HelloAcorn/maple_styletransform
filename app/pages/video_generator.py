"""
동영상 생성 페이지
라우터 시스템과 레이아웃 추상화를 사용하는 새로운 구조
"""
import streamlit as st
from PIL import Image
import time
from typing import Dict, Any

from app.core.router import PageSpec
from app.modules.image_utils import ImageUtils
from app.modules.byteplus_integration import BytePlusVideoGenerator
from app.modules.video_utils import VideoUtils
from app.utils.logger import setup_logger
from app.utils.prompt_manager import PromptManager


class VideoGeneratorPage:
    """동영상 생성 페이지"""
    
    # 페이지 메타데이터
    spec = PageSpec(
        name="동영상 생성",
        icon="🎬",
        order=20,
        requires_api_key=False  # BytePlus API는 별도 관리
    )
    
    def __init__(self):
        self.logger = setup_logger('video_generator')
        self.prompt_manager = PromptManager()
    
    def render(self, ctx: Dict[str, Any]) -> None:
        """
        페이지 렌더링
        
        Args:
            ctx: 애플리케이션 컨텍스트
        """
        # 컨텍스트에서 레이아웃 팩토리 추출
        layout_factory = ctx.get('layout_factory')
        
        st.subheader("🎬 동영상 생성")
        
        # 합성된 이미지 확인
        has_synthesized = 'synthesized_images' in st.session_state and len(st.session_state.synthesized_images) > 0
        
        selected_image = None
        selected_image_name = None
        selected_image_info = None
        
        if has_synthesized:
            # 합성된 이미지가 있을 때: 1:1 레이아웃
            col_left, col_right = st.columns([1, 1])
            
            with col_left:
                st.subheader("📁 이미지 업로드")
                
                uploaded_file = st.file_uploader(
                    "동영상으로 변환할 이미지를 선택하세요",
                    type=['jpg', 'jpeg', 'png', 'bmp', 'webp'],
                    key="image_video"
                )
                
                if uploaded_file:
                    selected_image = Image.open(uploaded_file)
                    selected_image_name = uploaded_file.name
                    st.image(selected_image, caption=selected_image_name, use_container_width=True)
            
            with col_right:
                st.subheader("🎨 합성된 이미지")
                
                # 합성된 이미지 선택
                synthesized_options = [
                    f"{img['filename']}" 
                    for img in st.session_state.synthesized_images
                ]
                
                selected_synthesized = st.selectbox(
                    "합성된 이미지 선택:",
                    options=synthesized_options,
                    help="픽셀 아트 합성에서 생성한 이미지를 사용할 수 있습니다."
                )
                
                if selected_synthesized and not uploaded_file:
                    # 업로드된 파일이 없을 때만 합성 이미지 사용
                    idx = synthesized_options.index(selected_synthesized)
                    selected_image = st.session_state.synthesized_images[idx]['image']
                    selected_image_name = st.session_state.synthesized_images[idx]['filename']
                    selected_image_info = st.session_state.synthesized_images[idx]
                    
                    # 합성된 이미지 미리보기
                    st.image(selected_image, caption=selected_image_name, use_container_width=True)
                    
        else:
            # 합성된 이미지가 없을 때: 이미지 업로드만
            st.subheader("📁 이미지 업로드")
            
            uploaded_file = st.file_uploader(
                "동영상으로 변환할 이미지를 선택하세요",
                type=['jpg', 'jpeg', 'png', 'bmp', 'webp'],
                key="image_video"
            )
            
            if uploaded_file:
                selected_image = Image.open(uploaded_file)
                selected_image_name = uploaded_file.name
                st.image(selected_image, caption=selected_image_name, use_container_width=True)
        
        if selected_image:
            self._handle_video_generation(selected_image, selected_image_name, layout_factory)
    
    def _handle_video_generation(self, image: Image.Image, image_name: str, layout_factory) -> None:
        """동영상 생성 처리"""
        # 이미지가 이미 PIL Image 객체이므로 직접 사용
        image = ImageUtils.resize_image_if_needed(image, 1024)
        
        # 이미지 정보만 표시 (이미지는 위에서 이미 표시됨)
        st.divider()

        # 동영상 설정
        st.subheader("⚙️ 동영상 설정")
        
        # 설정용 3열 레이아웃
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # YAML 프롬프트 스타일 선택
            available_prompts = self.prompt_manager.get_video_prompt_list()
            
            selected_prompt_key = st.selectbox(
                "동영상 스타일",
                options=available_prompts,
                help="YAML 파일에서 로드되는 프롬프트 스타일을 선택하세요"
            )
        
        with col2:
            # 동영상 길이
            duration = st.slider("동영상 길이 (초)", 3, 6, 3)
            
            # 해상도 선택
            video_generator = BytePlusVideoGenerator()
            resolutions = video_generator.get_supported_resolutions()

        
        with col3:
            resolution = st.selectbox(
                "해상도",
                options=resolutions,
                format_func=lambda x: {
                    "480p": "480p (9:16 세로)",
                }.get(x, x)
            )
        
        # 선택된 프롬프트 가져오기
        final_prompt = self.prompt_manager.get_video_prompt_content(selected_prompt_key)
        
        # 동영상 생성 버튼
        st.divider()
        col_center = st.columns([1, 2, 1])[1]
        with col_center:
            if st.button("🎬 동영상 생성 시작", type="primary", use_container_width=True):
                self._process_video_generation(image, final_prompt, duration, resolution)
    
    def _process_video_generation(self, image: Image.Image, prompt: str, duration: int, resolution: str) -> None:
        """동영상 생성 처리"""
        try:
            VideoUtils.create_video_directories()
            
            # 동영상 생성 시작 시간 기록
            start_time = time.time()
            
            # 단일 progress bar와 status 텍스트
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            video_generator = BytePlusVideoGenerator()
            
            # 1단계: 작업 생성
            status_text.info("🎬 동영상 생성 작업 시작...")
            progress_bar.progress(20)
            
            task_id = video_generator.create_video_task(image, prompt, duration, resolution=resolution)
            
            if not task_id:
                status_text.error("❌ 동영상 생성 작업 생성에 실패했습니다.")
                return
            
            # 2단계: 동영상 생성 대기
            status_text.info("🎬 동영상 생성 중... (시간이 걸릴 수 있습니다)")
            progress_bar.progress(40)
            
            task_result = video_generator.wait_for_completion(task_id, max_wait_time=90)
            
            if not task_result:
                status_text.error("❌ 동영상 생성에 실패했거나 시간이 초과되었습니다.")
                return
            
            # 3단계: URL 추출
            status_text.info("🎬 생성된 동영상 다운로드 중...")
            progress_bar.progress(70)
            
            # BytePlusVideoGenerator의 _extract_video_url 메서드 사용
            video_url = video_generator._extract_video_url(task_result)
            if not video_url:
                status_text.error("❌ 생성된 동영상 URL을 찾을 수 없습니다.")
                return
            
            video_path = VideoUtils.get_video_save_path()
            
            # 4단계: 다운로드
            status_text.info("🎬 동영상 저장 중...")
            progress_bar.progress(90)
            
            if video_generator.download_video(video_url, video_path):
                # 5단계: 완료 - 생성 시간 계산
                end_time = time.time()
                generation_time = end_time - start_time
                status_text.success("🎉 동영상 생성 완료!")
                progress_bar.progress(100)
                
                # 결과 표시
                st.subheader("🎉 동영상 생성 완료")
                
                with open(video_path, 'rb') as video_file:
                    video_bytes = video_file.read()
                
                st.video(video_bytes)
                
                # 동영상 정보 3열 레이아웃으로 표시
                st.subheader("📊 생성된 동영상 정보")
                col1, col2, col3 = st.columns(3)
                
                # 파일 크기 계산
                file_size_bytes = len(video_bytes)
                file_size_mb = file_size_bytes / (1024 * 1024)
                
                # 생성 시간 포맷팅
                if generation_time < 60:
                    time_str = f"{generation_time:.1f}초"
                else:
                    minutes = int(generation_time // 60)
                    seconds = generation_time % 60
                    time_str = f"{minutes}분 {seconds:.1f}초"
                
                with col1:
                    st.metric(
                        label="📦 파일 크기",
                        value=f"{file_size_mb:.2f} MB"
                    )
                
                with col2:
                    st.metric(
                        label="🎬 형식",
                        value="MP4"
                    )
                
                with col3:
                    st.metric(
                        label="⏱️ 생성 시간",
                        value=time_str
                    )
                
                st.download_button(
                    label="📥 동영상 다운로드",
                    data=video_bytes,
                    file_name=f"generated_video_{int(time.time())}.mp4",
                    mime="video/mp4",
                    type="secondary",
                    use_container_width=True
                )
                
                VideoUtils.cleanup_old_videos()
            else:
                st.error("❌ 동영상 다운로드에 실패했습니다.")
                
        except Exception as e:
            st.error(f"❌ 동영상 생성 중 오류가 발생했습니다: {str(e)}")
            st.info("네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요.")
        
        finally:
            # 성공 시에는 progress bar와 status를 유지
            pass


# 페이지 인스턴스 생성 (라우터가 자동으로 발견)
page = VideoGeneratorPage()