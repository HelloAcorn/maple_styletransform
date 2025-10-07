#!/usr/bin/env python3
"""
메이플스토리 픽셀 아트 캐릭터 샘플 비디오 생성 테스트 스크립트
각 입력 이미지에 대해 모든 비디오 프롬프트를 적용하여 비디오를 생성합니다.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import time
from datetime import datetime
from PIL import Image
import yaml
import asyncio
import concurrent.futures
from functools import partial

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.modules.byteplus_integration import BytePlusVideoGenerator
from app.utils.logger import setup_logger
from app.core.character_categories import get_character_category, get_video_prompt_directory


class SampleVideoGenerator:
    """샘플 비디오 생성기"""
    
    def __init__(self, duration: int = 5, resolution: str = "480p"):
        self.logger = setup_logger('sample_video_generator')
        self.video_generator = BytePlusVideoGenerator()
        self.base_dir = Path(__file__).parent.parent
        self.input_image_dir = self.base_dir / "test" / "video_input_image"
        self.prompt_dir = self.base_dir / "app" / "prompt" / "video"
        self.result_dir = self.base_dir / "test" / "video_result"
        
        # 비디오 생성 파라미터
        self.duration = duration
        self.resolution = resolution
        
        # 결과 디렉토리 생성
        self.result_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"비디오 생성기 초기화 완료 - Duration: {duration}초, Resolution: {resolution}")
        
    def get_available_input_images(self) -> List[Path]:
        """사용 가능한 입력 이미지 목록 반환"""
        input_images = []
        if self.input_image_dir.exists():
            for file in self.input_image_dir.iterdir():
                if file.is_file() and file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
                    input_images.append(file)
        return sorted(input_images)
    
    def extract_character_name(self, image_filename: str) -> Optional[str]:
        """
        이미지 파일명에서 캐릭터 이름 추출
        파일명 형식: "남자_데몬슬레이어_05_20251007_225930_734.png"
        
        Args:
            image_filename: 이미지 파일명
            
        Returns:
            str: 캐릭터 이름 또는 None
        """
        try:
            # 확장자 제거
            name_without_ext = image_filename.rsplit('.', 1)[0]
            # '_'로 분리
            parts = name_without_ext.split('_')
            
            # 두 번째 부분이 캐릭터 이름 (남자_캐릭터명_번호_날짜_시간_밀리초)
            if len(parts) >= 2:
                character_name = parts[1]
                self.logger.debug(f"추출된 캐릭터 이름: {character_name} (from {image_filename})")
                return character_name
            
            return None
        except Exception as e:
            self.logger.warning(f"캐릭터 이름 추출 실패 ({image_filename}): {e}")
            return None
    
    def get_available_prompts(self, character_name: Optional[str] = None) -> Dict[str, str]:
        """
        사용 가능한 비디오 프롬프트 목록 반환
        캐릭터 이름이 제공되면 해당 카테고리의 프롬프트만 반환
        
        Args:
            character_name: 캐릭터 이름 (None이면 모든 프롬프트)
            
        Returns:
            Dict[str, str]: 프롬프트명 -> 프롬프트 텍스트
        """
        prompts = {}
        
        # 캐릭터 이름이 제공된 경우 해당 카테고리 폴더만 검색
        if character_name:
            try:
                category = get_character_category(character_name)
                category_dir = self.base_dir / "app" / "prompt" / "video" / category.value
                
                if category_dir.exists():
                    self.logger.info(f"{character_name} → {category.value} 카테고리 프롬프트 로드")
                    for file in category_dir.iterdir():
                        if file.is_file() and file.suffix.lower() == '.yaml':
                            try:
                                with open(file, 'r', encoding='utf-8') as f:
                                    data = yaml.safe_load(f)
                                    if data and 'base_prompt' in data:
                                        prompts[file.stem] = data['base_prompt']
                                        self.logger.debug(f"프롬프트 로드 완료: {file.stem}")
                            except Exception as e:
                                self.logger.warning(f"프롬프트 파일 로드 실패 ({file.name}): {e}")
                else:
                    self.logger.warning(f"카테고리 디렉토리가 존재하지 않음: {category_dir}")
            except Exception as e:
                self.logger.error(f"카테고리별 프롬프트 로드 실패: {e}")
        
        # 캐릭터 이름이 없거나 로드 실패 시 모든 프롬프트 로드
        if not prompts and self.prompt_dir.exists():
            self.logger.info("전체 프롬프트 로드 (카테고리 무시)")
            for file in self.prompt_dir.iterdir():
                if file.is_file() and file.suffix.lower() == '.yaml':
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f)
                            if data and 'base_prompt' in data:
                                prompts[file.stem] = data['base_prompt']
                                self.logger.debug(f"프롬프트 로드 완료: {file.stem}")
                    except Exception as e:
                        self.logger.warning(f"프롬프트 파일 로드 실패 ({file.name}): {e}")
        
        return prompts
    
    def generate_single_video(self, image_path: Path, prompt_name: str, 
                             prompt_text: str, index: int, total: int) -> Dict:
        """단일 비디오 생성"""
        try:
            self.logger.info(f"[{index}/{total}] {image_path.stem} + {prompt_name} 비디오 생성 시작...")
            
            start_time = time.time()
            
            # 이미지 로드
            image = Image.open(image_path)
            image.load()
            
            # 비디오 생성 (BytePlus API 호출)
            # duration은 프롬프트에 이미 포함되어 있으므로 파라미터로도 전달
            task_id = self.video_generator.create_video_task(
                image=image,
                prompt=prompt_text,
                duration=self.duration,
                resolution=self.resolution
            )
            
            if not task_id:
                self.logger.error(f"{image_path.stem} + {prompt_name} - Task 생성 실패")
                return {
                    'success': False,
                    'image': image_path.stem,
                    'prompt': prompt_name,
                    'error': 'Task 생성 실패'
                }
            
            self.logger.info(f"{image_path.stem} + {prompt_name} - Task ID: {task_id}, 대기 중...")
            
            # 작업 완료 대기 (최대 90초)
            task_result = self.video_generator.wait_for_completion(task_id, max_wait_time=90)
            
            if not task_result:
                self.logger.error(f"{image_path.stem} + {prompt_name} - 비디오 생성 실패 또는 타임아웃")
                return {
                    'success': False,
                    'image': image_path.stem,
                    'prompt': prompt_name,
                    'error': '생성 실패 또는 타임아웃'
                }
            
            # 비디오 URL 추출
            video_url = self.video_generator._extract_video_url(task_result)
            if not video_url:
                self.logger.error(f"{image_path.stem} + {prompt_name} - 비디오 URL 추출 실패")
                return {
                    'success': False,
                    'image': image_path.stem,
                    'prompt': prompt_name,
                    'error': '비디오 URL 추출 실패'
                }
            
            # 저장 경로 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{image_path.stem}_{prompt_name}_{timestamp}.mp4"
            save_path = self.result_dir / filename
            
            # 비디오 다운로드
            if self.video_generator.download_video(video_url, str(save_path)):
                elapsed_time = time.time() - start_time
                self.logger.info(f"✅ {image_path.stem} + {prompt_name} 완료 ({elapsed_time:.1f}초) - {filename}")
                return {
                    'success': True,
                    'image': image_path.stem,
                    'prompt': prompt_name,
                    'filename': filename,
                    'path': str(save_path),
                    'elapsed_time': elapsed_time
                }
            else:
                self.logger.error(f"{image_path.stem} + {prompt_name} - 비디오 다운로드 실패")
                return {
                    'success': False,
                    'image': image_path.stem,
                    'prompt': prompt_name,
                    'error': '비디오 다운로드 실패'
                }
                
        except Exception as e:
            self.logger.error(f"{image_path.stem} + {prompt_name} 생성 오류: {str(e)}")
            return {
                'success': False,
                'image': image_path.stem,
                'prompt': prompt_name,
                'error': str(e)
            }
    
    def generate_videos_for_image(self, image_path: Path) -> List[Dict]:
        """
        하나의 이미지에 대해 캐릭터에 맞는 프롬프트를 적용하여 비디오 생성 (비동기)
        
        Args:
            image_path: 입력 이미지 경로
            
        Returns:
            List[Dict]: 생성 결과 리스트
        """
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"🎬 이미지: {image_path.name}")
        self.logger.info(f"{'='*80}")
        
        # 이미지 파일명에서 캐릭터 이름 추출
        character_name = self.extract_character_name(image_path.name)
        
        # 캐릭터에 맞는 프롬프트 로드
        prompts = self.get_available_prompts(character_name)
        
        if not prompts:
            self.logger.error(f"사용 가능한 프롬프트가 없습니다: {image_path.name}")
            return []
        
        total_prompts = len(prompts)
        if character_name:
            category = get_character_category(character_name)
            self.logger.info(f"캐릭터: {character_name} (카테고리: {category.value})")
        self.logger.info(f"총 {total_prompts}개 프롬프트로 비디오 생성 시작")
        
        results = []
        
        # ThreadPoolExecutor를 사용하여 병렬 처리
        # 각 프롬프트에 대해 비디오 생성 작업을 제출
        with concurrent.futures.ThreadPoolExecutor(max_workers=total_prompts) as executor:
            futures = []
            for idx, (prompt_name, prompt_text) in enumerate(prompts.items(), 1):
                future = executor.submit(
                    self.generate_single_video,
                    image_path,
                    prompt_name,
                    prompt_text,
                    idx,
                    total_prompts
                )
                futures.append(future)
            
            # 모든 작업이 완료될 때까지 대기하고 결과 수집
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
        
        # 결과 정렬 (프롬프트 이름 순)
        results.sort(key=lambda x: x.get('prompt', ''))
        
        successful = len([r for r in results if r['success']])
        self.logger.info(f"\n{image_path.stem} 완료: {successful}/{total_prompts}개 성공")
        
        return results
    
    def generate_all_videos(self, selected_image: Optional[str] = None) -> Dict[str, List[Dict]]:
        """모든 입력 이미지에 대해 비디오 생성 (캐릭터별 자동 매칭)
        
        Args:
            selected_image: 특정 이미지만 처리 (None이면 모든 이미지)
        """
        input_images = self.get_available_input_images()
        
        if not input_images:
            self.logger.error("사용 가능한 입력 이미지가 없습니다.")
            return {}
        
        # 특정 이미지만 선택된 경우 필터링
        if selected_image:
            input_images = [img for img in input_images if img.stem == selected_image]
            if not input_images:
                self.logger.error(f"이미지 '{selected_image}'를 찾을 수 없습니다.")
                available = [img.stem for img in self.get_available_input_images()]
                self.logger.info(f"사용 가능한 이미지: {', '.join(available)}")
                return {}
        
        total_images = len(input_images)
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"🎥 비디오 생성 작업 시작 (캐릭터 자동 매칭)")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"입력 이미지: {total_images}개")
        self.logger.info(f"비디오 설정: {self.duration}초, {self.resolution}, 1:1 ratio")
        self.logger.info(f"저장 위치: {self.result_dir}")
        self.logger.info(f"{'='*80}\n")
        
        all_results = {}
        total_start_time = time.time()
        
        for idx, image_path in enumerate(input_images, 1):
            self.logger.info(f"\n[진행률: {idx}/{total_images}] 처리 중: {image_path.name}")
            
            image_start_time = time.time()
            results = self.generate_videos_for_image(image_path)
            image_end_time = time.time()
            
            all_results[image_path.stem] = results
            
            image_elapsed = image_end_time - image_start_time
            successful = len([r for r in results if r['success']])
            total_prompts = len(results)
            self.logger.info(f"{image_path.stem} 완료: {successful}/{total_prompts}개 성공, 소요시간: {image_elapsed:.1f}초")
        
        total_end_time = time.time()
        total_elapsed = total_end_time - total_start_time
        
        # 최종 결과 요약
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"🎉 전체 비디오 생성 완료")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"총 소요시간: {total_elapsed:.1f}초 ({total_elapsed/60:.1f}분)")
        
        total_successful = 0
        total_attempted = 0
        
        for image_name, results in all_results.items():
            successful = len([r for r in results if r['success']])
            total_successful += successful
            total_attempted += len(results)
            self.logger.info(f"  📸 {image_name}: {successful}/{len(results)}개 성공")
        
        success_rate = (total_successful/total_attempted*100) if total_attempted > 0 else 0
        self.logger.info(f"\n전체 성공률: {total_successful}/{total_attempted}개 ({success_rate:.1f}%)")
        self.logger.info(f"{'='*80}\n")
        
        return all_results


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="메이플스토리 픽셀 아트 캐릭터 샘플 비디오 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python make_sample_video.py                                      # 모든 이미지에 대해 비디오 생성
  python make_sample_video.py -i 남자_데몬슬레이어_05_20251007_225930_734  # 특정 이미지만 처리
  python make_sample_video.py -d 5                                 # 5초 길이로 생성
  python make_sample_video.py --list-images                        # 이미지 목록 표시
  python make_sample_video.py --list-prompts                       # 프롬프트 목록 표시
  python make_sample_video.py --help                               # 도움말 표시
        """
    )
    
    parser.add_argument(
        '-d', '--duration',
        type=int,
        default=5,
        help='비디오 길이 (초, 기본값: 5)'
    )
    
    parser.add_argument(
        '-r', '--resolution',
        type=str,
        default='480p',
        help='비디오 해상도 (기본값: 480p)'
    )
    
    parser.add_argument(
        '-i', '--image',
        type=str,
        default=None,
        help='특정 이미지만 처리 (확장자 제외한 파일명)', 
        metavar='IMAGE'
    )
    
    parser.add_argument(
        '--list-images',
        action='store_true',
        help='사용 가능한 이미지 목록만 표시하고 종료'
    )
    
    parser.add_argument(
        '--list-prompts',
        action='store_true',
        help='사용 가능한 프롬프트 목록만 표시하고 종료'
    )
    
    args = parser.parse_args()
    
    # 비디오 생성기 초기화
    try:
        generator = SampleVideoGenerator(duration=args.duration, resolution=args.resolution)
    except Exception as e:
        print(f"❌ 비디오 생성기 초기화 실패: {e}")
        print("💡 app/core/.api_key 파일에 BYTEPLUS_API_KEY가 설정되어 있는지 확인하세요.")
        return 1
    
    # 이미지 목록만 표시하는 경우
    if args.list_images:
        input_images = generator.get_available_input_images()
        
        if input_images:
            print("📸 사용 가능한 입력 이미지 목록:")
            for i, image_path in enumerate(input_images, 1):
                print(f"  {i:2d}. {image_path.stem}")
            print(f"\n총 {len(input_images)}개 이미지")
        else:
            print("❌ 사용 가능한 입력 이미지가 없습니다.")
            print(f"💡 {generator.input_image_dir} 폴더에 이미지를 추가하세요.")
            
        return 0
    
    # 프롬프트 목록만 표시하는 경우
    if args.list_prompts:
        from app.core.character_categories import get_all_categories, get_category_description
        
        print("🎬 카테고리별 비디오 프롬프트 목록:\n")
        
        total_prompts = 0
        for category in get_all_categories():
            print(f"📁 {category.value}")
            print(f"   {get_category_description(category)}\n")
            
            category_dir = generator.base_dir / "app" / "prompt" / "video" / category.value
            if category_dir.exists():
                prompts = {}
                for file in category_dir.iterdir():
                    if file.is_file() and file.suffix.lower() == '.yaml':
                        try:
                            with open(file, 'r', encoding='utf-8') as f:
                                data = yaml.safe_load(f)
                                if data and 'base_prompt' in data:
                                    prompts[file.stem] = data['base_prompt']
                        except:
                            pass
                
                if prompts:
                    for i, (name, prompt) in enumerate(prompts.items(), 1):
                        preview = prompt.strip()[:80].replace('\n', ' ')
                        print(f"   {i}. {name}")
                        print(f"      {preview}...\n")
                    total_prompts += len(prompts)
                else:
                    print(f"   (프롬프트 없음)\n")
            else:
                print(f"   (디렉토리 없음)\n")
        
        print(f"총 {total_prompts}개 프롬프트 (카테고리별 5개씩)")
        return 0
    
    # 입력값 검증
    if args.duration <= 0:
        print("❌ 비디오 길이는 1 이상이어야 합니다.")
        return 1
    
    if args.duration > 10:
        print("⚠️  비디오 길이가 깁니다. API 비용과 처리 시간이 증가할 수 있습니다.")
        response = input("계속하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("작업이 취소되었습니다.")
            return 0
    
    input_images = generator.get_available_input_images()
    
    if not input_images:
        print(f"❌ {generator.input_image_dir} 폴더에 입력 이미지가 없습니다.")
        return 1
    
    # 특정 이미지 선택 시 검증
    if args.image:
        available_stems = [img.stem for img in input_images]
        if args.image not in available_stems:
            print(f"❌ 이미지 '{args.image}'를 찾을 수 없습니다.")
            print(f"\n사용 가능한 이미지 목록:")
            for i, stem in enumerate(available_stems, 1):
                print(f"  {i:2d}. {stem}")
            return 1
        selected_images = [args.image]
    else:
        selected_images = None
    
    total_images = 1 if args.image else len(input_images)
    
    if args.image:
        print(f"🎥 이미지 '{args.image}'에 대해 캐릭터 매칭하여 비디오를 생성합니다.")
    else:
        print(f"🎥 {total_images}개 이미지에 대해 캐릭터별 비디오를 자동 생성합니다.")
    print(f"⚙️  설정: {args.duration}초, {args.resolution}, 1:1 ratio")
    print(f"📁 결과는 {generator.result_dir} 폴더에 저장됩니다.")
    print(f"⏱️  각 캐릭터마다 5개 프롬프트 적용 (카테고리별 자동 매칭)")
    print(f"⏱️  예상 소요시간: 약 {total_images * 5 * 1.5:.0f}분 (이미지당 ~7.5분)")
    
    try:
        # 비디오 생성 실행
        results = generator.generate_all_videos(selected_image=args.image)
        
        if results:
            print(f"\n✅ 샘플 비디오 생성이 완료되었습니다!")
            print(f"📁 결과 위치: {generator.result_dir}")
        else:
            print("❌ 비디오 생성에 실패했습니다.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        return 1
    except Exception as e:
        print(f"❌ 오류가 발생했습니다: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

