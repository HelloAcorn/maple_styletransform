"""
애플리케이션 컨텍스트 관리
페이지에 필요한 모든 의존성과 상태를 중앙에서 관리
"""
import streamlit as st
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from app.core.layout import LayoutFactory
from app.core.config import APIConfig
from app.utils.logger import setup_logger


@dataclass
class AppContext:
    """애플리케이션 컨텍스트"""
    
    # 세션 상태
    session: Any = field(default_factory=lambda: st.session_state)
    
    # API 키
    api_key: Optional[str] = None
    
    # 레이아웃 팩토리
    layout_factory: LayoutFactory = field(default_factory=LayoutFactory)
    
    # 서비스들 (필요시 추가)
    services: Dict[str, Any] = field(default_factory=dict)
    
    # 설정
    config: Dict[str, Any] = field(default_factory=dict)
    
    # 로거
    logger: Any = field(default_factory=lambda: setup_logger('app_context'))
    
    def create_layout(self, kind: str = "two_col", **kwargs):
        """레이아웃 생성 헬퍼"""
        return self.layout_factory.create(kind, **kwargs)
    
    def get_service(self, name: str) -> Any:
        """서비스 가져오기"""
        return self.services.get(name)
    
    def set_service(self, name: str, service: Any) -> None:
        """서비스 등록"""
        self.services[name] = service
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (기존 코드 호환성)"""
        return {
            "session": self.session,
            "api_key": self.api_key,
            "layout_factory": self.layout_factory,
            "services": self.services,
            "config": self.config,
            "logger": self.logger
        }


def make_context() -> AppContext:
    """
    애플리케이션 컨텍스트 생성
        
    Returns:
        AppContext 인스턴스
    """
    logger = setup_logger('context')
    logger.info("컨텍스트 생성 시작")
    
    # 컨텍스트 생성 (API 키는 각 페이지에서 직접 로드)
    ctx = AppContext(
        api_key=None,  # 더 이상 사용하지 않음
        config={
            "app_name": "AI 멀티미디어 스튜디오",
            "version": "2.0",
            "theme": "default"
        }
    )
    
    # 필요한 서비스들 초기화 (lazy loading 가능)
    # ctx.set_service("image_processor", ImageProcessor())
    # ctx.set_service("video_generator", VideoGenerator())
    
    logger.info("컨텍스트 생성 완료")
    return ctx


def get_or_create_context() -> AppContext:
    """
    세션에서 컨텍스트를 가져오거나 새로 생성
    Streamlit의 rerun 시에도 컨텍스트 유지
    """
    if 'app_context' not in st.session_state:
        st.session_state.app_context = make_context()
    
    return st.session_state.app_context
