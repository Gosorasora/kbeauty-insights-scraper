# Terraform으로 Azure 인프라 배포 (v2: Cognitive Search)

## 📋 개요

이 Terraform 구성은 K-Beauty RAG 시스템을 Azure에 배포하기 위한 **v2 아키텍처**를 생성합니다.

### 💰 예상 비용

| 서비스 | SKU | 월간 비용 |
|--------|-----|----------|
| Azure AI Search | Basic | $75 |
| Azure OpenAI | S0 (종량제) | $30-50 |
| App Service | B1 (Basic) | $13 |
| Storage Account | Standard LRS | $1-5 |
| Key Vault | Standard | $0.03 |
| **총 예상 비용** | | **$120-145** |

### 🎯 포함된 리소스

**Korea Central Region:**
1. **Resource Group**: 모든 리소스 컨테이너
2. **App Service (B1)**: Python 3.11 RAG Agent
3. **Azure AI Search (Basic)**: Vector Database ($75/월)
4. **Blob Storage (Standard LRS)**: 데이터 저장
5. **Key Vault (Standard)**: API 키 관리

**East US Region:**
6. **Azure OpenAI (S0)**: 임베딩 + GPT 모델

**특징:**
- 멀티 리전 아키텍처 (OpenAI 리전 제한)
- GPU 가속 Vector 검색
- 최대 100만 documents 지원

---

## 🚀 배포 방법

### 1. 사전 요구사항

```bash
# Azure CLI 설치 확인
az --version

# Terraform 설치 확인
terraform --version

# Azure 로그인
az login

# 구독 확인
az account show
```

### 2. Terraform 초기화

```bash
cd terraform

# 변수 파일 생성
cp variables.tfvars.example variables.tfvars

# variables.tfvars 편집
# admin_email을 실제 이메일로 변경
nano variables.tfvars
```

### 3. Terraform 실행

```bash
# 초기화
terraform init

# 계획 확인 (무엇이 생성될지 미리보기)
terraform plan -var-file="variables.tfvars"

# 배포 실행
terraform apply -var-file="variables.tfvars"

# 확인 메시지에서 'yes' 입력
```

### 4. Azure OpenAI 모델 배포 (수동)

Terraform으로는 OpenAI 모델을 자동 배포할 수 없어서 Portal에서 수동으로 배포해야 합니다.

```bash
# 1. Azure Portal 접속
https://portal.azure.com

# 2. OpenAI 리소스 찾기
리소스 그룹: rg-kbeauty-dev
리소스 이름: openai-kbeauty-dev

# 3. "Model deployments" 메뉴 클릭

# 4. 다음 모델 배포:
```

#### 모델 1: Embeddings
- **모델**: `text-embedding-ada-002`
- **배포 이름**: `text-embedding-ada-002`
- **버전**: 최신
- **Capacity**: 10 (TPM: 10,000)

#### 모델 2: Chat (선택)

**옵션 A: 비용 절감 (권장)**
- **모델**: `gpt-35-turbo`
- **배포 이름**: `gpt-35-turbo`
- **버전**: 최신
- **Capacity**: 10 (TPM: 10,000)
- **비용**: ~$0.002/1K tokens

**옵션 B: 고품질**
- **모델**: `gpt-4`
- **배포 이름**: `gpt-4`
- **버전**: 최신
- **Capacity**: 10 (TPM: 10,000)
- **비용**: ~$0.03/1K tokens (15배 비쌈)

### 5. 데이터 업로드

```bash
# Storage Account에 데이터 업로드
az storage blob upload-batch \
  --account-name stkbeautydev \
  --destination raw-data \
  --source ../results \
  --pattern "*.csv"

# 업로드 확인
az storage blob list \
  --account-name stkbeautydev \
  --container-name raw-data \
  --output table
```

### 6. 애플리케이션 배포

```bash
# 프로젝트 루트로 이동
cd ..

# 배포 패키지 생성
zip -r deploy.zip . \
  -x "*.git*" \
  -x "terraform/*" \
  -x "results/*" \
  -x "chroma_db/*" \
  -x "chrome_profile/*" \
  -x "*.pyc" \
  -x "__pycache__/*"

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

### 7. 환경 변수 설정

```bash
# 현재 환경 변수 확인
az webapp config appsettings list \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev

# 추가 환경 변수 설정 (필요시)
az webapp config appsettings set \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev \
  --settings \
    AZURE_OPENAI_DEPLOYMENT_NAME="gpt-35-turbo" \
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT="text-embedding-ada-002" \
    AZURE_OPENAI_API_VERSION="2024-02-15-preview"
