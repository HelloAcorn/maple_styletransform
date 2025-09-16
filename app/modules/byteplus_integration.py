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
        
        # API 키가 로드되지 않은 경우 명시적으로 로드
        if not APIConfig.BYTEPLUS_API_KEY:
            APIConfig.load_api_keys()
            self.logger.info("API 키 파일에서 BytePlus API 키 로드")
        
        self.api_key = APIConfig.get_byteplus_api_key()
        self.base_url = APIConfig.BYTEPLUS_BASE_URL
        self.headers = APIConfig.get_byteplus_headers()
        
        # API 엔드포인트
        self.create_video_url = f"{self.base_url}/api/v3/contents/generations/tasks"
        self.query_video_url = f"{self.base_url}/api/v3/contents/generations/tasks"
        
        self.logger.info(f"BytePlus API 클라이언트 초기화 완료 - Base URL: {self.base_url}")
        self.logger.info(f"API 키 상태: {'✅ 로드됨' if self.api_key else '❌ 없음'}")
        
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
    
    def _extract_video_url(self, status_info: Dict[str, Any]) -> Optional[str]:
        """
        응답 구조에서 video URL 추출
        """
        # "content" 객체에서 "video_url" 확인 (v3 API 표준)
        content = status_info.get("content")
        if content and "video_url" in content:
            return content["video_url"]
        
        return None
    
    def create_video_task(self, image: Union[str, Image.Image], 
                         prompt: str = "자연스럽고 부드러운 움직임으로 생동감 있는 동영상을 만들어주세요.",
                         duration: int = 4,
                         fps: int = 24,
                         resolution: str = "480p") -> Optional[str]:
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
            
            # 이미지를 data URL 형식으로 변환
            url_image = f"data:image/png;base64,{image_base64}"
            
            # 프롬프트에 설정 파라미터 추가 (테스트 코드 방식)
            enhanced_prompt = f"{prompt} --resolution 480p --duration {duration} --ratio 9:16 --camerafixed true"
            
            # API 요청 데이터 - v3 API 형식
            request_data = {
                "model": "seedance-1-0-pro-250528",  # 테스트 코드와 동일한 모델명
                "content": [
                    {
                        "type": "text",
                        "text": enhanced_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": url_image}
                    }
                ]
            }
            
            self.logger.info(f"동영상 생성 요청 - 모델: {request_data['model']}, duration: {duration}초")
            
            # API 호출 (최신 헤더 사용)
            headers = APIConfig.get_byteplus_headers()
            log_api_request(self.logger, "BytePlus", self.create_video_url, "요청 시작")
            response = requests.post(
                self.create_video_url,
                headers=headers,
                data=json.dumps(request_data),  # json 대신 data 사용
                timeout=90
            )
            
            log_api_request(self.logger, "BytePlus", self.create_video_url, f"응답 수신 (상태코드: {response.status_code})")
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get("id")  # v3 API는 직접 id 반환
                if task_id:
                    self.logger.info(f"동영상 생성 작업 생성 성공 - Task ID: {task_id}")
                    return task_id
                else:
                    self.logger.error(f"API 응답에서 task ID를 찾을 수 없음: {result}")
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
            # API 호출 (최신 헤더 사용)
            headers = APIConfig.get_byteplus_headers()
            response = requests.get(
                f"{self.query_video_url}/{task_id}",
                headers=headers,
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                return result  # v3 API는 직접 결과 반환
            else:
                self.logger.error(f"HTTP 오류: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            print(f"동영상 작업 상태 조회 중 오류 발생: {str(e)}")
            return None
    
    def wait_for_completion(self, task_id: str, max_wait_time: int = 90, 
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
            
            if status == "succeeded":  # v3 API는 "succeeded" 사용
                return task_info
            elif status in ["failed", "canceled"]:
                print(f"동영상 생성 실패: {task_info.get('error_message', 'Unknown error')}")
                return None
            elif status in ["processing", "pending", "running", "queued"]:
                # 진행 중인 경우 계속 대기
                time.sleep(check_interval)
            else:
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
            video_url = self._extract_video_url(task_result)
            if not video_url:
                self.logger.error("동영상 URL을 찾을 수 없습니다.")
                return None
            
            # 4. 저장 경로 설정
            if save_path is None:
                timestamp = int(time.time())
                save_path = f"files/videos/generated_video_{timestamp}.mp4"
            
            # 5. 동영상 다운로드
            if self.download_video(video_url, save_path):
                return save_path
            else:
                return None
                
        except Exception as e:
            print(f"동영상 생성 전체 프로세스 중 오류 발생: {str(e)}")
            return None
    
    def get_supported_resolutions(self) -> list:
        """지원되는 해상도 목록 반환 - 480p 9:16 고정"""
        return [
            "480p",  # 480p 해상도 (9:16 비율 고정)
        ]
    
    def get_supported_durations(self) -> list:
        """지원되는 동영상 길이 목록 반환"""
        return list(range(APIConfig.VIDEO_DURATION_MIN, APIConfig.VIDEO_DURATION_MAX + 1))
