"""
페이지 라우터 시스템
파일시스템 기반 자동 페이지 발견 및 등록
"""
import importlib
import pkgutil
from dataclasses import dataclass
from typing import List, Protocol, Optional, Dict, Any
from pathlib import Path
import streamlit as st

from app.utils.logger import setup_logger


@dataclass
class PageSpec:
    """페이지 메타데이터"""
    name: str
    icon: str = "📄"
    order: int = 100
    requires_api_key: bool = False
    
    @property
    def display_name(self) -> str:
        """탭에 표시될 이름"""
        return f"{self.icon} {self.name}".strip()


class PageProtocol(Protocol):
    """페이지 인터페이스"""
    spec: PageSpec
    
    def render(self, ctx: Dict[str, Any]) -> None:
        """페이지 렌더링"""
        ...


def discover_pages(package_name: str = "app.pages") -> List[PageProtocol]:
    """
    pages 패키지에서 자동으로 페이지를 발견하고 로드
    
    Args:
        package_name: 페이지가 있는 패키지 이름
        
    Returns:
        발견된 페이지 인스턴스 리스트 (order 순으로 정렬)
    """
    logger = setup_logger('router')
    pages: List[PageProtocol] = []
    
    try:
        # 패키지 import
        package = importlib.import_module(package_name)
        package_path = Path(package.__file__).parent
        
        # 모든 모듈 순회
        modules_found = []
        for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
            modules_found.append(module_name)
            if module_name.startswith('_'):
                logger.debug(f"언더스코어로 시작하는 모듈 건너뜀: {module_name}")
                continue
            
            try:
                # 모듈 import
                full_module_name = f"{package_name}.{module_name}"
                module = importlib.import_module(full_module_name)
                
                # page 인스턴스 찾기
                if hasattr(module, 'page'):
                    page = module.page
                    pages.append(page)
                    logger.info(f"페이지 로드 성공: {page.spec.name} from {module_name}")
                else:
                    logger.warning(f"'page' 인스턴스 없음: {module_name}")
                    
            except Exception as e:
                logger.error(f"모듈 로드 실패 {module_name}: {e}")
        
    except ImportError as e:
        logger.error(f"패키지 import 실패 {package_name}: {e}")
        import traceback
        logger.error(f"스택 트레이스: {traceback.format_exc()}")
    
    # order 순으로 정렬
    pages.sort(key=lambda p: (p.spec.order, p.spec.name))
    
    logger.info(f"총 {len(pages)}개 페이지 발견")
    return pages


class Router:
    """메인 라우터 클래스"""
    
    def __init__(self):
        self.logger = setup_logger('router')
        self.pages: List[PageProtocol] = []
    
    def load_pages(self, package_name: str = "app.pages") -> None:
        """페이지 로드"""
        self.pages = discover_pages(package_name)
    
    def render_tabs(self, ctx: Dict[str, Any]) -> None:
        """탭 형태로 페이지 렌더링"""
        if not self.pages:
            st.warning("로드된 페이지가 없습니다.")
            return
        
        # 탭 생성
        tab_names = [p.spec.display_name for p in self.pages]
        tabs = st.tabs(tab_names)
        
        # 각 탭에 페이지 렌더링
        for tab, page in zip(tabs, self.pages):
            with tab:
                page.render(ctx)
