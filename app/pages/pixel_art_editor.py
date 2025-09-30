"""
픽셀 아트 캐릭터 합성 페이지
라우터 시스템과 레이아웃 추상화를 사용하는 새로운 구조
"""
import streamlit as st
from PIL import Image
from datetime import datetime
import io
import zipfile
from typing import Dict, Any, List
import concurrent.futures
import threading

from app.core.router import PageSpec
from app.modules.image_integration import LLMImageProcessor
from app.modules.image_utils import ImageUtils
from app.modules.asset_manager import get_asset_manager
from app.utils.logger import setup_logger


class PixelArtEditorPage:
    """픽셀 아트 캐릭터 합성 페이지"""
    
    # 페이지 메타데이터
    spec = PageSpec(
        name="픽셀 아트 합성",
        icon="🎨",
        order=10,
        requires_api_key=True
    )
    
    def __init__(self):
        self.logger = setup_logger('pixel_art_editor')
        self.default_style = "기본 스타일"
        self.asset_manager = get_asset_manager()
    
    def render(self, ctx: Dict[str, Any]) -> None:
        """
        페이지 렌더링
        
        Args:
            ctx: 애플리케이션 컨텍스트
        """
        # 컨텍스트에서 필요한 것들 추출
        from app.core.config import APIConfig
        api_key = APIConfig.get_gemini_api_key()
        layout_factory = ctx.get('layout_factory')
        
        # 페이지 제목
        st.subheader("🎨 픽셀 아트 캐릭터 합성")
        st.info("📸 셀카와 🎭 캐릭터를 선택해주세요!")
        
        
        # 2열 레이아웃 생성 (셀카 | 캐릭터선택)
        upload_layout = layout_factory.create_two_column(1, 1)
        
        # 변수 초기화
        uploaded_selfie = None
        selected_character = None
        
        # 첫 번째 열: 셀카 업로드
        with upload_layout.use_slot("left"):
            st.markdown("### 📸 셀카")
            uploaded_selfie = st.file_uploader(
                "최소 상반신까지는 보이는 정면의 사진을 업로드하세요.",
                type=['jpg', 'jpeg', 'png', 'bmp', 'webp'],
                key="selfie_upload",
                help="얼굴이 잘 보이는 셀카를 선택하세요"
            )
            
            if uploaded_selfie:
                if ImageUtils.validate_image_file(uploaded_selfie):
                    selfie_image = Image.open(uploaded_selfie)
                    selfie_image = ImageUtils.resize_image_if_needed(selfie_image, 512)
                    st.image(selfie_image, caption=uploaded_selfie.name, use_container_width=True)
                else:
                    st.error("❌ 유효하지 않은 이미지 파일입니다.")
        
        # 두 번째 열: 캐릭터 선택
        with upload_layout.use_slot("right"):
            st.markdown("### 🎭 캐릭터 선택")
            selected_character = self.asset_manager.display_character_selector(key="character_select")
            
            if selected_character:
                self.asset_manager.display_character_preview(selected_character, "선택된 캐릭터")
        
        
        # 스타일 정보 표시
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 이미지 처리
        self._handle_two_column_input(
            uploaded_selfie, selected_character, 
            api_key, layout_factory
        )
    
    def _handle_two_column_input(self, selfie_file, character_name: str, api_key: str, layout_factory) -> None:
        """2열 입력 처리"""
        # 필수 입력 체크
        if not selfie_file or not character_name:
            if selfie_file or character_name:
                st.info("📋 모든 항목을 선택해주세요: 셀카, 캐릭터")
            return
        
        st.divider()
        
        # 합성 버튼
        col_center = st.columns([1, 2, 1])[1]
        with col_center:
            if st.button("🎨 픽셀 아트 캐릭터 합성 시작", type="primary", use_container_width=True):
                if not api_key:
                    st.error("❌ Gemini API 키가 설정되지 않았습니다.")
                    st.info("💡 API 키를 설정 파일에 추가해주세요.")
                else:
                    self._process_two_column_images(selfie_file, character_name, api_key)
    
    def _handle_image_upload(self, file1, file2, api_key: str, layout_factory) -> None:
        """이미지 업로드 처리 (기존 호환성 유지)"""
        if not (file1 or file2):
            return
        
        st.subheader("🖼️ 업로드된 이미지 미리보기")
        
        # 미리보기용 2열 레이아웃
        preview_layout = layout_factory.create_two_column(1, 1)
        
        image1, image2 = None, None
        
        with preview_layout.use_slot("left"):
            if file1:
                if ImageUtils.validate_image_file(file1):
                    image1 = Image.open(file1)
                    image1 = ImageUtils.resize_image_if_needed(image1, 1024)
                    st.image(image1, caption=file1.name, use_container_width=True)
                else:
                    st.error("❌ 유효하지 않은 이미지 파일입니다.")
        
        with preview_layout.use_slot("right"):
            if file2:
                if ImageUtils.validate_image_file(file2):
                    image2 = Image.open(file2)
                    image2 = ImageUtils.resize_image_if_needed(image2, 1024)
                    st.image(image2, caption=file2.name, use_container_width=True)
                else:
                    st.error("❌ 유효하지 않은 이미지 파일입니다.")
        
        # 합성 버튼
        if image1 and image2:
            st.divider()
            
            col_center = st.columns([1, 2, 1])[1]
            with col_center:
                if st.button("🎨 픽셀 아트 캐릭터 합성 시작", type="primary", use_container_width=True):
                    if not api_key:
                        st.error("❌ Gemini API 키가 설정되지 않았습니다.")
                        st.info("💡 API 키를 설정 파일에 추가해주세요.")
                    else:
                        # make_sample_image.py와 동일한 순서: 픽셀 캐릭터 → 참고 사진
                        # image1이 픽셀 캐릭터, image2가 참고 사진이라고 가정
                        self._process_images(image1, image2, api_key)
    
    def _generate_single_image(self, processor: LLMImageProcessor, selfie_image: Image.Image, 
                              pixel_character_image: Image.Image, enhanced_style: str, 
                              character_name: str, index: int) -> Dict[str, Any]:
        """단일 이미지 생성 (병렬 처리용)"""
        try:
            self.logger.info(f"이미지 생성 시작 #{index + 1}")
            # 각 스레드에서 이미지의 안전한 복사본을 사용
            # BytesIO를 통해 완전히 독립적인 이미지 생성
            
            # 셀카 이미지 복사본 생성
            selfie_buffer = io.BytesIO()
            selfie_image.save(selfie_buffer, format='PNG')
            selfie_buffer.seek(0)
            selfie_copy = Image.open(selfie_buffer)
            selfie_copy.load()
            
            # 픽셀 캐릭터 이미지 복사본 생성
            pixel_buffer = io.BytesIO()
            pixel_character_image.save(pixel_buffer, format='PNG')
            pixel_buffer.seek(0)
            pixel_copy = Image.open(pixel_buffer)
            pixel_copy.load()
            
            # 비동기 메소드를 동기적으로 호출
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                merged_image = loop.run_until_complete(
                    processor.analyze_and_merge_images(pixel_copy, selfie_copy, character_name)
                )
            finally:
                loop.close()
            if merged_image:
                saved_path = ImageUtils.save_pil_image(merged_image)
                self.logger.info(f"이미지 생성 완료 #{index + 1}")
                return {
                    'success': True,
                    'image': merged_image,
                    'path': saved_path,
                    'index': index
                }
            else:
                self.logger.warning(f"이미지 생성 실패 #{index + 1}")
                return {'success': False, 'index': index}
        except Exception as e:
            self.logger.error(f"이미지 생성 오류 #{index + 1}: {str(e)}")
            return {'success': False, 'index': index, 'error': str(e)}
    
    def _process_two_column_images(self, selfie_file, character_name: str, api_key: str) -> None:
        """2열 입력으로 4장의 이미지를 동시에 처리"""
        ImageUtils.create_directories()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # 1. 셀카 이미지 처리
            status_text.text("📸 셀카 이미지 처리 중...")
            progress_bar.progress(10)
            
            if not ImageUtils.validate_image_file(selfie_file):
                st.error("❌ 유효하지 않은 셀카 파일입니다.")
                return
            
            # 파일 포인터를 처음으로 되돌리고 이미지 열기
            selfie_file.seek(0)
            selfie_image = Image.open(selfie_file)
            # 이미지를 완전히 로드 (lazy loading 방지)
            selfie_image.load()
            # RGB로 변환 (RGBA나 다른 모드일 경우를 대비)
            if selfie_image.mode not in ('RGB', 'L'):
                selfie_image = selfie_image.convert('RGB')
            selfie_image = ImageUtils.resize_image_if_needed(selfie_image, 1024)
            
            # 2. 픽셀 캐릭터 이미지 로드 (pixel_character_image 폴더에서)
            status_text.text(f"🎭 픽셀 캐릭터 이미지 로드 중... ({character_name})")
            progress_bar.progress(15)
            
            # pixel_character_image 폴더에서 픽셀화된 캐릭터 이미지 로드
            pixel_character_image = self.asset_manager.load_pixel_character_image(character_name)
            if not pixel_character_image:
                st.error(f"❌ 픽셀 캐릭터 이미지를 찾을 수 없습니다: {character_name}_픽셀.png")
                st.info("픽셀 캐릭터 에셋이 아직 준비되지 않았습니다. pixel_character_image 폴더에 해당 캐릭터의 픽셀화된 이미지를 추가해주세요.")
                available_characters = self.asset_manager.get_pixel_character_options()
                if available_characters:
                    st.warning(f"현재 사용 가능한 픽셀 캐릭터: {', '.join(available_characters)}")
                else:
                    st.warning("아직 사용 가능한 픽셀 캐릭터가 없습니다.")
                return
            
            # 이미지 복사본 생성 및 RGB 변환 (멀티스레드 환경에서 안전하게 사용)
            pixel_character_image = pixel_character_image.copy()
            # 이미지를 완전히 로드 (lazy loading 방지)
            pixel_character_image.load()
            if pixel_character_image.mode not in ('RGB', 'L'):
                pixel_character_image = pixel_character_image.convert('RGB')
            pixel_character_image = ImageUtils.resize_image_if_needed(pixel_character_image, 1024)
            
            # 3. Gemini AI 모델 초기화 (4개의 프로세서 생성)
            status_text.text("🔧 Gemini AI 모델 초기화 중...")
            progress_bar.progress(20)
            
            processors = [LLMImageProcessor() for _ in range(4)]
            
            # 4. 4장의 픽셀 아트 캐릭터 동시 합성
            status_text.text(f"🎨 4장의 메이플스토리 캐릭터 생성 중... ({character_name})")
            progress_bar.progress(30)
            
            # 캐릭터 정보를 스타일에 추가
            enhanced_style = f"{self.default_style} (캐릭터: {character_name})"
            
            # 병렬로 4장의 이미지 생성
            generated_images = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                # 4개의 작업을 동시에 제출
                futures = []
                for i in range(4):
                    future = executor.submit(
                        self._generate_single_image,
                        processors[i], selfie_image, pixel_character_image,
                        enhanced_style, character_name, i
                    )
                    futures.append(future)
                
                # 진행 상황 업데이트
                completed = 0
                for future in concurrent.futures.as_completed(futures):
                    completed += 1
                    progress = 30 + (completed * 15)  # 30% ~ 90%
                    status_text.text(f"🎨 이미지 생성 중... ({completed}/4 완료)")
                    progress_bar.progress(progress)
                    
                    result = future.result()
                    if result['success']:
                        generated_images.append(result)
            
            # 성공한 이미지들을 인덱스 순으로 정렬
            generated_images.sort(key=lambda x: x['index'])
            
            if generated_images:
                status_text.text("💾 결과 저장 중...")
                progress_bar.progress(95)
                
                status_text.text(f"✅ {len(generated_images)}장의 픽셀 아트 캐릭터 합성 완료!")
                progress_bar.progress(100)
                
                # 결과 표시 (2x2 그리드)
                self._display_grid_result(generated_images, character_name)
                
                # 오래된 파일 정리
                ImageUtils.cleanup_old_files("files/uploads")
                ImageUtils.cleanup_old_files("files/merged_images")
            else:
                st.error("❌ 모든 픽셀 아트 캐릭터 합성에 실패했습니다.")
                
        except Exception as e:
            st.error(f"❌ 오류가 발생했습니다: {str(e)}")
            st.info("API 키가 올바른지 확인해주세요.")
            self.logger.error(f"2열 이미지 처리 오류: {str(e)}")
        
        finally:
            progress_bar.empty()
            status_text.empty()
    
    def _process_images(self, pixel_character_image: Image.Image, reference_photo: Image.Image, api_key: str) -> None:
        """이미지 처리 (픽셀 캐릭터 + 참고 사진 순서)"""
        ImageUtils.create_directories()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🔧 Gemini AI 모델 초기화 중...")
            progress_bar.progress(20)
            
            processor = LLMImageProcessor()
            
            status_text.text("🎨 픽셀 아트 캐릭터 합성 중... (시간이 다소 걸릴 수 있습니다)")
            progress_bar.progress(40)
            
            # 비동기 메소드 호출을 위한 asyncio 사용
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                merged_image = loop.run_until_complete(
                    processor.analyze_and_merge_images(pixel_character_image, reference_photo, character_name)
                )
            finally:
                loop.close()
            progress_bar.progress(80)
            
            if merged_image:
                status_text.text("💾 결과 저장 중...")
                saved_path = ImageUtils.save_pil_image(merged_image)
                progress_bar.progress(100)
                
                status_text.text("✅ 픽셀 아트 캐릭터 합성 완료!")
                
                # 결과 표시
                self._display_result(merged_image, "업로드 이미지", "기본", saved_path)
                
                # 오래된 파일 정리
                ImageUtils.cleanup_old_files("files/uploads")
                ImageUtils.cleanup_old_files("files/merged_images")
            else:
                st.error("❌ 픽셀 아트 캐릭터 합성에 실패했습니다.")
                
        except Exception as e:
            st.error(f"❌ 오류가 발생했습니다: {str(e)}")
            st.info("API 키가 올바른지 확인해주세요.")
        
        finally:
            progress_bar.empty()
            status_text.empty()
    
    def _display_grid_result(self, generated_images: List[Dict[str, Any]], character_name: str) -> None:
        """결과 표시"""
        st.subheader("🎉 합성 결과")
        
        # 2x2 그리드 레이아웃 생성
        st.markdown("### 생성된 이미지")
        
        # 이미지를 2개씩 나누어서 행 생성
        for row_idx in range(0, len(generated_images), 2):
            cols = st.columns(2)
            
            # 첫 번째 열
            if row_idx < len(generated_images):
                with cols[0]:
                    img_data = generated_images[row_idx]
                    st.image(img_data['image'], caption=f"이미지 {row_idx + 1}", use_container_width=True)
            
            # 두 번째 열
            if row_idx + 1 < len(generated_images):
                with cols[1]:
                    img_data = generated_images[row_idx + 1]
                    st.image(img_data['image'], caption=f"이미지 {row_idx + 2}", use_container_width=True)
        
        st.divider()
        
        # 개별 다운로드 버튼들
        st.markdown("### 📥 개별 다운로드")
        download_cols = st.columns(4)
        
        for idx, img_data in enumerate(generated_images):
            with download_cols[idx % 4]:
                img_byte_arr = io.BytesIO()
                img_data['image'].save(img_byte_arr, format='PNG', quality=95)
                img_byte_arr = img_byte_arr.getvalue()
                
                safe_character = character_name.replace(" ", "_")
                filename = f"pixel_{safe_character}_{idx+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                
                st.download_button(
                    label=f"📥 이미지 {idx + 1}",
                    data=img_byte_arr,
                    file_name=filename,
                    mime="image/png",
                    key=f"download_{idx}",
                    use_container_width=True
                )
        
        # 전체 이미지 ZIP 다운로드
        st.divider()
        st.markdown("### 📦 전체 다운로드")
        
        # ZIP 파일 생성
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, img_data in enumerate(generated_images):
                img_byte_arr = io.BytesIO()
                img_data['image'].save(img_byte_arr, format='PNG', quality=95)
                
                safe_character = character_name.replace(" ", "_")
                filename = f"pixel_{safe_character}_{idx+1}.png"
                
                zip_file.writestr(filename, img_byte_arr.getvalue())
        
        zip_buffer.seek(0)
        
        st.download_button(
            label="📦 모든 이미지 다운로드 (ZIP)",
            data=zip_buffer.getvalue(),
            file_name=f"pixel_{character_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True
        )
        
        # 세션 상태에 저장 (호환성 유지)
        if 'processed_images' not in st.session_state:
            st.session_state.processed_images = []
        
        if 'synthesized_images' not in st.session_state:
            st.session_state.synthesized_images = []
        
        # 모든 생성된 이미지를 세션에 저장
        for img_data in generated_images:
            st.session_state.synthesized_images.append({
                'image': img_data['image'],
                'character': character_name,
                'style': self.default_style,
                'path': img_data['path'],
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'filename': f"pixel_character_{character_name}_{img_data['index']+1}.png"
            })
            
            st.session_state.processed_images.append({
                'character': character_name,
                'style': self.default_style,
                'path': img_data['path'],
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    
    def _display_result(self, merged_image: Image.Image, character_name: str, saved_path: str) -> None:
        """결과 표시 (단일 이미지용 - 기존 호환성 유지)"""
        st.subheader("🎉 합성 결과")
        
        # 결과 이미지 표시
        st.image(merged_image, use_container_width=True)
         
        # 다운로드 버튼
        img_byte_arr = io.BytesIO()
        merged_image.save(img_byte_arr, format='PNG', quality=95)
        img_byte_arr = img_byte_arr.getvalue()
        
        # 파일명에 캐릭터 정보 포함
        safe_character = character_name.replace(" ", "_")
        filename = f"pixel_character_{safe_character}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        st.download_button(
            label="📥 캐릭터 다운로드",
            data=img_byte_arr,
            file_name=filename,
            mime="image/png",
            type="secondary",
            use_container_width=True
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 처리 기록에 추가
        if 'processed_images' not in st.session_state:
            st.session_state.processed_images = []
        
        # 합성된 이미지를 세션에 저장 (동영상 생성에서 사용)
        if 'synthesized_images' not in st.session_state:
            st.session_state.synthesized_images = []
        
        # 이미지 데이터와 메타정보 저장
        st.session_state.synthesized_images.append({
            'image': merged_image,  # PIL Image 객체
            'character': character_name,
            'style': self.default_style,
            'path': saved_path,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'filename': f"pixel_character_{character_name}.png"
        })
        
        # 기존 processed_images에도 추가 (호환성 유지)
        st.session_state.processed_images.append({
            'character': character_name,
            'style': self.default_style,
            'path': saved_path,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })


# 페이지 인스턴스 생성 (라우터가 자동으로 발견)
page = PixelArtEditorPage()