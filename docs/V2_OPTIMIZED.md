# Version 2: 최적화 아키텍처 (Cognitive Search)

## 📋 개요

**월간 비용**: $140-170 (+Redis +Monitoring)  
**권장 대상**: 공모전, 스타트업, MVP, 5만개 이상 데이터  
**배포 시간**: 30분  
**SLA**: 99.9% (App Service B1)

**아키텍처 다이어그램**:
- 📊 [v2 아키텍처](./v2-architecture.drawio) - Redis 캐시 포함 Azure 아키텍처

---

## 🏗️ 아키텍처 상세

### 핵심 구성 요소

| 구성 요소 | SKU | 위치 | 역할 |
|----------|-----|------|------|
| **App Service** | B1 | Korea Central | RAG Agent 실행 |
| **Azure AI Search** | Basic | Korea Central | Vector 검색 엔진 |
| **Azure OpenAI** | S0 | East US | 임베딩 + GPT 모델 |
| **Redis Cache** | C0 (Basic) | Korea Central | 응답 캐싱 |
| **Application Insights** | Standard | Korea Central | 성능 모니터링 |
| **Blob Storage** | Standard LRS | Korea Central | 데이터 저장 |
| **Key Vault** | Standard | Korea Central | 비밀 관리 |

### 데이터 흐름

1. **사용자 요청** → App Service (HTTPS)
2. **캐시 확인** → Redis Cache (5-10ms)
3. **캐시 미스 시**:
   - **질문 임베딩** → Azure OpenAI (API Call)
   - **Vector 검색** → Azure AI Search (20-50ms)
   - **답변 생성** → Azure OpenAI (GPT-3.5 Turbo)
   - **응답 캐싱** → Redis Cache (1시간 TTL)
4. **응답 반환** → 사용자
5. **성능 메트릭** → Application Insights

### 리전 전략

**Korea Central (주요 리소스)**
- 한국 사용자 대상 서비스
- 낮은 지연시간 (< 50ms)
- 데이터 주권 준수

### 리전 전략

**Korea Central (주요 리소스)**
- 한국 사용자 대상 서비스
- 낮은 지연시간 (< 50ms)
- 데이터 주권 준수

**East US (Azure OpenAI)**
- OpenAI 지원 리전 제한
- 리전 간 통신 비용: ~$0.10/월
- API 호출 지연시간: 100-200ms (허용 가능)

## 🌍 Azure 인프라 구조

### Region 배치 전략

본 프로젝트는 **멀티 리전** 아키텍처를 사용합니다:

| 리소스 | Region | 이유 |
|--------|--------|------|
| App Service | Korea Central | 한국 사용자 대상 (낮은 지연시간) |
| Azure AI Search | Korea Central | App Service와 동일 리전 (빠른 통신) |
| Blob Storage | Korea Central | 데이터 저장 위치 |
| Key Vault | Korea Central | 보안 정책 준수 |
| **Azure OpenAI** | **East US** | **OpenAI 지원 리전 제한** |

### Azure OpenAI 리전 제한

Azure OpenAI는 특정 리전에서만 사용 가능합니다:

**지원 리전**: East US, West Europe, South Central US 등  
**미지원**: Korea Central, Korea South, Japan East

**해결책**: OpenAI만 East US에 배포하고 나머지는 Korea Central 사용

---

## 🌐 CDN 필요성 분석

### K-Beauty RAG 시스템에서 CDN이 필요한가?

**결론: 현재 단계에서는 불필요**

### CDN이 도움이 되는 경우
- ✅ 정적 콘텐츠 (이미지, CSS, JS)
- ✅ 파일 다운로드
- ✅ 글로벌 사용자 대상
- ✅ 대용량 미디어 콘텐츠

### 본 프로젝트 특성
- ❌ **API 기반 서비스**: CDN으로 캐시 불가
- ❌ **동적 응답**: 매번 다른 답변 생성
- ❌ **개인화된 결과**: 사용자별 맞춤 응답
- ❌ **실시간 처리**: Vector 검색 + GPT 생성

### 대안: 애플리케이션 레벨 최적화

**1. 응답 캐싱**
```python
# 동일한 질문에 대한 캐싱
@lru_cache(maxsize=1000)
def get_cached_response(question_hash):
    return cached_answer
```

**2. Vector 검색 최적화**
- Azure AI Search의 GPU 가속 활용
- HNSW 알고리즘 파라미터 튜닝
- 검색 결과 캐싱

**3. 지연시간 최적화**
- Korea Central 리전 사용 (한국 사용자 대상)
- App Service와 AI Search 동일 리전 배치
- 불필요한 API 호출 제거

