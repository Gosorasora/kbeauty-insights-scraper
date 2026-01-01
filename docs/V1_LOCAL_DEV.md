# Version 1: 로컬 개발 환경

## 📋 개요

**월간 비용**: $10-30  
**권장 대상**: 개발 초기, 학습, 프로토타입  
**배포 시간**: 10분

---

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    로컬 개발 환경                         │
└─────────────────────────────────────────────────────────┘

💻 Local Machine
├── Python 3.11
├── azure_rag_agent.py
├── ChromaDB (./chroma_db/)
├── CSV 파일 (./results/)
└── .env (환경 변수)
    │
    ↓ HTTPS
    │
☁️  Azure OpenAI (Cloud)
├── text-embedding-ada-002
└── gpt-35-turbo
```

---

## 💰 비용 구성

| 항목 | 위치 | 월간 비용 | 비고 |
|------|------|----------|------|
| Azure OpenAI API | Cloud | $10-30 | 종량제 |
| ChromaDB | Local | $0 | 무료 |
| Python App | Local | $0 | 무료 |
| CSV 파일 | Local | $0 | 무료 |
| **총 비용** | | **$10-30** | |

### Azure OpenAI 사용량 예측

**Embeddings (text-embedding-ada-002)**
- 초기 구축: 5,621개 리뷰 → $0.11 (1회)
- 월간 증분: 500개 리뷰 → $0.01

**Chat (gpt-35-turbo)**
- 개발/테스트: 100 질문 → $0.40
- 일일 테스트: 10 질문/일 x 30일 → $12

**월간 총 비용: $12-30**

---

## 🚀 설치 및 설정

### 1. 사전 요구사항

```bash
# Python 3.11 설치 확인
python3 --version

# pip 업그레이드
pip install --upgrade pip
```

### 2. 프로젝트 클론

```bash
git clone https://github.com/Gosorasora/kbeauty-insights-scraper.git
cd kbeauty-insights-scraper
```

### 3. 라이브러리 설치

```bash
# Azure RAG 시스템용
pip install -r requirements_azure.txt
```

### 4. Azure OpenAI 설정

#### 4.1 Azure Portal에서 리소스 생성

1. https://portal.azure.com 접속
2. "Azure OpenAI" 검색
3. "만들기" 클릭
4. 정보 입력:
   - 리소스 그룹: `rg-kbeauty-dev`
   - 이름: `openai-kbeauty-dev`
   - 지역: `East US` (OpenAI 지원 지역)
   - 가격 책정: `Standard S0`

#### 4.2 모델 배포

1. OpenAI 리소스 → "Model deployments"
2. 다음 모델 배포:

**Embeddings:**
- 모델: `text-embedding-ada-002`
- 배포 이름: `text-embedding-ada-002`
- Capacity: 10 TPM

**Chat:**
- 모델: `gpt-35-turbo`
- 배포 이름: `gpt-35-turbo`
- Capacity: 10 TPM

#### 4.3 API 키 확인

1. OpenAI 리소스 → "Keys and Endpoint"
2. KEY 1 복사
3. Endpoint 복사

### 5. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env
```

`.env` 내용:
```env
AZURE_OPENAI_ENDPOINT=https://openai-kbeauty-dev.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

---

## 📊 데이터 준비

### 1. 데이터 전처리

```bash
python preprocess_data.py
```

**출력:**
- `results/amazon_reviews_clean.csv`
- `results/amazon_reviews_clean.json`

### 2. Vector Database 구축

```bash
python build_vector_db.py
```

**소요 시간**: 10-15분 (5,621개 리뷰)  
**출력**: `./chroma_db/` 폴더

---

## 💬 RAG 에이전트 실행

### 1. 대화형 모드

```bash
python azure_rag_agent.py
```

**사용 예시:**
```
질문을 입력하세요: 요즘 인기 있는 진정 토너는?

[1/3] 관련 리뷰 검색 중... (Top 10)
✓ 10개 리뷰 검색 완료

[2/3] 컨텍스트 생성 중...
✓ 컨텍스트 생성 완료 (3,245자)

[3/3] AI 답변 생성 중...
✓ 답변 생성 완료

답변:
미국에서 인기 있는 K-Beauty 진정 토너는...
```

### 2. Python 스크립트에서 사용

```python
from azure_rag_agent import KBeautyRAGAgent

# 에이전트 초기화
agent = KBeautyRAGAgent()

# 질문하기
answer = agent.ask("요즘 인기 있는 진정 토너는?")
print(answer)

# 여러 질문
questions = [
    "Snail Mucin 제품 반응은?",
    "건조한 피부에 좋은 제품은?",
    "Niacinamide 고평점 제품은?"
]

for q in questions:
    answer = agent.ask(q)
```

---

## 🔧 개발 워크플로우

### 일반적인 개발 사이클

```bash
# 1. 코드 수정
nano azure_rag_agent.py

# 2. 테스트
python azure_rag_agent.py

# 3. 디버깅 (필요시)
python -m pdb azure_rag_agent.py

