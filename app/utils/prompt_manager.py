import yaml
import os
from pathlib import Path
from typing import Dict, List

class PromptManager:
    def __init__(self):
        # app/utils에서 app/prompt로 경로 설정
        current_dir = Path(__file__).parent
        app_dir = current_dir.parent
        self.prompt_dir = app_dir / 'prompt'
        self.image_prompt_dir = self.prompt_dir / 'image'
        self.video_prompt_dir = self.prompt_dir / 'video'
    
    def get_pixel_art_prompt(self) -> str:
        """픽셀 아트 편집 프롬프트를 반환합니다."""
        yaml_path = self.image_prompt_dir / 'pixel_art_editing.yaml'
        with open(yaml_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        return data['base_prompt'].strip()
    
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
