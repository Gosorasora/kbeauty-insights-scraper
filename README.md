# K-Beauty 리테일 인사이트 분석

Amazon K-Beauty 제품 리뷰 데이터를 수집하고 Azure OpenAI 기반 RAG 시스템으로 분석하는 프로젝트입니다.

## 🎯 프로젝트 목표

해외 고객들의 K-Beauty 제품 리뷰 데이터를 AI가 분석하여 **글로벌 고객이 K-Beauty 브랜드에 기대하는 포인트**를 자동으로 알려주는 에이전트 개발

## 🚀 빠른 시작

### 버전 선택

프로젝트는 3가지 버전으로 제공됩니다:

| 버전 | 비용 | 용도 | 문서 |
|------|------|------|------|
| **v1 (로컬)** | $10-30/월 | 개발, 학습 | [V1_LOCAL_DEV.md](docs/V1_LOCAL_DEV.md) |
| **v2 (최적화)** | $120-145/월 | 공모전, MVP, 5만개+ 데이터 | [V2_OPTIMIZED.md](docs/V2_OPTIMIZED.md) |
| **v3 (프로덕션)** | $700-1,000/월 | 상용 서비스 | [V3_PRODUCTION.md](docs/V3_PRODUCTION.md) |

**권장**: 공모전 준비 중이라면 **v2 (Cognitive Search)** 추천합니다.

### v1: 로컬 개발 (현재 권장)

```bash
# 1. 라이브러리 설치
pip install -r requirements_azure.txt

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에 Azure OpenAI 정보 입력

# 3. 데이터 전처리
python preprocess_data.py

# 4. Vector DB 구축
python build_vector_db.py

# 5. RAG 에이전트 실행
python azure_rag_agent.py
```

**비용**: $10-30/월 (Azure OpenAI API만)  
**상세 가이드**: [V1_LOCAL_DEV.md](docs/V1_LOCAL_DEV.md)

### v2: Azure 배포 (공모전 제출용)

```bash
# Terraform으로 자동 배포
cd terraform
cp variables.tfvars.example variables.tfvars
# variables.tfvars 편집

terraform init
terraform apply -var-file="variables.tfvars"

# Cognitive Search 인덱스 생성
python migrate_to_cognitive_search.py
```

**비용**: $120-145/월 (Azure AI Search 포함)  
**성능**: 검색 20-50ms, 동시 사용자 50명+  
**상세 가이드**: [V2_OPTIMIZED.md](docs/V2_OPTIMIZED.md)

## 📊 수집 데이터

- **리뷰 수**: 5,686개
- **제품 수**: 280개
- **데이터 소스**: Amazon US "Korean Skincare"
- **수집 기간**: 2025-12-22

### 데이터 파일
- `results/amazon_reviews.csv` - 원본 리뷰 데이터
- `results/amazon_reviews_clean.csv` - 전처리된 리뷰 데이터
- `results/amazon_products.csv` - 제품 메타데이터

## 🏗️ 시스템 아키텍처

```
User ──HTTPS──▶ App Service ──Vector Query──▶ AI Search
                     │
                     └──API Call──▶ Azure OpenAI (East US)
```

**핵심 구성**:
- **App Service (B1)**: RAG Agent 실행 (Korea Central)
- **Azure AI Search**: Vector 검색 엔진 (Korea Central)  
- **Azure OpenAI**: 임베딩 + GPT 모델 (East US)
- **Blob Storage**: 데이터 저장 (Korea Central)

## 💡 주요 기능

### ✅ Phase 1: 데이터 수집 (완료)
- Amazon 제품 검색 및 리뷰 수집
- 별점, 유용함 투표, 검증된 구매 정보 수집
- CSV 형식으로 저장
- Ctrl+C 중단 시 자동 저장

### ✅ Phase 2: RAG 시스템 (완료)
- Azure OpenAI 기반 임베딩 생성
- ChromaDB Vector Database 구축
- 자연어 질문 답변 AI 에이전트
- 관련 리뷰 검색 및 인사이트 제공

### 🔄 Phase 3-6: 진행 예정
- 고급 텍스트 분석 (감성 분석, 토픽 모델링)
- 시각화 대시보드
- 데이터 소스 확장
- 자동화 및 스케줄링

## 📁 프로젝트 구조

```
.
├── amazon_scraper.py              # Amazon 크롤러
├── preprocess_data.py             # 데이터 전처리
├── build_vector_db.py             # Vector DB 구축
├── azure_rag_agent.py             # RAG AI 에이전트
├── analyze_trends.py              # 기본 트렌드 분석
├── requirements.txt               # 크롤러 의존성
├── requirements_azure.txt         # Azure RAG 의존성
├── .env.example                   # 환경 변수 예시
├── README.md                      # 프로젝트 소개
├── results/                       # 크롤링 결과 (gitignore)
│   ├── amazon_reviews.csv
│   ├── amazon_reviews_clean.csv
│   └── amazon_products.csv
├── chroma_db/                     # Vector Database (gitignore)
├── docs/                          # 문서 (gitignore)
│   ├── PROJECT_STATUS.md          # 프로젝트 현황
│   ├── TODO.md                    # 작업 목록
│   ├── IMPLEMENTATION_GUIDE.md    # 구현 가이드
│   ├── AZURE_SETUP_GUIDE.md       # Azure 설정 가이드
│   └── PROJECT_SUMMARY.md         # 작업 히스토리
└── chrome_profile/                # Chrome 프로필 (gitignore)
```

