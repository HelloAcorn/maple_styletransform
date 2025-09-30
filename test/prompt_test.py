#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import json
import base64
import mimetypes
import yaml
import time
from datetime import datetime
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# === 경로 설정 ===
IMG_DIR = "/home/acorn/maple_styletransform/test/input_Image"
PROMPT_YAML = "/home/acorn/maple_styletransform/app/prompt/human_explain.yaml"

# === 폴더 내 모든 이미지 선택 ===
def list_all_images(img_dir: str):
    exts = ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp")
    candidates = []
    for pat in exts:
        candidates.extend(glob.glob(os.path.join(img_dir, pat)))
    if not candidates:
        raise FileNotFoundError(f"No image found in: {img_dir}")
    return sorted(candidates)

# === 로컬 이미지를 Gemini API 형태로 변환 ===
def local_image_to_gemini_part(path: str) -> dict:
    with open(path, "rb") as f:
        image_data = f.read()
    return {
        "mime_type": "image/png",
        "data": image_data
    }

# === YAML 프롬프트 로드 ===
def load_prompt(yaml_path: str) -> str:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for k in ("prompt", "base_prompt", "text", "instruction"):
            if k in data and isinstance(data[k], str):
                return data[k]
    return json.dumps(data, ensure_ascii=False)

def main():
    print(f"🚀 Gemini 2.5 Flash Lite Preview 이미지 분석 테스트 시작")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 전체 시작 시간
    total_start_time = time.time()
    
    # 1) 이미지 전체 리스트
    img_paths = list_all_images(IMG_DIR)
    print(f"📸 발견된 이미지: {len(img_paths)}개")
    
    # 2) 프롬프트 로드
    user_prompt = load_prompt(PROMPT_YAML)
    print(f"📝 프롬프트 로드 완료")
    print()

    # 3) Gemini API 설정 및 클라이언트
    # API 키 로드
    api_key_file = "/home/acorn/maple_styletransform/app/core/.api_key"
    try:
        with open(api_key_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # GOOGLE_API_KEY 추출
            for line in content.split('\n'):
                if line.startswith('GOOGLE_API_KEY'):
                    api_key = line.split('=')[1].strip().strip('"')
                    break
            else:
                raise ValueError("GOOGLE_API_KEY를 찾을 수 없습니다.")
    except Exception as e:
        print(f"❌ API 키 로드 실패: {e}")
        return
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025')
    print(f"🤖 Gemini 모델 초기화 완료")

    # 4) 각 이미지에 대해 분석 실행
    successful_analyses = 0
    total_api_time = 0
    
    for i, img_path in enumerate(img_paths, 1):
        filename = os.path.basename(img_path)
        print(f"[{i}/{len(img_paths)}] 📷 분석 중: {filename}")
        
        try:
            # 이미지 변환 시간 측정
            convert_start = time.time()
            image_part = local_image_to_gemini_part(img_path)
            convert_time = time.time() - convert_start
            
            # API 호출 시간 측정
            api_start = time.time()
            response = model.generate_content(
                [user_prompt, image_part],
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
            api_time = time.time() - api_start
            total_api_time += api_time
            
            out = response.text
            successful_analyses += 1
            
            print(f"✅ 분석 완료 (변환: {convert_time:.2f}초, API: {api_time:.2f}초)")
            print(f"=== 결과: {filename} ===")
            print(out)
            print()
            
        except Exception as e:
            print(f"❌ 분석 실패: {filename} - {str(e)}")
            print()
    
    # 전체 완료 시간
    total_end_time = time.time()
    total_time = total_end_time - total_start_time
    
    # 결과 요약
    print("=" * 60)
    print("📊 분석 결과 요약")
    print(f"⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 성공률: {successful_analyses}/{len(img_paths)}개 ({successful_analyses/len(img_paths)*100:.1f}%)")
    print(f"⏱️  총 소요시간: {total_time:.2f}초")
    print(f"🔥 총 API 호출시간: {total_api_time:.2f}초")
    if successful_analyses > 0:
        print(f"📈 평균 API 응답시간: {total_api_time/successful_analyses:.2f}초")
    print("=" * 60)

if __name__ == "__main__":
    main()