### v3 (프로덕션)에서 CDN 고려사항

**CDN이 유용한 경우:**
- 웹 UI 정적 파일 (React/Vue 앱)
- 제품 이미지 캐싱
- API 문서 페이지
- 다운로드 파일

**권장 CDN 설정 (v3):**
```hcl
resource "azurerm_cdn_profile" "main" {
  name                = "cdn-${local.resource_prefix}"
  location            = "Global"
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard_Microsoft"
}

# 정적 콘텐츠만 CDN 사용
resource "azurerm_cdn_endpoint" "static" {
  name                = "static-${local.resource_prefix}"
  profile_name        = azurerm_cdn_profile.main.name
  location            = azurerm_cdn_profile.main.location
  resource_group_name = azurerm_resource_group.main.name
  
  origin {
    name      = "static-origin"
    host_name = azurerm_storage_account.main.primary_blob_endpoint
  }
  
  # API 경로는 제외
  delivery_rule {
    name  = "api-bypass"
    order = 1
    
    url_path_condition {
      operator     = "BeginsWith"
      match_values = ["/api/"]
    }
    
    cache_expiration_action {
      behavior = "BypassCache"
    }
  }
}
```

**비용 영향:**
- CDN 추가 시: +$10-20/월
- 성능 개선: 정적 파일만 (API 응답 시간 변화 없음)

---

## 🏗️ 아키텍처

**시각적 다이어그램**: [v2-architecture.drawio](./v2-architecture.drawio)

### 아키텍처 개요

```
User (Client) ──HTTPS──▶ App Service (B1)
                            │
                            ├──Vector Query (20-50ms)──▶ Azure AI Search
                            │
                            ├──API Call (Embedding/Chat)──▶ Azure OpenAI (East US)
                            │
                            ├──Get Secrets (Managed Identity)──▶ Key Vault
                            │
                            └──Read/Write Data──▶ Blob Storage
```

### 리전 배치

**Korea Central (주요 리소스)**
- App Service (B1): Python 3.11 RAG Agent
- Azure AI Search (Basic): Vector 검색 엔진
- Blob Storage (Standard LRS): 데이터 저장
- Key Vault (Standard): 비밀 관리

**East US (OpenAI 전용)**
- Azure OpenAI (S0): GPT-3.5 Turbo + Embeddings

---

## 💰 비용 구성

| 서비스 | SKU | 월간 비용 | 비고 |
|--------|-----|----------|------|
| Azure AI Search | Basic | $75 | Vector Search |
| Azure OpenAI | S0 (종량제) | $20-40 | 캐시로 30% 절감 |
| App Service | B1 (Basic) | $13 | 1 vCPU, 1.75GB |
| Redis Cache | C0 (Basic) | $16 | 250MB, 응답 캐싱 |
| Application Insights | Standard | $5-10 | 성능 모니터링 |
| Storage Account | Standard LRS | $1-5 | 로컬 중복 |
| Log Analytics | PerGB2018 | $2-5 | 중앙화된 로깅 |
| Key Vault | Standard | $0.03 | 비밀 관리 |
| **총 비용** | | **$140-170** | |

### 상세 비용 분석

**Azure AI Search ($75)**
- Basic SKU: 고정 비용
- 최대 100만 documents
- Vector Search 지원
- GPU 가속 검색

**Azure OpenAI (월 $20-40, 30% 절감)**
- Embeddings: $0.11 (초기) + $0.01 (증분)
- GPT-3.5 Turbo: $8-30 (캐시 효과로 절감)
  - 100 질문/일: $8 (캐시 히트율 40%)
  - 500 질문/일: $35 (캐시 히트율 50%)

**Redis Cache C0 ($16)**
- 250MB 메모리
- 자주 묻는 질문 캐싱
- OpenAI API 호출 30% 절감
- 응답 시간 80% 단축

**Application Insights ($5-10)**
- 성능 모니터링
- 실시간 메트릭
- 자동 알림
- 30일 데이터 보존

**App Service B1 ($13)**
- CPU 부담 감소 (캐시 활용)
- 메모리 사용: ~200MB
- 안정적인 성능

---

## ⚡ 성능 비교

### ChromaDB 내장 vs Cognitive Search + Redis

| 항목 | ChromaDB 내장 | Cognitive Search + Redis | 개선 |
|------|--------------|--------------------------|------|
| 검색 시간 | 300-500ms | 5-10ms (캐시) / 20-50ms | **50배** |
| 동시 사용자 | 5명 | 100명+ | **20배** |
| 최대 데이터 | 5만개 | 100만개 | **20배** |
| CPU 사용률 | 50-80% | 5-15% | **5배** |
| 메모리 사용 | 1GB | 200MB | **5배** |
| OpenAI 비용 | 100% | 70% (30% 절감) | **30% 절감** |
| 비용 | $45-70 | $140-170 | +$70-100 |

