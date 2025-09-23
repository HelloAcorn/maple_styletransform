import yaml
import os
from pathlib import Path
from typing import Dict, List
from app.utils.logger import setup_logger

class PromptManager:
    def __init__(self):
        self.logger = setup_logger('prompt_manager')
        # app/utils에서 app/prompt로 경로 설정
        current_dir = Path(__file__).parent
        app_dir = current_dir.parent
        self.prompt_dir = app_dir / 'prompt'
        self.image_prompt_dir = self.prompt_dir / 'image'
        self.video_prompt_dir = self.prompt_dir / 'video'
    
    def get_pixel_art_prompt(self, character_name: str = None) -> str:
        """
        픽셀 아트 편집 프롬프트를 반환합니다.
        캐릭터에 맞는 프롬프트를 찾거나 기본 프롬프트를 반환합니다.
        
        Args:
            character_name: 캐릭터 이름
            
        Returns:
            str: 프롬프트 내용
        """
        # 캐릭터가 제공된 경우 캐릭터별 프롬프트 찾기
        if character_name:
            character_prompt_file = self.image_prompt_dir / f'{character_name}_editing.yaml'
            if character_prompt_file.exists():
                self.logger.info(f"캐릭터별 프롬프트 파일 발견: {character_name}_editing.yaml")
                with open(character_prompt_file, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                prompt = data['base_prompt'].strip()
                return prompt
            else:
                self.logger.warning(f"캐릭터별 프롬프트 파일이 존재하지 않음: {character_name}_editing.yaml")
        
        # 기본 프롬프트 (첫 번째 발견된 *_editing.yaml 파일 사용)
        editing_files = list(self.image_prompt_dir.glob('*_editing.yaml'))
        if editing_files:
            default_file = editing_files[0]
            self.logger.info(f"기본 프롬프트 파일 사용: {default_file.name}")
            with open(default_file, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
            prompt = data['base_prompt'].strip()
            return prompt
        
        # 아무 프롬프트도 없으면 기본 메시지 반환
        self.logger.warning("프롬프트 파일을 찾을 수 없음, 기본 메시지 사용")
        return "Edit the pixel art character in the style of the reference image."
    
    # 동영상 프롬프트 관련 메서드들
    def get_available_video_prompts(self) -> Dict[str, str]:
        """
        사용 가능한 동영상 프롬프트 목록을 반환합니다.
        
        Returns:
            Dict[str, str]: 파일명(확장자 제외) -> 표시명 매핑
        """
        prompts = {}
        
        if not self.video_prompt_dir.exists():
            return prompts
            
        # YAML 파일 목록 가져오기
        yaml_files = list(self.video_prompt_dir.glob("*.yaml"))
        
        for yaml_file in yaml_files:
            # 파일명에서 확장자 제거하고 그대로 사용
            prompt_key = yaml_file.stem
            display_name = prompt_key  # 파일명 그대로 사용
            prompts[prompt_key] = display_name
            
        return prompts
    
    def get_video_prompt_content(self, prompt_name: str) -> str:
        """
        특정 동영상 프롬프트의 내용을 반환합니다.
        
        Args:
            prompt_name: 프롬프트 파일명 (확장자 제외)
            
        Returns:
            str: 프롬프트 내용
        """
        yaml_file = self.video_prompt_dir / f"{prompt_name}.yaml"
        
        if not yaml_file.exists():
            return f"기본 동영상 생성 프롬프트 (파일 없음: {prompt_name})"
            
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('base_prompt', '기본 동영상 생성 프롬프트')
        except Exception as e:
            return f"프롬프트 로드 오류: {str(e)}"
    
    def get_video_prompt_list(self) -> List[str]:
        """
        동영상 프롬프트 키 목록을 반환합니다.
        
        Returns:
            List[str]: 프롬프트 키 목록
        """
        return list(self.get_available_video_prompts().keys())
