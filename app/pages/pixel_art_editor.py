"""
픽셀 아트 캐릭터 합성 페이지
라우터 시스템과 레이아웃 추상화를 사용하는 새로운 구조
"""
import streamlit as st
from PIL import Image
from datetime import datetime
import io
from typing import Dict, Any

from app.core.router import PageSpec
from app.modules.gemini_integration import GeminiImageProcessor
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
        st.info("📸 셀카, 🎭 캐릭터, 😊 얼굴모양을 선택해주세요! (현재는 캡틴만 가능)")
        
        
        # 3열 레이아웃 생성 (셀카 | 캐릭터선택 | 얼굴모양)
        upload_layout = layout_factory.create_three_column(1, 1, 1)
        
        # 변수 초기화
        uploaded_selfie = None
        selected_character = None
        selected_face_shape = None
        
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
        with upload_layout.use_slot("center"):
            st.markdown("### 🎭 캐릭터 선택")
            selected_character = self.asset_manager.display_character_selector(key="character_select")
            
            if selected_character:
                self.asset_manager.display_character_preview(selected_character, "선택된 캐릭터")
        
        # 세 번째 열: 얼굴 모양 선택
        with upload_layout.use_slot("right"):
            st.markdown("### 😊 얼굴 모양")
            selected_face_shape = self.asset_manager.display_face_selector(key="face_shape_select")
            
            if selected_face_shape:
                self.asset_manager.display_face_preview(selected_face_shape, "선택된 얼굴 모양")
        
        # 스타일 정보 표시
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 이미지 처리
        self._handle_three_column_input(
            uploaded_selfie, selected_character, selected_face_shape, 
            api_key, layout_factory
        )
    
    def _handle_three_column_input(self, selfie_file, character_name: str, face_shape: str, api_key: str, layout_factory) -> None:
        """3열 입력 처리"""
        # 필수 입력 체크
        if not selfie_file or not character_name or not face_shape:
            if selfie_file or character_name or face_shape:
                st.info("📋 모든 항목을 선택해주세요: 셀카, 캐릭터, 얼굴모양")
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
                    self._process_three_column_images(selfie_file, character_name, face_shape, api_key)
    
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
                        self._process_images(image1, image2, api_key)
    
    def _process_three_column_images(self, selfie_file, character_name: str, face_shape: str, api_key: str) -> None:
        """3열 입력으로 이미지 처리"""
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
            
            selfie_image = Image.open(selfie_file)
            selfie_image = ImageUtils.resize_image_if_needed(selfie_image, 1024)
            
            # 2. 캐릭터+얼굴 조합 이미지 로드
            status_text.text(f"🎭 캐릭터+얼굴 조합 이미지 로드 중... ({character_name}_{face_shape})")
            progress_bar.progress(20)
            
            combination_image = self.asset_manager.get_char_face_combination(character_name, face_shape)
            if not combination_image:
                st.error(f"❌ 조합 이미지를 찾을 수 없습니다: {character_name}_{face_shape}.png")
                st.info("char_face_image 폴더에 해당 조합 이미지가 있는지 확인해주세요.")
                return
            
            combination_image = ImageUtils.resize_image_if_needed(combination_image, 1024)
            
            # 3. Gemini AI 모델 초기화
            status_text.text("🔧 Gemini AI 모델 초기화 중...")
            progress_bar.progress(40)
            
            processor = GeminiImageProcessor(api_key)
            
            # 4. 픽셀 아트 캐릭터 합성 (셀카 + 조합이미지)
            status_text.text(f"🎨 픽셀 아트 캐릭터 합성 중... ({character_name}_{face_shape})")
            progress_bar.progress(60)
            
            # 조합 이미지 정보를 스타일에 추가
            enhanced_style = f"{self.default_style} (조합: {character_name}_{face_shape})"
            
            # 셀카와 조합 이미지로 픽셀 아트 생성 (캐릭터와 얼굴 정보 전달)
            merged_image = processor.create_artistic_merge(selfie_image, combination_image, enhanced_style, character_name, face_shape)
            progress_bar.progress(80)
            
            if merged_image:
                status_text.text("💾 결과 저장 중...")
                saved_path = ImageUtils.save_pil_image(merged_image)
                progress_bar.progress(100)
                
                status_text.text("✅ 픽셀 아트 캐릭터 합성 완료!")
                
                # 결과 표시 (조합 이미지 사용됨을 표시)
                self._display_result(merged_image, f"{character_name}_{face_shape}", "조합이미지", saved_path)
                
                # 오래된 파일 정리
                ImageUtils.cleanup_old_files("files/uploads")
                ImageUtils.cleanup_old_files("files/merged_images")
            else:
                st.error("❌ 픽셀 아트 캐릭터 합성에 실패했습니다.")
                
        except Exception as e:
            st.error(f"❌ 오류가 발생했습니다: {str(e)}")
            st.info("API 키가 올바른지 확인해주세요.")
            self.logger.error(f"3열 이미지 처리 오류: {str(e)}")
        
        finally:
            progress_bar.empty()
            status_text.empty()
    
    def _process_images(self, image1: Image.Image, image2: Image.Image, api_key: str) -> None:
        """이미지 처리"""
        ImageUtils.create_directories()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🔧 Gemini AI 모델 초기화 중...")
            progress_bar.progress(20)
            
            processor = GeminiImageProcessor(api_key)
            
            status_text.text("🎨 픽셀 아트 캐릭터 합성 중... (시간이 다소 걸릴 수 있습니다)")
            progress_bar.progress(40)
            
            merged_image = processor.create_artistic_merge(image1, image2, self.default_style)
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
    
    def _display_result(self, merged_image: Image.Image, character_name: str, face_shape: str, saved_path: str) -> None:
        """결과 표시"""
        st.subheader("🎉 합성 결과")
        
        # 결과 이미지 표시
        st.image(merged_image, use_container_width=True)
         
        # 다운로드 버튼
        img_byte_arr = io.BytesIO()
        merged_image.save(img_byte_arr, format='PNG', quality=95)
        img_byte_arr = img_byte_arr.getvalue()
        
        # 파일명에 캐릭터와 얼굴모양 정보 포함
        safe_character = character_name.replace(" ", "_")
        safe_face_shape = face_shape.replace(" ", "_")
        filename = f"pixel_character_{safe_character}_{safe_face_shape}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
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
            'face_shape': face_shape,
            'style': self.default_style,
            'path': saved_path,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'filename': f"pixel_character_{character_name}_{face_shape}.png"
        })
        
        # 기존 processed_images에도 추가 (호환성 유지)
        st.session_state.processed_images.append({
            'character': character_name,
            'face_shape': face_shape,
            'style': self.default_style,
            'path': saved_path,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })


# 페이지 인스턴스 생성 (라우터가 자동으로 발견)
page = PixelArtEditorPage()