```

### 8. 접속 확인

```bash
# App Service URL 확인
terraform output app_service_url

# 브라우저에서 접속
https://app-kbeauty-dev.azurewebsites.net
```

---

## 🔧 관리 명령어

### 리소스 상태 확인

```bash
# Terraform 상태 확인
terraform show

# 특정 리소스 확인
terraform state list
terraform state show azurerm_linux_web_app.main
```

### 리소스 업데이트

```bash
# 변경사항 확인
terraform plan -var-file="variables.tfvars"

# 변경사항 적용
terraform apply -var-file="variables.tfvars"
```

### 비용 확인

```bash
# Azure Cost Management
az consumption usage list \
  --start-date 2025-12-01 \
  --end-date 2025-12-31 \
  --query "[?contains(instanceName, 'kbeauty')]" \
  --output table
```

### 로그 확인

```bash
# App Service 로그 스트리밍
az webapp log tail \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev

# 최근 로그 다운로드
az webapp log download \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev \
  --log-file app-logs.zip
```

---

## 🗑️ 리소스 삭제

### 전체 삭제

```bash
# Terraform으로 모든 리소스 삭제
terraform destroy -var-file="variables.tfvars"

# 확인 메시지에서 'yes' 입력
```

### 개별 리소스 삭제

```bash
# 특정 리소스만 삭제
terraform destroy -target=azurerm_linux_web_app.main -var-file="variables.tfvars"
```

---

## 💡 비용 최적화 팁

### 1. GPT-3.5 Turbo 사용
```bash
# GPT-4 대신 GPT-3.5 Turbo 사용 (15배 저렴)
# .env 파일에서:
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
```

### 2. App Service 중지 (사용하지 않을 때)
```bash
# App Service 중지
az webapp stop \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev

# App Service 시작
az webapp start \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev
```

### 3. 캐싱 활용
```python
# 자주 묻는 질문 캐싱
import json

cache_file = "answer_cache.json"

def get_cached_answer(question):
    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        return cache.get(question)
    except:
        return None

def save_to_cache(question, answer):
    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
    except:
        cache = {}
    
    cache[question] = answer
    
    with open(cache_file, 'w') as f:
        json.dump(cache, f)
```

### 4. 배치 처리
```python
# 여러 질문을 한 번에 처리
questions = [
    "인기 토너는?",
    "Snail Mucin 반응은?",
    "건조한 피부 제품은?"
]

for q in questions:
    answer = agent.ask(q)
```

---

## 🐛 트러블슈팅

### 문제 1: Terraform 초기화 실패
```bash
# 캐시 삭제 후 재시도
rm -rf .terraform
terraform init
```

### 문제 2: Azure 로그인 오류
```bash
# 로그아웃 후 재로그인
az logout
az login

# 올바른 구독 선택
az account list --output table
az account set --subscription "구독ID"
```

### 문제 3: OpenAI 리소스 생성 실패
```bash
# OpenAI는 특정 리전만 지원
# main.tf에서 location을 다음 중 하나로 변경:
# - eastus
# - westeurope
# - southcentralus
```

### 문제 4: App Service 배포 실패
```bash
# 배포 로그 확인
az webapp log deployment show \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev

# SCM 사이트 접속 (고급 도구)
https://app-kbeauty-dev.scm.azurewebsites.net
```

### 문제 5: Key Vault 접근 오류
```bash
# App Service에 Managed Identity 활성화 확인
az webapp identity show \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev

# Key Vault 접근 정책 확인
az keyvault show \
  --name kv-kbeauty-dev \
  --query "properties.accessPolicies"
```

---

## 📊 모니터링

### Application Insights (선택)

```bash
# Application Insights 추가 (월 $5-10)
az monitor app-insights component create \
  --app app-kbeauty-dev \
  --location koreacentral \
  --resource-group rg-kbeauty-dev \
  --application-type web

# App Service에 연결
az webapp config appsettings set \
  --resource-group rg-kbeauty-dev \
  --name app-kbeauty-dev \
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING="<connection-string>"
```

---

## 🔗 참고 자료

- [Azure OpenAI 가격](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/)
- [App Service 가격](https://azure.microsoft.com/pricing/details/app-service/linux/)
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Azure CLI 문서](https://learn.microsoft.com/cli/azure/)

---

**작성일**: 2025-12-24  
**Terraform 버전**: >= 1.0  
**Azure Provider 버전**: ~> 3.0
