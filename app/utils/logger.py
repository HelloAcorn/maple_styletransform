"""
로깅 설정 유틸리티
"""
import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(name: str, level=logging.INFO) -> logging.Logger:
    """
    로거 설정 함수
    
    Args:
        name: 로거 이름
        level: 로그 레벨
        
    Returns:
        logging.Logger: 설정된 로거
    """
    # logs 디렉토리 생성
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # 로거 생성
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 있으면 중복 생성 방지
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 파일 핸들러 설정 (회전 로그)
    log_filename = os.path.join(logs_dir, f"{name}.log")
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # 콘솔에는 WARNING 이상만 출력
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def log_function_call(logger: logging.Logger, func_name: str, **kwargs):
    """
    함수 호출 로그 기록
    
    Args:
        logger: 로거 인스턴스
        func_name: 함수명
        **kwargs: 함수 파라미터들
    """
    params = ", ".join([f"{k}={v}" for k, v in kwargs.items() if v is not None])
    logger.info(f"함수 호출: {func_name}({params})")


def log_api_request(logger: logging.Logger, api_name: str, endpoint: str, status: str):
    """
    API 요청 로그 기록
    
    Args:
        logger: 로거 인스턴스
        api_name: API 이름
        endpoint: 엔드포인트
        status: 요청 상태
    """
    logger.info(f"API 요청: {api_name} - {endpoint} - 상태: {status}")


def log_error(logger: logging.Logger, error: Exception, context: str = ""):
    """
    에러 로그 기록
    
    Args:
        logger: 로거 인스턴스
        error: 예외 객체
        context: 에러 발생 컨텍스트
    """
    error_msg = f"에러 발생: {str(error)}"
    if context:
        error_msg = f"{context} - {error_msg}"
    
    logger.error(error_msg, exc_info=True)
