# 🎨 AI 멀티미디어 스튜디오

Gemini 2.0 Flash Image와 BytePlus ModelArk Seedance 1.0을 사용하여 이미지 합성과 동영상 생성을 제공하는 종합 AI 미디어 제작 도구입니다.

## ✨ 주요 기능

### 🎨 이미지 합성 (Gemini 2.0 Flash)
- 🖼️ **직관적인 이미지 업로드**: 드래그 앤 드롭으로 간편한 이미지 업로드
- 🎨 **다양한 합성 스타일**: 자연스러운 합성, 예술적 합성, 완전한 융합, 콜라주 스타일
- 🔧 **자동 이미지 최적화**: 큰 이미지 자동 리사이즈로 처리 속도 향상
- 💾 **결과 다운로드**: 고품질 PNG 형태로 합성 결과 저장

### 🎬 동영상 생성 (BytePlus Seedance 1.0)
- 📹 **이미지-동영상 변환**: 단일 이미지에서 생동감 있는 동영상 생성
- 🎭 **다양한 동영상 스타일**: 자연스러운, 영화적, 부드러운, 역동적, 예술적, 현실적
- ⚙️ **세밀한 설정 제어**: 해상도, 길이, 프롬프트 커스터마이징
- 📱 **다양한 해상도 지원**: 16:9, 9:16, 1:1 등 소셜미디어 최적화

### 🛠️ 공통 기능
- 📊 **실시간 처리 상태**: 진행 상황 표시 및 상세한 미디어 정보 제공
- 🗂️ **탭 기반 인터페이스**: 이미지 합성과 동영상 생성을 구분된 탭으로 제공
- 📝 **처리 기록 관리**: 이전 작업 내역 추적 및 관리
- 🔄 **자동 파일 정리**: 오래된 파일 자동 삭제로 저장 공간 관리

## 🛠️ 설치 및 설정

### 1. 저장소 클론
```bash
git clone <repository-url>
cd maple_styletransform
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. API 키 설정

#### Gemini API (이미지 합성용)
1. [Google AI Studio](https://aistudio.google.com/)에 접속
2. 'Get API Key' 클릭하여 새 API 키 생성
3. 애플리케이션 사이드바에서 Gemini API 키 입력

#### BytePlus API (동영상 생성용)
- BytePlus API 키는 이미 설정되어 있습니다
- 별도 설정 없이 동영상 생성 기능 바로 사용 가능

### 4. 애플리케이션 실행
```bash
streamlit run main.py
```

## 📁 프로젝트 구조

```
maple_styletransform/
├── app/
│   ├── main.py                   # 메인 Streamlit 애플리케이션
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # 기존 API 설정
│   │   ├── llm_settings.py       # 🆕 LLM 설정 관리
│   │   └── .api_key              # API 키 파일 (Git 제외)
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── llm_factory.py        # LLM 팩토리 패턴
│   │   ├── gemini_integration.py # Gemini API 통합 (업데이트됨)
│   │   └── image_utils.py        # 이미지 처리 유틸리티
│   └── static/
│       ├── uploads/              # 업로드된 이미지 저장
│       └── merged_images/        # 합성 결과 저장
├── requirements.txt              # Python 의존성
├── .env.example                  # 환경변수 예시
└── README.md                     # 프로젝트 문서
```

## 🎯 사용 방법

### 1. API 키 입력
- 사이드바에서 Gemini API 키를 입력합니다
- API 키는 `AIza...`로 시작하는 형태입니다

### 2. 이미지 업로드
- 첫 번째와 두 번째 이미지를 각각 업로드합니다
- 지원 형식: JPG, JPEG, PNG, BMP, WebP
- 최대 파일 크기: 10MB

### 3. 합성 스타일 선택
- **🌿 자연스러운 합성**: 현실적이고 자연스러운 결합
- **🎨 예술적 합성**: 창의적이고 예술적인 표현
- **✨ 완전한 융합**: 경계가 없는 완전한 통합
- **🖼️ 콜라주 스타일**: 콜라주 형태의 조화로운 배치

### 4. 합성 실행
- '🚀 이미지 합성 시작' 버튼 클릭
- 처리 과정이 진행 상황 표시줄로 표시됩니다
- 완료 후 결과 이미지 확인 및 다운로드

## ⚙️ 고급 설정

### 이미지 최적화
- **자동 리사이즈**: 큰 이미지를 자동으로 최적화
- **최대 크기 조절**: 512px~2048px 범위에서 설정 가능

### 파일 관리
- 자동으로 오래된 파일 정리 (최대 50개 파일 유지)
- 업로드 및 결과 파일 분리 저장

## 🔧 기술 스택

- **Frontend**: Streamlit
- **AI Models**: 
  - Google Gemini 2.5 Flash Image (이미지 편집)
  - OpenAI GPT-4o (텍스트 생성, 폴백)
  - BytePlus Seedance 1.0 (동영상 생성)
- **LLM Framework**: LangChain (OpenAI 통합)
- **Image Processing**: Pillow (PIL)
- **Backend**: Python 3.8+

## 📝 API 사용량 주의사항

- **Gemini API**: 이미지 편집 시 사용량에 따라 요금 부과
- **OpenAI API**: 텍스트 생성 및 폴백 시 토큰 기반 요금 부과
- 대용량 이미지나 복잡한 합성 작업은 처리 시간이 오래 걸릴 수 있습니다
- API 할당량 초과 시 자동 폴백 또는 오류가 발생할 수 있습니다

## 🐛 문제 해결

### 일반적인 오류
1. **API 키 오류**: OpenAI/Gemini API 키가 올바른지 확인
2. **이미지 업로드 실패**: 파일 형식과 크기 확인
3. **합성 실패**: 인터넷 연결 상태 확인, 폴백 로그 확인
4. **LLM 폴백 오류**: 로그에서 어떤 제공자가 실패했는지 확인

### 성능 최적화
- 이미지 크기를 1024px 이하로 설정
- 안정적인 인터넷 연결 환경에서 사용
- 동시에 여러 합성 작업 실행 지양

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🚀 Google Cloud Run 배포

### 1. 저장소 연결을 통한 자동 배포 (권장)

#### GitHub/GitLab 저장소 연결
1. Google Cloud Console → Cloud Run 이동
2. "Create Service" → "Deploy from source" 선택
3. GitHub/GitLab 저장소 연결
4. `cloudbuild.yaml` 파일이 자동으로 감지됨
5. 환경 변수에서 `GOOGLE_API_KEY` 설정

#### 자동 배포 흐름
- 코드 푸시 → Cloud Build 트리거 → 자동 빌드 & 배포
- `main` 브랜치 푸시 시 자동으로 프로덕션 배포

### 2. Cloud Build 트리거 설정
```yaml
# cloudbuild.yaml 파일이 모든 배포 설정을 관리
# 저장소 연결 시 자동으로 실행됩니다
```

### 배포 설정
- **메모리**: 2GB (AI 모델 처리를 위해)
- **CPU**: 2 vCPU (병렬 처리를 위해)
- **타임아웃**: 300초 (이미지 생성 시간 고려)
- **동시성**: 80 (동시 요청 처리)
- **최대 인스턴스**: 10개

## 🤝 기여

버그 리포트, 기능 제안, 풀 리퀘스트를 환영합니다!

---

**개발자**: AI 이미지 합성 전문팀  
**버전**: 2.0.0  
**최종 업데이트**: 2024년
