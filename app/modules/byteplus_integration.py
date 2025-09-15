"""
BytePlus ModelArk Seedance 1.0 모델을 사용한 이미지-동영상 변환 모듈
"""
import os
import io
import time
import base64
import requests
from typing import Optional, Dict, Any, Union
from PIL import Image
import json

from app.core.config import APIConfig
from app.utils.logger import setup_logger, log_function_call, log_api_request, log_error


class BytePlusVideoGenerator:
    """BytePlus ModelArk Seedance 1.0을 사용한 동영상 생성 클래스"""
    
    def __init__(self):
        """
        BytePlus API 클라이언트 초기화
        """
        self.logger = setup_logger('byteplus_integration')
        
        log_function_call(self.logger, "BytePlusVideoGenerator.__init__")
        
        self.api_key = APIConfig.BYTEPLUS_API_KEY
        self.base_url = APIConfig.BYTEPLUS_BASE_URL
        self.headers = APIConfig.get_byteplus_headers()
        
        # API 엔드포인트
        self.create_video_url = f"{self.base_url}/api/v1/video_generation"
        self.query_video_url = f"{self.base_url}/api/v1/video_generation"
        
        self.logger.info(f"BytePlus API 클라이언트 초기화 완료 - Base URL: {self.base_url}")
        
    def _image_to_base64(self, image: Union[str, Image.Image]) -> str:
        """
        이미지를 Base64 문자열로 변환
        
        Args:
            image: 이미지 파일 경로 또는 PIL Image 객체
            
        Returns:
            str: Base64 인코딩된 이미지 문자열
        """
        if isinstance(image, str):
            # 파일 경로인 경우
            with open(image, 'rb') as img_file:
                image_data = img_file.read()
        elif isinstance(image, Image.Image):
            # PIL Image 객체인 경우
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            image_data = img_byte_arr.getvalue()
        else:
            raise ValueError("이미지는 파일 경로 또는 PIL Image 객체여야 합니다.")
            
        return base64.b64encode(image_data).decode('utf-8')
    
    def create_video_task(self, image: Union[str, Image.Image], 
                         prompt: str = "자연스럽고 부드러운 움직임으로 생동감 있는 동영상을 만들어주세요.",
                         duration: int = 4,
                         fps: int = 24,
                         resolution: str = "1024x576") -> Optional[str]:
        """
        동영상 생성 작업 생성
        
        Args:
            image: 입력 이미지
            prompt: 동영상 생성을 위한 프롬프트
            duration: 동영상 길이 (초)
            fps: 프레임률
            resolution: 해상도
            
        Returns:
            str: 작업 ID 또는 None (실패 시)
        """
        log_function_call(self.logger, "create_video_task", 
                         image_type=type(image).__name__,
                         prompt_length=len(prompt),
                         duration=duration,
                         fps=fps,
                         resolution=resolution)
        
        try:
            self.logger.info("동영상 생성 작업 시작")
            
            # 이미지를 Base64로 변환
            self.logger.debug("이미지를 Base64로 변환 중")
            image_base64 = self._image_to_base64(image)
            
            req_key = f"video_gen_{int(time.time())}"
            
            # API 요청 데이터
            request_data = {
                "model": "Seedance-1.0-lite",  # Seedance 1.0 모델
                "req_key": req_key,
                "prompt": prompt,
                "image": image_base64,
                "cfg_scale": 7.5,
                "seed": -1,
                "duration": max(APIConfig.VIDEO_DURATION_MIN, 
                               min(duration, APIConfig.VIDEO_DURATION_MAX)),
                "fps": fps,
                "resolution": resolution,
                "format": APIConfig.VIDEO_OUTPUT_FORMAT
            }
            
            self.logger.info(f"동영상 생성 요청 - req_key: {req_key}, duration: {request_data['duration']}초")
            
            # API 호출
            log_api_request(self.logger, "BytePlus", self.create_video_url, "요청 시작")
            response = requests.post(
                self.create_video_url,
                headers=self.headers,
                json=request_data,
                timeout=30
            )
            
            log_api_request(self.logger, "BytePlus", self.create_video_url, f"응답 수신 (상태코드: {response.status_code})")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    task_id = result.get("data", {}).get("task_id")
                    self.logger.info(f"동영상 생성 작업 생성 성공 - Task ID: {task_id}")
                    return task_id
                else:
                    error_msg = result.get('message', 'Unknown error')
                    self.logger.error(f"API 오류: {error_msg}")
                    return None
            else:
                self.logger.error(f"HTTP 오류: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            log_error(self.logger, e, "동영상 생성 작업 생성")
            return None
    
    def query_video_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        동영상 생성 작업 상태 조회
        
        Args:
            task_id: 작업 ID
            
        Returns:
            dict: 작업 상태 정보 또는 None (실패 시)
        """
        try:
            # API 호출
            response = requests.get(
                f"{self.query_video_url}/{task_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    return result.get("data")
                else:
                    print(f"API 오류: {result.get('message', 'Unknown error')}")
                    return None
            else:
                print(f"HTTP 오류: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            print(f"동영상 작업 상태 조회 중 오류 발생: {str(e)}")
            return None
    
    def wait_for_completion(self, task_id: str, max_wait_time: int = 300, 
                           check_interval: int = 5) -> Optional[Dict[str, Any]]:
        """
        동영상 생성 완료까지 대기
        
        Args:
            task_id: 작업 ID
            max_wait_time: 최대 대기 시간 (초)
            check_interval: 상태 확인 간격 (초)
            
        Returns:
            dict: 완료된 작업 정보 또는 None (실패/타임아웃)
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            task_info = self.query_video_task(task_id)
            
            if task_info is None:
                return None
            
            status = task_info.get("status", "").lower()
            
            if status == "success":
                return task_info
            elif status in ["failed", "error"]:
                print(f"동영상 생성 실패: {task_info.get('error_message', 'Unknown error')}")
                return None
            elif status in ["processing", "pending", "running"]:
                # 진행 중인 경우 계속 대기
                time.sleep(check_interval)
            else:
                print(f"알 수 없는 상태: {status}")
                time.sleep(check_interval)
        
        print(f"동영상 생성 타임아웃 ({max_wait_time}초)")
        return None
    
    def download_video(self, video_url: str, save_path: str) -> bool:
        """
        생성된 동영상 다운로드
        
        Args:
            video_url: 동영상 URL
            save_path: 저장 경로
            
        Returns:
            bool: 다운로드 성공 여부
        """
        try:
            response = requests.get(video_url, stream=True, timeout=60)
            
            if response.status_code == 200:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                return True
            else:
                print(f"동영상 다운로드 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"동영상 다운로드 중 오류 발생: {str(e)}")
            return False
    
    def generate_video_from_image(self, image: Union[str, Image.Image],
                                 prompt: str = "자연스럽고 부드러운 움직임으로 생동감 있는 동영상을 만들어주세요.",
                                 duration: int = 4,
                                 save_path: Optional[str] = None) -> Optional[str]:
        """
        이미지로부터 동영상 생성 (전체 프로세스)
        
        Args:
            image: 입력 이미지
            prompt: 동영상 생성 프롬프트
            duration: 동영상 길이 (초)
            save_path: 저장 경로 (None인 경우 자동 생성)
            
        Returns:
            str: 저장된 동영상 파일 경로 또는 None (실패 시)
        """
        try:
            # 1. 동영상 생성 작업 생성
            task_id = self.create_video_task(image, prompt, duration)
            if not task_id:
                return None
            
            # 2. 작업 완료 대기
            task_result = self.wait_for_completion(task_id)
            if not task_result:
                return None
            
            # 3. 동영상 URL 추출
            video_url = task_result.get("video_url")
            if not video_url:
                print("동영상 URL을 찾을 수 없습니다.")
                return None
            
            # 4. 저장 경로 설정
            if save_path is None:
                timestamp = int(time.time())
                save_path = f"app/static/videos/generated_video_{timestamp}.mp4"
            
            # 5. 동영상 다운로드
            if self.download_video(video_url, save_path):
                return save_path
            else:
                return None
                
        except Exception as e:
            print(f"동영상 생성 전체 프로세스 중 오류 발생: {str(e)}")
            return None
    
    def get_supported_resolutions(self) -> list:
        """지원되는 해상도 목록 반환"""
        return [
            "1024x576",  # 16:9 가로
            "576x1024",  # 9:16 세로
            "768x768",   # 1:1 정사각형
            "1280x720",  # HD
            "720x1280"   # HD 세로
        ]
    
    def get_supported_durations(self) -> list:
        """지원되는 동영상 길이 목록 반환"""
        return list(range(APIConfig.VIDEO_DURATION_MIN, APIConfig.VIDEO_DURATION_MAX + 1))