## 🤖 사용 예시

### 데이터 수집 (Chrome Remote Debugging)

```bash
# Chrome 디버그 모드 실행
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome_debug_profile

# Amazon 로그인 후 크롤러 실행
python3 amazon_scraper.py
```

### RAG AI 에이전트 사용

```python
from azure_rag_agent import KBeautyRAGAgent

# 에이전트 초기화
agent = KBeautyRAGAgent()

# 질문하기
agent.ask("요즘 미국에서 인기 있는 진정 토너는 무엇인가요?")
agent.ask("Snail Mucin 제품에 대한 고객 반응은 어떤가요?")
agent.ask("건조한 피부에 좋은 K-Beauty 제품을 추천해주세요.")

# 대화형 모드
agent.interactive_mode()
```

## 📈 예시 질문

1. 요즘 미국에서 인기 있는 진정 토너는 무엇인가요?
2. Snail Mucin 제품에 대한 고객 반응은 어떤가요?
3. 건조한 피부에 좋은 K-Beauty 제품을 추천해주세요.
4. Niacinamide 성분이 들어간 제품 중 평점이 높은 것은?
5. 40대 이상 고객들이 선호하는 제품은?
6. 최근 3개월간 급상승한 성분 트렌드는?
7. 경쟁사 대비 아모레퍼시픽 제품의 강점은?

## 🛠️ 기술 스택

### 데이터 수집
- Python 3.9+
- Selenium 4.39.0
- BeautifulSoup4
- Pandas

### RAG 시스템
- Azure OpenAI (GPT-4, text-embedding-ada-002)
- ChromaDB (Vector Database)
- LangChain
- OpenAI Python SDK

## 💰 비용 예상

### Azure OpenAI 사용 시
- **초기 구축**: $1 (임베딩 생성)
- **질문당**: $0.09 (GPT-4 기준)
- **월간 운영** (100 질문/일): $270

### 비용 절감 방법
- GPT-3.5-turbo 사용 (비용 1/10)
- 자주 묻는 질문 캐싱
- 로컬 LLM 사용 (Ollama)

## 📝 상세 문서

### 버전별 가이드
- **v1 (로컬 개발)**: [V1_LOCAL_DEV.md](docs/V1_LOCAL_DEV.md) - 로컬 환경 설정 및 개발
- **v2 (최적화)**: [V2_OPTIMIZED.md](docs/V2_OPTIMIZED.md) - Azure 배포 (공모전/MVP)
- **v3 (프로덕션)**: [V3_PRODUCTION.md](docs/V3_PRODUCTION.md) - 상용 서비스 아키텍처

### 프로젝트 문서
- **비용 비교**: [COST_COMPARISON.md](docs/COST_COMPARISON.md) - 3가지 버전 비용 비교
- **아키텍처**: [ARCHITECTURE.md](docs/ARCHITECTURE.md) - 시스템 아키텍처 상세
- **Azure 설정**: [AZURE_SETUP_GUIDE.md](docs/AZURE_SETUP_GUIDE.md) - Azure OpenAI 설정
- **프로젝트 현황**: [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) - 완료/진행 상황
- **작업 목록**: [TODO.md](docs/TODO.md) - 우선순위별 작업
- **프로젝트 요약**: [PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md) - 전체 히스토리

## 🎯 공모전 어필 포인트

### 기술적 강점
1. ✅ **실시간 데이터**: 직접 수집한 최신 리뷰 데이터
2. ✅ **Azure 기반 RAG**: 엔터프라이즈급 AI 시스템
3. ✅ **확장 가능성**: 모듈화된 구조
4. 🔄 **자동화**: 지속적 업데이트 (진행 예정)

### 비즈니스 가치
1. 🔄 **트렌드 예측**: 성분/제형 트렌드 조기 발견
2. 🔄 **경쟁 분석**: 아모레퍼시픽 vs 경쟁사 비교
3. 🔄 **제품 개발**: 고객 니즈 기반 신제품 기획
4. 🔄 **마케팅**: 효과적인 메시지 포인트 도출

## 📊 프로젝트 진행률

- ✅ Phase 1: 데이터 수집 (100%)
- ✅ Phase 2: RAG 시스템 (100%)
- 🔄 Phase 3: 고급 분석 (0%)
- 🔄 Phase 4: 시각화 (0%)

**전체 진행률**: 50%

## 🔗 참고 자료

- [Azure OpenAI 공식 문서](https://learn.microsoft.com/azure/ai-services/openai/)
- [ChromaDB 문서](https://docs.trychroma.com/)
- [LangChain 문서](https://python.langchain.com/)

---

**프로젝트**: 아모레퍼시픽 K-Beauty 인사이트 분석  
**작성일**: 2025.12  
**GitHub**: https://github.com/Gosorasora/kbeauty-insights-scraper  
**최종 업데이트**: 2025-12-24
