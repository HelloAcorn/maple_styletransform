"""
이미지 합성 Streamlit 애플리케이션
Gemini 2.0 Flash Image 모델을 사용하여 두 이미지를 하나로 합성
"""
import os
import sys
import time
import streamlit as st
from PIL import Image
from dotenv import load_dotenv
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app.modules.gemini_integration import GeminiImageProcessor
from app.modules.image_utils import ImageUtils, display_image_info
from app.modules.byteplus_integration import BytePlusVideoGenerator
from app.modules.video_utils import (VideoUtils, display_video_info, 
                                   display_video_generation_progress,
                                   create_video_generation_prompt_templates)
from app.core.config import APIConfig
from app.utils.logger import setup_logger, log_function_call, log_error

# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="AI 이미지 합성기",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #FF6B6B;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .sub-header {
        text-align: center;
        color: #4ECDC4;
        font-size: 1.2rem;
        margin-bottom: 3rem;
    }
    .upload-section {
        background-color: #f0f2f6;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .result-section {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 10px;
        border: 2px solid #4ECDC4;
        margin: 2rem 0;
    }
    .stButton > button {
        background-color: #FF6B6B;
        color: white;
        border: none;
        border-radius: 20px;
        padding: 0.5rem 2rem;
        font-size: 1.1rem;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background-color: #FF5252;
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """세션 상태 초기화"""
    if 'processed_images' not in st.session_state:
        st.session_state.processed_images = []
    if 'api_key_valid' not in st.session_state:
        st.session_state.api_key_valid = False

def validate_api_key(api_key: str) -> bool:
    """API 키 유효성 검사"""
    if not api_key or len(api_key) < 10:
        return False
    return True

def main():
    """메인 애플리케이션"""
    logger = setup_logger('streamlit_app')
    logger.info("AI 멀티미디어 스튜디오 애플리케이션 시작")
    
    initialize_session_state()
    
    # 헤더
    st.markdown('<h1 class="main-header">🎨 AI 멀티미디어 스튜디오</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI 기반 이미지 합성 & 동영상 생성</p>', unsafe_allow_html=True)
    
    # 사이드바 설정
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # API 키 입력
        st.subheader("🔑 API 설정")
        
        # Gemini API 키
        gemini_api_key = st.text_input(
            "Gemini API 키",
            type="default",
            help="Google AI Studio에서 발급받은 API 키를 입력하세요",
            placeholder="AIza..."
        )
        
        if gemini_api_key:
            if validate_api_key(gemini_api_key):
                st.session_state.api_key_valid = True
                APIConfig.set_gemini_api_key(gemini_api_key)
                st.success("✅ Gemini API 키가 설정되었습니다")
            else:
                st.session_state.api_key_valid = False
                st.error("❌ 유효하지 않은 Gemini API 키입니다")
        
        # BytePlus API 키 상태 표시
        st.info("🎬 BytePlus API: 설정 완료 (동영상 생성 지원)")
        
        st.divider()
        
        # 애플리케이션 정보
        st.subheader("📊 애플리케이션 정보")
        st.info("🎨 **이미지 합성**: Gemini 2.0 Flash")
        st.info("🎬 **동영상 생성**: BytePlus Seedance 1.0")
        
        st.divider()
        
        # 처리 기록
        if st.session_state.processed_images:
            st.subheader("📝 처리 기록")
            st.write(f"총 {len(st.session_state.processed_images)}개의 이미지를 처리했습니다.")
            if st.button("기록 초기화"):
                st.session_state.processed_images = []
                st.rerun()
    
    # 메인 탭 생성
    tab1, tab2 = st.tabs(["🎨 이미지 합성", "🎬 동영상 생성"])
    
    with tab1:
        image_synthesis_tab(gemini_api_key if 'gemini_api_key' in locals() else None)
    
    with tab2:
        video_generation_tab()

def image_synthesis_tab(api_key: str):
    """이미지 합성 탭"""
    if not api_key or not validate_api_key(api_key):
        st.warning("⚠️ 먼저 사이드바에서 Gemini API 키를 입력해주세요.")
        st.info("""
        **API 키 발급 방법:**
        1. [Google AI Studio](https://aistudio.google.com/)에 접속
        2. 'Get API Key' 클릭
        3. 새 프로젝트 생성 또는 기존 프로젝트 선택
        4. API 키 복사 후 사이드바에 입력
        """)
        return
    # 사이드바에서 설정값 가져오기
    style_options = {
        "natural": "🌿 자연스러운 합성",
        "artistic": "🎨 예술적 합성", 
        "seamless": "✨완전한 융합",
        "collage": "🖼️ 콜라주 스타일"
    }
    
    # 이미지 업로드 섹션
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("📁 이미지 업로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**첫 번째 이미지**")
        uploaded_file1 = st.file_uploader(
            "첫 번째 이미지를 선택하세요",
            type=['jpg', 'jpeg', 'png', 'bmp', 'webp'],
            key="image1_synthesis"
        )
    
    with col2:
        st.write("**두 번째 이미지**")
        uploaded_file2 = st.file_uploader(
            "두 번째 이미지를 선택하세요", 
            type=['jpg', 'jpeg', 'png', 'bmp', 'webp'],
            key="image2_synthesis"
        )
    
    # 합성 스타일 선택
    selected_style = st.selectbox(
        "합성 스타일 선택",
        options=list(style_options.keys()),
        format_func=lambda x: style_options[x]
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 업로드된 이미지 미리보기
    if uploaded_file1 or uploaded_file2:
        st.subheader("🖼️ 업로드된 이미지 미리보기")
        
        preview_col1, preview_col2 = st.columns(2)
        
        image1, image2 = None, None
        
        with preview_col1:
            if uploaded_file1:
                if ImageUtils.validate_image_file(uploaded_file1):
                    image1 = Image.open(uploaded_file1)
                    image1 = ImageUtils.resize_image_if_needed(image1, 1024)
                    st.image(image1, caption="첫 번째 이미지", use_column_width=True)
                    display_image_info(image1, "이미지 1 정보")
                else:
                    st.error("❌ 유효하지 않은 이미지 파일입니다.")
        
        with preview_col2:
            if uploaded_file2:
                if ImageUtils.validate_image_file(uploaded_file2):
                    image2 = Image.open(uploaded_file2)
                    image2 = ImageUtils.resize_image_if_needed(image2, 1024)
                    st.image(image2, caption="두 번째 이미지", use_column_width=True)
                    display_image_info(image2, "이미지 2 정보")
                else:
                    st.error("❌ 유효하지 않은 이미지 파일입니다.")
        
        # 이미지 합성 버튼
        if image1 and image2:
            st.divider()
            
            col_center = st.columns([1, 2, 1])[1]
            with col_center:
                if st.button("🚀 이미지 합성 시작", type="primary", use_container_width=True):
                    process_images(image1, image2, api_key, selected_style)

def video_generation_tab():
    """동영상 생성 탭"""
    st.subheader("🎬 이미지에서 동영상 생성")
    st.info("BytePlus ModelArk Seedance 1.0 모델을 사용하여 이미지를 동영상으로 변환합니다.")
    
    # 이미지 업로드 섹션
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("📁 이미지 업로드")
    
    uploaded_file = st.file_uploader(
        "동영상으로 변환할 이미지를 선택하세요",
        type=['jpg', 'jpeg', 'png', 'bmp', 'webp'],
        key="image_video"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if uploaded_file:
        if ImageUtils.validate_image_file(uploaded_file):
            # 이미지 미리보기
            image = Image.open(uploaded_file)
            image = ImageUtils.resize_image_if_needed(image, 1024)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.image(image, caption="업로드된 이미지", use_column_width=True)
            
            with col2:
                display_image_info(image, "이미지 정보")
            
            # 동영상 설정
            st.divider()
            st.subheader("⚙️ 동영상 설정")
            
            col_settings1, col_settings2 = st.columns(2)
            
            with col_settings1:
                # 프롬프트 템플릿 선택
                prompt_templates = create_video_generation_prompt_templates()
                prompt_style = st.selectbox(
                    "동영상 스타일",
                    options=list(prompt_templates.keys()),
                    format_func=lambda x: {
                        "natural": "🌿 자연스러운",
                        "cinematic": "🎬 영화적",
                        "smooth": "✨ 부드러운",
                        "dynamic": "⚡ 역동적",
                        "artistic": "🎨 예술적",
                        "realistic": "📷 현실적"
                    }.get(x, x)
                )
                
                # 동영상 길이
                duration = st.slider("동영상 길이 (초)", 2, 10, 4)
            
            with col_settings2:
                # 해상도 선택
                video_generator = BytePlusVideoGenerator()
                resolutions = video_generator.get_supported_resolutions()
                resolution = st.selectbox(
                    "해상도",
                    options=resolutions,
                    format_func=lambda x: {
                        "1024x576": "1024×576 (16:9 가로)",
                        "576x1024": "576×1024 (9:16 세로)",
                        "768x768": "768×768 (1:1 정사각형)",
                        "1280x720": "1280×720 (HD 가로)",
                        "720x1280": "720×1280 (HD 세로)"
                    }.get(x, x)
                )
                
                # 사용자 정의 프롬프트
                custom_prompt = st.text_area(
                    "사용자 정의 프롬프트 (선택사항)",
                    placeholder="원하는 동영상 스타일이나 움직임을 설명해주세요...",
                    height=80
                )
            
            # 최종 프롬프트 결정
            final_prompt = custom_prompt if custom_prompt.strip() else prompt_templates[prompt_style]
            
            # 동영상 생성 버튼
            st.divider()
            col_center = st.columns([1, 2, 1])[1]
            with col_center:
                if st.button("🎬 동영상 생성 시작", type="primary", use_container_width=True):
                    process_video_generation(image, final_prompt, duration, resolution)
        else:
            st.error("❌ 유효하지 않은 이미지 파일입니다.")

def process_video_generation(image: Image.Image, prompt: str, duration: int, resolution: str):
    """동영상 생성 처리"""
    try:
        # 필요한 디렉토리 생성
        VideoUtils.create_video_directories()
        
        # 진행 상황 표시
        progress_container = st.container()
        status_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
        
        with status_container:
            status_text = st.empty()
        
        # BytePlus 동영상 생성기 초기화
        video_generator = BytePlusVideoGenerator()
        
        display_video_generation_progress(1, 5, "동영상 생성 작업 시작...")
        progress_bar.progress(20)
        
        # 동영상 생성 작업 생성
        task_id = video_generator.create_video_task(image, prompt, duration, resolution=resolution)
        
        if not task_id:
            st.error("❌ 동영상 생성 작업 생성에 실패했습니다.")
            return
        
        display_video_generation_progress(2, 5, "동영상 생성 중... (시간이 걸릴 수 있습니다)")
        progress_bar.progress(40)
        
        # 작업 완료 대기
        task_result = video_generator.wait_for_completion(task_id, max_wait_time=300)
        
        if not task_result:
            st.error("❌ 동영상 생성에 실패했거나 시간이 초과되었습니다.")
            return
        
        display_video_generation_progress(3, 5, "생성된 동영상 다운로드 중...")
        progress_bar.progress(60)
        
        # 동영상 URL 추출
        video_url = task_result.get("video_url")
        if not video_url:
            st.error("❌ 생성된 동영상 URL을 찾을 수 없습니다.")
            return
        
        # 동영상 다운로드
        video_path = VideoUtils.get_video_save_path()
        
        display_video_generation_progress(4, 5, "동영상 저장 중...")
        progress_bar.progress(80)
        
        if video_generator.download_video(video_url, video_path):
            display_video_generation_progress(5, 5, "동영상 생성 완료!")
            progress_bar.progress(100)
            
            # 결과 표시
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.subheader("🎉 동영상 생성 완료")
            
            # 동영상 재생
            with open(video_path, 'rb') as video_file:
                video_bytes = video_file.read()
            
            st.video(video_bytes)
            
            # 동영상 정보 표시
            display_video_info(video_path, "생성된 동영상 정보")
            
            # 다운로드 버튼
            st.download_button(
                label="📥 동영상 다운로드",
                data=video_bytes,
                file_name=f"generated_video_{int(time.time())}.mp4",
                mime="video/mp4",
                type="secondary"
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 오래된 파일 정리
            VideoUtils.cleanup_old_videos()
            
        else:
            st.error("❌ 동영상 다운로드에 실패했습니다.")
            
    except Exception as e:
        st.error(f"❌ 동영상 생성 중 오류가 발생했습니다: {str(e)}")
        st.info("네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요.")
    
    finally:
        # 진행 상황 표시 정리
        if 'progress_bar' in locals():
            progress_bar.empty()
        if 'status_text' in locals():
            status_text.empty()

def process_images(image1: Image.Image, image2: Image.Image, api_key: str, style: str):
    """이미지 처리 및 합성"""
    
    # 필요한 디렉토리 생성
    ImageUtils.create_directories()
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔧 Gemini AI 모델 초기화 중...")
        progress_bar.progress(20)
        
        # Gemini 프로세서 초기화
        processor = GeminiImageProcessor(api_key)
        
        status_text.text("🎨 이미지 합성 중... (시간이 다소 걸릴 수 있습니다)")
        progress_bar.progress(40)
        
        # 이미지 합성
        merged_image = processor.create_artistic_merge(image1, image2, style)
        progress_bar.progress(80)
        
        if merged_image:
            status_text.text("💾 결과 저장 중...")
            
            # 결과 이미지 저장
            saved_path = ImageUtils.save_pil_image(merged_image)
            progress_bar.progress(100)
            
            status_text.text("✅ 이미지 합성 완료!")
            
            # 결과 표시
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.subheader("🎉 합성 결과")
            
            # 결과 이미지 표시
            st.image(merged_image, caption="합성된 이미지", use_column_width=True)
            
            # 결과 정보
            display_image_info(merged_image, "합성 결과 정보")
            
            # 다운로드 버튼
            import io
            img_byte_arr = io.BytesIO()
            merged_image.save(img_byte_arr, format='PNG', quality=95)
            img_byte_arr = img_byte_arr.getvalue()
            
            st.download_button(
                label="📥 결과 이미지 다운로드",
                data=img_byte_arr,
                file_name=f"merged_image_{style}.png",
                mime="image/png",
                type="secondary"
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 처리 기록에 추가
            st.session_state.processed_images.append({
                'style': style,
                'path': saved_path,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # 오래된 파일 정리
            ImageUtils.cleanup_old_files("app/static/uploads")
            ImageUtils.cleanup_old_files("app/static/merged_images")
            
        else:
            st.error("❌ 이미지 합성에 실패했습니다. API 키를 확인하거나 다른 이미지로 시도해보세요.")
            
    except Exception as e:
        st.error(f"❌ 오류가 발생했습니다: {str(e)}")
        st.info("API 키가 올바른지, 인터넷 연결이 안정적인지 확인해주세요.")
    
    finally:
        progress_bar.empty()
        status_text.empty()

if __name__ == "__main__":
    main()