**결론**: 캐시 효과로 사용자 경험 대폭 개선 + OpenAI 비용 절감!

---

## 🚀 배포 방법

### 방법 1: Terraform 자동 배포 (권장)

#### 1. 사전 준비

```bash
# Azure CLI 설치 및 로그인
az login

# Terraform 설치 확인
terraform --version

# 프로젝트 클론
git clone https://github.com/Gosorasora/kbeauty-insights-scraper.git
cd kbeauty-insights-scraper
```

#### 2. Terraform 설정

```bash
cd terraform

# 변수 파일 생성
cp variables.tfvars.example variables.tfvars

# 변수 편집
nano variables.tfvars
```

`variables.tfvars` 내용:
```hcl
project_name = "kbeauty"
environment  = "dev"
location     = "koreacentral"
admin_email  = "your-email@example.com"
```

#### 3. 배포 실행

```bash
# 초기화
terraform init

# 계획 확인
terraform plan -var-file="variables.tfvars"

# 배포
terraform apply -var-file="variables.tfvars"
# 'yes' 입력
```

**배포 시간**: 약 5-10분

#### 4. Azure OpenAI 모델 배포 (수동)

```bash
# 1. Azure Portal 접속
https://portal.azure.com

# 2. OpenAI 리소스 찾기
리소스 그룹: rg-kbeauty-dev
리소스: openai-kbeauty-dev

# 3. Model deployments 메뉴

# 4. 모델 배포
```

**Embeddings:**
- 모델: `text-embedding-ada-002`
- 배포 이름: `text-embedding-ada-002`
- Capacity: 10 TPM

**Chat:**
- 모델: `gpt-35-turbo`
- 배포 이름: `gpt-35-turbo`
- Capacity: 10 TPM

#### 5. Cognitive Search 인덱스 생성

```bash
# 마이그레이션 스크립트 실행
cd ..
python migrate_to_cognitive_search.py
```

이 스크립트는:
1. Cognitive Search 인덱스 생성
2. ChromaDB 데이터 읽기
3. Cognitive Search에 업로드

#### 6. 데이터 업로드

```bash
# Storage Account에 데이터 업로드
az storage blob upload-batch \
  --account-name stkbeautydev \
  --destination raw-data \
  --source ./results \
  --pattern "*.csv"
```

#### 7. 애플리케이션 배포

```bash
# 배포 패키지 생성
zip -r deploy.zip . \
  -x "*.git*" \
  -x "terraform/*" \
  -x "results/*" \
  -x "chroma_db/*" \
  -x "chrome_profile/*" \
  -x "*.pyc" \
  -x "__pycache__/*" \
  -x "docs/*"

# App Service에 배포
az webapp deployment source config-zip \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev \
  --src deploy.zip

# 배포 로그 확인
az webapp log tail \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev
```

#### 8. 접속 확인

```bash
# App Service URL 확인
terraform output app_service_url

# 브라우저에서 접속
https://app-kbeauty-dev.azurewebsites.net
```

---

## 🔧 운영 및 관리

### 애플리케이션 업데이트

```bash
# 코드 수정 후
git add .
git commit -m "Update feature"
git push

# 재배포
zip -r deploy.zip . -x "*.git*" -x "terraform/*" -x "results/*"
az webapp deployment source config-zip \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev \
  --src deploy.zip
```

### 로그 확인

```bash
# 실시간 로그 스트리밍
az webapp log tail \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev

# 로그 다운로드
az webapp log download \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev \
  --log-file app-logs.zip
```

### Cognitive Search 모니터링

```bash
# 검색 통계 확인
az search service show \
  --resource-group rg-kbeauty-dev \
  --name search-kbeauty-dev

# 인덱스 통계
az search index show \
  --service-name search-kbeauty-dev \
  --name kbeauty-reviews
```

---

## 💡 비용 최적화 전략

### 1. Azure for Students 활용

```bash
# 신청: https://azure.microsoft.com/free/students/
# $100 크레딧 (12개월)

예상 사용:
- 3개월: $360-435
- 크레딧 사용: $100
- 실제 지불: $260-335
```

### 2. 공모전 후 리소스 중지

```bash
# App Service 중지
az webapp stop --name app-kbeauty-dev --resource-group rg-kbeauty-dev

# Search Service는 중지 불가 (삭제만 가능)
# 공모전 끝나면 삭제
az search service delete \
  --resource-group rg-kbeauty-dev \
  --name search-kbeauty-dev
```

