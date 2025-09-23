"""
AI 멀티미디어 스튜디오 - 메인 애플리케이션
라우터와 레이아웃 시스템을 사용하는 새로운 구조
"""
import os
import sys
import streamlit as st
from dotenv import load_dotenv

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.core.router import Router
from app.core.context import get_or_create_context
from app.core.config import APIConfig
from app.utils.logger import setup_logger

# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="AI 멀티미디어 스튜디오",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed"
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
    if 'router_initialized' not in st.session_state:
        st.session_state.router_initialized = False




def main():
    """메인 애플리케이션"""
    logger = setup_logger('main')
    
    # API 키 파일에서 로드
    APIConfig.load_api_keys()
    
    # 세션 상태 초기화
    initialize_session_state()
    
    # 헤더
    st.markdown('<h1 class="main-header">🎨 AI 멀티미디어 스튜디오</h1>', unsafe_allow_html=True)
    
    # 컨텍스트 생성/가져오기
    ctx = get_or_create_context()
    
    # 라우터 초기화 (세션당 한 번만)
    if not st.session_state.router_initialized:
        st.session_state.router = Router()
        st.session_state.router.load_pages("app.pages")
        st.session_state.router_initialized = True
        pass  # 라우터 초기화 완룜
    
    # 라우터를 통해 탭 렌더링
    router = st.session_state.router
    router.render_tabs(ctx.to_dict())


if __name__ == "__main__":
    main()