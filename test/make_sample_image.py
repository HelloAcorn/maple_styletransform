#!/usr/bin/env python3
"""
메이플스토리 픽셀 아트 캐릭터별 샘플 이미지 생성 테스트 스크립트
각 캐릭터별로 n장씩 이미지를 생성하여 캐릭터별 폴더에 저장합니다.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict
import time
from datetime import datetime
from PIL import Image
import concurrent.futures
import threading

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.modules.image_integration import LLMImageProcessor
from app.modules.image_utils import ImageUtils
from app.utils.logger import setup_logger


class SampleImageGenerator:
    """샘플 이미지 생성기"""
    
    def __init__(self):
        self.logger = setup_logger('sample_image_generator')
        self.processor = LLMImageProcessor()
        self.base_dir = Path(__file__).parent.parent
        self.character_dir = self.base_dir / "files" / "pixel_character_image"
        self.input_image_dir = self.base_dir / "test" / "input_Image"
        self.result_dir = self.base_dir / "test" / "result"
        
        # 결과 디렉토리 생성
        self.result_dir.mkdir(parents=True, exist_ok=True)
        
    def get_available_characters(self) -> List[str]:
        """사용 가능한 캐릭터 목록 반환"""
        characters = []
        if self.character_dir.exists():
            for file in self.character_dir.iterdir():
                if file.is_file() and file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    # "_픽셀" 접미사 제거하여 캐릭터 이름 추출
                    character_name = file.stem
                    if character_name.endswith('_픽셀'):
                        character_name = character_name[:-3]  # "_픽셀" 제거
                    characters.append(character_name)
        return sorted(characters)
    
    def get_available_input_images(self) -> List[str]:
        """사용 가능한 입력 이미지 목록 반환"""
        input_images = []
        if self.input_image_dir.exists():
            for file in self.input_image_dir.iterdir():
                if file.is_file() and file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
                    input_images.append(file.stem)
        return sorted(input_images)
    
    def load_input_image(self, image_name: str) -> Image.Image:
        """입력 이미지 로드"""
        # 다양한 확장자 확인
        for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
            image_path = self.input_image_dir / f"{image_name}{ext}"
            if image_path.exists():
                image = Image.open(image_path)
                image.load()  # 메모리에 완전히 로드
                self.logger.debug(f"입력 이미지 로드 완료: {image_path}")
                return image
        
        raise FileNotFoundError(f"입력 이미지를 찾을 수 없습니다: {image_name}")
    
    def generate_combination_images(self, input_image_name: str, character_name: str, 
                                   num_images: int) -> List[Dict]:
        """특정 입력 이미지와 캐릭터 조합으로 n장의 이미지 생성"""
        # 픽셀 캐릭터 이미지 경로 확인
        character_image_path = self.character_dir / f"{character_name}_픽셀.png"
        if not character_image_path.exists():
            # 다른 확장자들도 확인
            for ext in ['.jpg', '.jpeg', '.PNG']:
                character_image_path = self.character_dir / f"{character_name}_픽셀{ext}"
                if character_image_path.exists():
                    break
            else:
                self.logger.error(f"캐릭터 이미지를 찾을 수 없습니다: {character_name}_픽셀")
                return []
        
        # 결과 폴더 구조: input_image/ (캐릭터별 하위 폴더 없이)
        input_result_dir = self.result_dir / input_image_name
        input_result_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"{input_image_name} + {character_name} 조합으로 {num_images}장의 이미지 생성 시작")
        
        try:
            # 입력 이미지 로드
            input_image = self.load_input_image(input_image_name)
            
            # 픽셀 캐릭터 이미지 로드
            pixel_character = Image.open(character_image_path)
            pixel_character.load()
            
            self.logger.debug(f"이미지 로드 완료 - 입력: {input_image_name}, 캐릭터: {character_name}")
            
        except Exception as load_error:
            self.logger.error(f"이미지 로드 실패: {load_error}")
            return []
        
        def generate_single_image(index: int) -> Dict:
            """단일 이미지 생성"""
            try:
                self.logger.info(f"{input_image_name}+{character_name} - 이미지 {index + 1}/{num_images} 생성 중...")
                
                # 각 스레드에서 완전히 독립적인 이미지 복사본 생성
                try:
                    pixel_copy = pixel_character.copy()
                    input_copy = input_image.copy()
                    
                    self.logger.debug(f"{input_image_name}+{character_name} - 이미지 복사본 생성 완료")
                    
                except Exception as copy_error:
                    self.logger.error(f"{input_image_name}+{character_name} - 이미지 복사 실패: {copy_error}")
                    return {'success': False, 'index': index, 'error': f'이미지 복사 실패: {copy_error}'}
                
                # 이미지 생성 (픽셀 캐릭터 + 입력 이미지) - 새로운 분석 방식 사용
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result_image = loop.run_until_complete(
                        self.processor.analyze_and_merge_images(pixel_copy, input_copy, character_name)
                    )
                finally:
                    loop.close()
                
                if result_image:
                    # 파일명 생성 (입력이미지_캐릭터_번호_타임스탬프)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 밀리초 포함
                    filename = f"{input_image_name}_{character_name}_{index + 1:02d}_{timestamp}.png"
                    file_path = input_result_dir / filename
                    
                    # 이미지 저장
                    result_image.save(file_path, "PNG")
                    
                    self.logger.info(f"{input_image_name}+{character_name} - 이미지 {index + 1} 완료: {filename}")
                    return {
                        'success': True,
                        'index': index,
                        'filename': filename,
                        'path': str(file_path),
                        'input_image': input_image_name,
                        'character': character_name
                    }
                else:
                    self.logger.warning(f"{input_image_name}+{character_name} - 이미지 {index + 1} 생성 실패")
                    return {'success': False, 'index': index}
                    
            except Exception as e:
                self.logger.error(f"{input_image_name}+{character_name} - 이미지 {index + 1} 생성 오류: {str(e)}")
                return {'success': False, 'index': index, 'error': str(e)}
        
        # 병렬로 이미지 생성 (최대 5개 동시)
        results = []
        max_workers = min(5, num_images)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(generate_single_image, i) for i in range(num_images)]
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
        
        # 결과를 인덱스 순으로 정렬
        results.sort(key=lambda x: x.get('index', 0))
        
        successful_results = [r for r in results if r['success']]
        self.logger.info(f"{input_image_name}+{character_name} 완료: {len(successful_results)}/{num_images}장 성공")
        
        return successful_results
    
    def generate_all_combinations(self, num_images: int, selected_character: str = None) -> Dict[str, Dict[str, List[Dict]]]:
        """모든 입력 이미지와 캐릭터 조합에 대해 이미지 생성
        
        Args:
            num_images: 각 조합당 생성할 이미지 수
            selected_character: 특정 캐릭터만 생성 (None이면 모든 캐릭터)
        """
        characters = self.get_available_characters()
        input_images = self.get_available_input_images()
        
        if not characters:
            self.logger.error("사용 가능한 캐릭터가 없습니다.")
            return {}
            
        if not input_images:
            self.logger.error("사용 가능한 입력 이미지가 없습니다.")
            return {}
        
        # 특정 캐릭터만 선택된 경우 필터링
        if selected_character:
            if selected_character in characters:
                characters = [selected_character]
                self.logger.info(f"선택된 캐릭터: {selected_character}")
            else:
                self.logger.error(f"캐릭터 '{selected_character}'를 찾을 수 없습니다.")
                self.logger.info(f"사용 가능한 캐릭터: {', '.join(self.get_available_characters())}")
                return {}
        
        total_combinations = len(input_images) * len(characters)
        self.logger.info(f"총 {len(input_images)}개 입력 이미지 × {len(characters)}개 캐릭터 = {total_combinations}개 조합")
        self.logger.info(f"각 조합당 {num_images}장씩 생성 → 총 {total_combinations * num_images}장 생성 예정")
        self.logger.info(f"입력 이미지: {', '.join(input_images)}")
        self.logger.info(f"캐릭터 목록: {', '.join(characters)}")
        
        all_results = {}
        total_start_time = time.time()
        combination_count = 0
        
        for input_image in input_images:
            self.logger.info(f"\n🖼️  입력 이미지: {input_image}")
            all_results[input_image] = {}
            
            for character in characters:
                combination_count += 1
                self.logger.info(f"\n[{combination_count}/{total_combinations}] {input_image} + {character} 조합 처리 중...")
                
                combination_start_time = time.time()
                results = self.generate_combination_images(input_image, character, num_images)
                combination_end_time = time.time()
                
                all_results[input_image][character] = results
                
                successful = len([r for r in results if r['success']])
                self.logger.info(f"{input_image}+{character} 완료 - {successful}/{num_images}장 성공, 소요시간: {combination_end_time - combination_start_time:.1f}초")
        
        total_end_time = time.time()
        
        # 최종 결과 요약
        self.logger.info(f"\n=== 전체 생성 완료 ===")
        self.logger.info(f"총 소요시간: {total_end_time - total_start_time:.1f}초")
        
        total_successful = 0
        total_attempted = 0
        
        for input_image, character_results in all_results.items():
            self.logger.info(f"\n📸 {input_image}:")
            for character, results in character_results.items():
                successful = len([r for r in results if r['success']])
                total_successful += successful
                total_attempted += num_images
                self.logger.info(f"  └ {character}: {successful}/{num_images}장 성공")
        
        success_rate = (total_successful/total_attempted*100) if total_attempted > 0 else 0
        self.logger.info(f"\n전체 성공률: {total_successful}/{total_attempted}장 ({success_rate:.1f}%)")
        
        return all_results


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="메이플스토리 픽셀 아트 캐릭터별 샘플 이미지 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python make_sample_image.py -n 3                    # 모든 캐릭터별로 3장씩 생성
  python make_sample_image.py -n 5 -c 메이플러       # 메이플러만 5장씩 생성
  python make_sample_image.py --char 슬라임          # 슬라임만 2장씩 생성 (기본값)
  python make_sample_image.py --list-characters      # 캐릭터 목록 표시
  python make_sample_image.py --help                 # 도움말 표시
        """
    )
    
    parser.add_argument(
        '-n', '--num-images',
        type=int,
        default=2,
        help='각 캐릭터별로 생성할 이미지 수 (기본값: 2)'
    )
    
    parser.add_argument(
        '-c', '--char',
        type=str,
        default=None,
        help='특정 캐릭터만 생성 (예: 메이플러)', 
        metavar='CHARACTER'
    )
    
    parser.add_argument(
        '--list-characters',
        action='store_true',
        help='사용 가능한 캐릭터 목록만 표시하고 종료'
    )
    
    args = parser.parse_args()
    
    # 샘플 이미지 생성기 초기화 (API 키는 LLMSettings에서 자동 로드)
    try:
        generator = SampleImageGenerator()
    except Exception as e:
        print(f"❌ 이미지 생성기 초기화 실패: {e}")
        print("💡 app/core/.api_key 파일에 GOOGLE_API_KEY가 설정되어 있는지 확인하세요.")
        return 1
    
    # 캐릭터 목록만 표시하는 경우
    if args.list_characters:
        characters = generator.get_available_characters()
        input_images = generator.get_available_input_images()
        
        if characters:
            print("🎮 사용 가능한 캐릭터 목록:")
            for i, character in enumerate(characters, 1):
                print(f"  {i:2d}. {character}")
            print(f"\n총 {len(characters)}개 캐릭터")
        else:
            print("❌ 사용 가능한 캐릭터가 없습니다.")
            
        if input_images:
            print("\n📸 사용 가능한 입력 이미지 목록:")
            for i, image in enumerate(input_images, 1):
                print(f"  {i:2d}. {image}")
            print(f"\n총 {len(input_images)}개 입력 이미지")
        else:
            print("❌ 사용 가능한 입력 이미지가 없습니다.")
            
        if characters and input_images:
            total_combinations = len(characters) * len(input_images)
            print(f"\n총 {total_combinations}개 조합 가능")
            
        return 0
    
    # 입력값 검증
    if args.num_images <= 0:
        print("❌ 이미지 수는 1 이상이어야 합니다.")
        return 1
    
    if args.num_images > 10:
        print("⚠️  이미지 수가 많습니다. 처리 시간이 오래 걸릴 수 있습니다.")
        response = input("계속하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("작업이 취소되었습니다.")
            return 0
    
    input_images = generator.get_available_input_images()
    characters = generator.get_available_characters()
    
    if not input_images:
        print("❌ test/input_Image 폴더에 입력 이미지가 없습니다.")
        return 1
        
    if not characters:
        print("❌ files/pixel_character_image 폴더에 캐릭터 이미지가 없습니다.")
        return 1
    
    # 특정 캐릭터 선택 시 검증
    if args.char:
        if args.char not in characters:
            print(f"❌ 캐릭터 '{args.char}'를 찾을 수 없습니다.")
            print(f"\n사용 가능한 캐릭터 목록:")
            for i, character in enumerate(characters, 1):
                print(f"  {i:2d}. {character}")
            return 1
        selected_chars = [args.char]
    else:
        selected_chars = characters
    
    total_combinations = len(input_images) * len(selected_chars)
    total_images = total_combinations * args.num_images
    
    if args.char:
        print(f"🎨 {len(input_images)}개 입력 이미지 × 캐릭터 '{args.char}' 조합으로 각각 {args.num_images}장씩 생성합니다.")
    else:
        print(f"🎨 {len(input_images)}개 입력 이미지 × {len(selected_chars)}개 캐릭터 조합으로 각각 {args.num_images}장씩 생성합니다.")
    print(f"📊 총 {total_combinations}개 조합 × {args.num_images}장 = {total_images}장 생성 예정")
    print(f"📁 결과는 test/result/입력이미지명/ 폴더에 모든 캐릭터 이미지가 저장됩니다.")
    
    try:
        # 이미지 생성 실행
        results = generator.generate_all_combinations(args.num_images, selected_character=args.char)
        
        if results:
            print(f"\n✅ 샘플 이미지 생성이 완료되었습니다!")
            print(f"📁 결과 위치: {generator.result_dir}")
        else:
            print("❌ 이미지 생성에 실패했습니다.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        return 1
    except Exception as e:
        print(f"❌ 오류가 발생했습니다: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
