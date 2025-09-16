"""
통합 로깅 시스템
터미널 출력 + 단일 streamlit.log 파일 관리
"""
import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


# 전역 로거 인스턴스 (싱글톤 패턴)
_streamlit_logger: Optional[logging.Logger] = None


def setup_logger(name: str, level=logging.INFO) -> logging.Logger:
    """
    통합 로거 설정 함수
    모든 로그를 streamlit.log 파일 하나로 관리하고 터미널에도 출력
    
    Args:
        name: 로거 이름 (컴포넌트 구분용)
        level: 로그 레벨
        
    Returns:
        logging.Logger: 설정된 로거
    """
    global _streamlit_logger
    
    # 싱글톤: 이미 생성된 로거가 있으면 반환
    if _streamlit_logger is not None:
        return _streamlit_logger.getChild(name)
    
    # logs 디렉토리 생성
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # 메인 로거 생성
    _streamlit_logger = logging.getLogger('streamlit_app')
    _streamlit_logger.setLevel(level)
    
    # 중복 핸들러 방지
    if _streamlit_logger.handlers:
        return _streamlit_logger.getChild(name)
    
    # 포맷터 설정
    # 터미널용: 간단한 포맷
    console_formatter = logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 파일용: 상세한 포맷
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 파일 핸들러 설정 (단일 streamlit.log 파일)
    log_filename = os.path.join(logs_dir, "streamlit.log")
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=50*1024*1024,  # 50MB (더 큰 용량)
        backupCount=3,          # 백업 파일 3개
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)
    
    # 콘솔 핸들러 설정 (모든 레벨 출력)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)  # INFO 이상 모든 로그 터미널 출력
    console_handler.setFormatter(console_formatter)
    
    # 핸들러 추가
    _streamlit_logger.addHandler(file_handler)
    _streamlit_logger.addHandler(console_handler)
    
    # 초기 로그 메시지
    _streamlit_logger.info("=" * 60)
    _streamlit_logger.info(f"AI 멀티미디어 스튜디오 로깅 시스템 시작")
    _streamlit_logger.info(f"로그 파일: {log_filename}")
    _streamlit_logger.info("=" * 60)
    
    # 컴포넌트별 자식 로거 반환
    return _streamlit_logger.getChild(name)


def get_main_logger() -> logging.Logger:
    """메인 로거 인스턴스 반환"""
    if _streamlit_logger is None:
        return setup_logger('main')
    return _streamlit_logger


def log_function_call(logger: logging.Logger, func_name: str, **kwargs):
    """
    함수 호출 로그 기록
    
    Args:
        logger: 로거 인스턴스
        func_name: 함수명
        **kwargs: 함수 파라미터들
    """
    params = ", ".join([f"{k}={v}" for k, v in kwargs.items() if v is not None])
    logger.debug(f"🔧 함수 호출: {func_name}({params})")


def log_api_request(logger: logging.Logger, api_name: str, endpoint: str, status: str):
    """
    API 요청 로그 기록
    
    Args:
        logger: 로거 인스턴스
        api_name: API 이름
        endpoint: 엔드포인트
        status: 요청 상태
    """
    logger.info(f"🌐 API 요청: {api_name} - {endpoint} - 상태: {status}")


def log_error(logger: logging.Logger, error: Exception, context: str = ""):
    """
    에러 로그 기록
    
    Args:
        logger: 로거 인스턴스
        error: 예외 객체
        context: 에러 발생 컨텍스트
    """
    error_msg = f"❌ 에러 발생: {str(error)}"
    if context:
        error_msg = f"{context} - {error_msg}"
    
    logger.error(error_msg, exc_info=True)


def log_page_access(logger: logging.Logger, page_name: str, user_action: str = "access"):
    """
    페이지 접근 로그 기록
    
    Args:
        logger: 로거 인스턴스
        page_name: 페이지 이름
        user_action: 사용자 액션
    """
    logger.info(f"📄 페이지 {user_action}: {page_name}")


def log_system_info(logger: logging.Logger, info_type: str, message: str):
    """
    시스템 정보 로그 기록
    
    Args:
        logger: 로거 인스턴스
        info_type: 정보 타입 (startup, shutdown, config 등)
        message: 메시지
    """
    logger.info(f"⚙️  {info_type.upper()}: {message}")


def cleanup_old_logs(days: int = 7):
    """
    오래된 로그 파일 정리
    
    Args:
        days: 보관할 일수
    """
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        return
    
    import time
    current_time = time.time()
    cutoff_time = current_time - (days * 24 * 60 * 60)
    
    for filename in os.listdir(logs_dir):
        file_path = os.path.join(logs_dir, filename)
        if os.path.isfile(file_path):
            file_time = os.path.getctime(file_path)
            if file_time < cutoff_time:
                try:
                    os.remove(file_path)
                    print(f"오래된 로그 파일 삭제: {filename}")
                except Exception as e:
                    print(f"로그 파일 삭제 실패 {filename}: {e}")


# 편의 함수들
def info(message: str, component: str = "main"):
    """정보 로그 출력"""
    logger = setup_logger(component)
    logger.info(message)


def error(message: str, component: str = "main", exc_info: bool = False):
    """에러 로그 출력"""
    logger = setup_logger(component)
    logger.error(message, exc_info=exc_info)


def warning(message: str, component: str = "main"):
    """경고 로그 출력"""
    logger = setup_logger(component)
    logger.warning(message)


def debug(message: str, component: str = "main"):
    """디버그 로그 출력"""
    logger = setup_logger(component)
    logger.debug(message)