# 4. 커밋
git add .
git commit -m "Update RAG agent"
git push
```

### 데이터 업데이트

```bash
# 1. 새 데이터 수집
python amazon_scraper.py

# 2. 전처리
python preprocess_data.py

# 3. Vector DB 재구축
rm -rf ./chroma_db
python build_vector_db.py
```

---

## 💡 비용 절감 팁

### 1. GPT-3.5 Turbo 사용 (필수)

```env
# .env 파일
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo  # gpt-4 대신
```

**절감액**: GPT-4 대비 22배 저렴

### 2. 캐싱 구현

```python
import json
from pathlib import Path

class CachedAgent:
    def __init__(self):
        self.agent = KBeautyRAGAgent()
        self.cache_file = Path("answer_cache.json")
        self.cache = self.load_cache()
    
    def load_cache(self):
        if self.cache_file.exists():
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def ask(self, question):
        if question in self.cache:
            print("[캐시에서 가져옴]")
            return self.cache[question]
        
        answer = self.agent.ask(question)
        self.cache[question] = answer
        self.save_cache()
        return answer

# 사용
cached_agent = CachedAgent()
answer = cached_agent.ask("인기 토너는?")  # API 호출
answer = cached_agent.ask("인기 토너는?")  # 캐시 사용 (무료)
```

**절감액**: 중복 질문 30-50% 절감

### 3. 배치 처리

```python
# 여러 질문을 한 번에 처리
questions = [
    "인기 토너는?",
    "Snail Mucin 반응은?",
    "건조한 피부 제품은?"
]

# 한 번에 처리
for q in questions:
    answer = agent.ask(q)
    print(f"\n질문: {q}")
    print(f"답변: {answer[:100]}...")
```

### 4. 개발 중 API 호출 최소화

```python
# 테스트용 Mock 데이터
MOCK_MODE = True  # 개발 중에는 True

if MOCK_MODE:
    def mock_ask(question):
        return "테스트 답변입니다."
    agent.ask = mock_ask
```

---

## 🐛 트러블슈팅

### 문제 1: Azure OpenAI 연결 실패

```
Error: Incorrect API key provided
```

**해결:**
```bash
# .env 파일 확인
cat .env

# API 키 재확인 (Azure Portal)
# Keys and Endpoint → KEY 1 복사
```

### 문제 2: ChromaDB 오류

```
Error: Collection not found
```

**해결:**
```bash
# Vector DB 재구축
rm -rf ./chroma_db
python build_vector_db.py
```

### 문제 3: 메모리 부족

```
MemoryError: Unable to allocate array
```

**해결:**
```python
# build_vector_db.py에서 배치 크기 줄이기
batch_size = 5  # 10 → 5로 변경
```

### 문제 4: 느린 응답 속도

**원인**: 네트워크 지연 또는 API Rate Limit

**해결:**
```python
# 타임아웃 설정
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    timeout=30.0  # 30초 타임아웃
)
```

---

## 📊 성능 모니터링

### 로컬 로깅

```python
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_agent.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 사용
logger.info(f"질문: {question}")
logger.info(f"검색 결과: {len(results)}개")
logger.info(f"답변 길이: {len(answer)}자")
```

### 비용 추적

```python
import json
from datetime import datetime

class CostTracker:
    def __init__(self):
        self.log_file = "cost_log.json"
        self.costs = self.load_log()
    
    def load_log(self):
        try:
            with open(self.log_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def log_api_call(self, api_type, tokens, cost):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "api_type": api_type,
            "tokens": tokens,
            "cost": cost
        }
        self.costs.append(entry)
        
        with open(self.log_file, 'w') as f:
            json.dump(self.costs, f, indent=2)
    
    def get_total_cost(self):
        return sum(c['cost'] for c in self.costs)

# 사용
tracker = CostTracker()
tracker.log_api_call("embedding", 1000, 0.0001)
tracker.log_api_call("chat", 2500, 0.005)
print(f"총 비용: ${tracker.get_total_cost():.4f}")
```

---

## 🎯 다음 단계

### v1 → v2 마이그레이션 준비

공모전 제출 2주 전에 v2 (최적화)로 전환:

1. **코드 정리**
   - 불필요한 파일 삭제
   - 주석 정리
   - README 업데이트

2. **테스트**
   - 모든 기능 동작 확인
   - 예시 질문 10개 테스트
   - 응답 시간 측정

3. **문서화**
   - API 사용법 문서
   - 데모 시나리오 작성
   - 발표 자료 준비

4. **v2 배포**
   ```bash
   cd terraform/v2-optimized
   terraform init
   terraform apply
   ```

---

## 📚 참고 자료

- [Azure OpenAI 문서](https://learn.microsoft.com/azure/ai-services/openai/)
- [ChromaDB 문서](https://docs.trychroma.com/)
- [Python dotenv](https://pypi.org/project/python-dotenv/)

---

**작성일**: 2025-12-24  
**버전**: v1 (로컬 개발)  
**다음 문서**: `V2_OPTIMIZED.md`
