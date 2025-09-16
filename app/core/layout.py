"""
레이아웃 추상화 시스템
페이지와 레이아웃 결합도를 제거하는 슬롯 기반 레이아웃
"""
import streamlit as st
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager


class Layout:
    """레이아웃 추상화 클래스"""
    
    def __init__(self, kind: str = "two_col", ratios: Optional[List[int]] = None):
        """
        레이아웃 초기화
        
        Args:
            kind: 레이아웃 종류 ("two_col", "three_col", "single", "sidebar_main")
            ratios: 컬럼 비율 (예: [2, 1] for 2:1 ratio)
        """
        self.kind = kind
        self.slots: Dict[str, Any] = {}
        
        if kind == "single":
            # 단일 컬럼
            self.slots["main"] = st.container()
            
        elif kind == "two_col":
            # 2열 레이아웃
            ratios = ratios or [2, 1]
            left, right = st.columns(ratios)
            self.slots["left"] = left
            self.slots["right"] = right
            self.slots["main"] = left  # alias
            self.slots["side"] = right  # alias
            
        elif kind == "three_col":
            # 3열 레이아웃
            ratios = ratios or [1, 2, 1]
            left, center, right = st.columns(ratios)
            self.slots["left"] = left
            self.slots["center"] = center
            self.slots["right"] = right
            self.slots["main"] = center  # alias
            
        elif kind == "sidebar_main":
            # 사이드바 + 메인
            self.slots["sidebar"] = st.sidebar
            self.slots["main"] = st.container()
            
        else:
            # 기본값: 단일 컨테이너
            self.slots["main"] = st.container()
    
    def slot(self, name: str) -> Any:
        """
        슬롯 가져오기
        
        Args:
            name: 슬롯 이름
            
        Returns:
            Streamlit 컨테이너 또는 컬럼
        """
        return self.slots.get(name, st.container())
    
    @contextmanager
    def use_slot(self, name: str):
        """
        슬롯을 컨텍스트 매니저로 사용
        
        Example:
            with layout.use_slot("main"):
                st.write("Hello")
        """
        with self.slot(name):
            yield
    
    def get_available_slots(self) -> List[str]:
        """사용 가능한 슬롯 이름 리스트"""
        return list(self.slots.keys())


class ResponsiveLayout:
    """반응형 레이아웃 (확장 가능)"""
    
    @staticmethod
    def create(breakpoint: int = 768) -> Layout:
        """
        화면 크기에 따른 레이아웃 생성
        (Streamlit은 아직 미디어 쿼리를 지원하지 않지만, 향후 확장 가능)
        """
        # 현재는 기본 레이아웃 반환
        return Layout("two_col")


class LayoutFactory:
    """레이아웃 팩토리"""
    
    @staticmethod
    def create(
        kind: str = "two_col",
        ratios: Optional[List[int]] = None,
        **kwargs
    ) -> Layout:
        """
        레이아웃 생성
        
        Args:
            kind: 레이아웃 종류
            ratios: 컬럼 비율
            **kwargs: 추가 옵션
            
        Returns:
            Layout 인스턴스
        """
        return Layout(kind, ratios)
    
    @staticmethod
    def create_two_column(left_ratio: int = 2, right_ratio: int = 1) -> Layout:
        """2열 레이아웃 생성"""
        return Layout("two_col", [left_ratio, right_ratio])
    
    @staticmethod
    def create_three_column(
        left_ratio: int = 1,
        center_ratio: int = 2,
        right_ratio: int = 1
    ) -> Layout:
        """3열 레이아웃 생성"""
        return Layout("three_col", [left_ratio, center_ratio, right_ratio])
    
    @staticmethod
    def create_single_column() -> Layout:
        """단일 컬럼 레이아웃 생성"""
        return Layout("single")