### 3. GPT-3.5 Turbo 사용

```bash
# .env 또는 App Settings
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo  # gpt-4 대신
```

**절감액**: $258/월 (100 질문/일 기준)

---

## 🎯 사용 시나리오

### 시나리오 1: 공모전 데모 (5만개 데이터)

**목표**: 빠른 응답으로 심사위원 인상

```bash
# 1. 배포
terraform apply

# 2. 데모 준비
- 응답 시간: 0.6초 (빠름!)
- 동시 접속: 10명 가능
- 안정적인 성능

# 3. 발표 포인트
"Azure AI Search로 Vector 검색을 분리하여
10배 빠른 성능을 달성했습니다"
```

### 시나리오 2: MVP 서비스 (10만개 데이터)

**목표**: 초기 사용자 확보

```bash
# 1. 데이터 확장
- 5만 → 10만개로 증가
- 성능 유지 (검색 30-60ms)

# 2. 모니터링
az monitor metrics list \
  --resource search-kbeauty-dev \
  --metric "SearchQueriesPerSecond"

# 3. 필요시 스케일업
az search service update \
  --resource-group rg-kbeauty-dev \
  --name search-kbeauty-dev \
  --partition-count 2
```

---

## 📊 성능 최적화

### 1. Cognitive Search 설정 최적화

```python
# migrate_to_cognitive_search.py

# HNSW 알고리즘 파라미터 최적화
HnswAlgorithmConfiguration(
    name="myHnsw",
    parameters={
        "m": 4,              # 연결 수 (기본: 4)
        "efConstruction": 400,  # 인덱스 구축 품질
        "efSearch": 500,     # 검색 품질
        "metric": "cosine"   # 유사도 메트릭
    }
)
```

### 2. 배치 업로드 최적화

```python
# 1000개씩 배치 업로드
batch_size = 1000
for i in range(0, len(documents), batch_size):
    batch = documents[i:i+batch_size]
    search_client.upload_documents(batch)
```

### 3. 쿼리 최적화

```python
# Top-K 조정
results = search_client.search(
    search_text=None,
    vector_queries=[{
        "vector": embedding,
        "k_nearest_neighbors": 10,  # 5 → 10으로 증가
        "fields": "embedding"
    }]
)
```

---

## 🐛 트러블슈팅

### 문제 1: Cognitive Search 인덱스 생성 실패

```
Error: Index creation failed
```

**해결:**
```bash
# Search Service 상태 확인
az search service show \
  --resource-group rg-kbeauty-dev \
  --name search-kbeauty-dev

# 기존 인덱스 삭제 후 재생성
az search index delete \
  --service-name search-kbeauty-dev \
  --name kbeauty-reviews
```

### 문제 2: Vector 검색 느림

```
Search time > 100ms
```

**해결:**
```python
# HNSW 파라미터 조정
"efSearch": 500  # 300 → 500으로 증가
```

### 문제 3: 비용 초과

```
Monthly cost > $200
```

**해결:**
```bash
# 1. GPT-3.5 Turbo 사용 확인
# 2. 불필요한 쿼리 제거
# 3. 캐싱 활성화
```

---

## 📈 모니터링 및 알림

### Cognitive Search 메트릭

```bash
# 검색 쿼리 수
az monitor metrics list \
  --resource /subscriptions/<sub-id>/resourceGroups/rg-kbeauty-dev/providers/Microsoft.Search/searchServices/search-kbeauty-dev \
  --metric "SearchQueriesPerSecond"

# 검색 지연 시간
az monitor metrics list \
  --resource /subscriptions/<sub-id>/resourceGroups/rg-kbeauty-dev/providers/Microsoft.Search/searchServices/search-kbeauty-dev \
  --metric "SearchLatency"
```

---

## 🎯 v2 → v3 업그레이드 가이드

### 언제 v3로 업그레이드하나요?

- ✅ 일일 사용자 > 100명
- ✅ 월간 질문 > 10,000개
- ✅ 데이터 > 100만개
- ✅ 가용성 요구사항 > 99.9%
- ✅ 예산 > $500/월

---

## 📚 참고 자료

- [Azure AI Search 가격](https://azure.microsoft.com/pricing/details/search/)
- [Azure OpenAI 가격](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/)
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)

---

**작성일**: 2025-12-29  
**버전**: v2 (Cognitive Search)  
**이전 문서**: `V1_LOCAL_DEV.md`  
**다음 문서**: `V3_PRODUCTION.md`
