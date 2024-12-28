# 🚀 Amor-Party AI Agent 배포 가이드

## 📋 사전 준비사항

### 1. 필수 도구 설치
```bash
# Azure CLI 설치 및 로그인
az login

# Terraform 설치 확인
terraform --version

# Python 3.11+ 설치 확인
python --version
```

### 2. 프로젝트 클론
```bash
git clone <repository-url>
cd amor-party-ai-agent
```

## 🔧 배포 단계

### 1단계: Terraform 변수 설정

```bash
# 변수 파일 생성
cd terraform
cp variables.tfvars.example variables.tfvars

# variables.tfvars 파일 편집
nano variables.tfvars
```

**variables.tfvars 필수 수정 항목:**
```hcl
# 🔴 필수: 관리자 이메일 주소 입력
admin_email = "your-email@example.com"

# 선택사항 (기본값 사용 가능)
project_name = "amor-party"
environment = "dev"
location = "koreacentral"
```

### 2단계: Azure 인프라 배포

```bash
# Terraform 초기화
terraform init

# 배포 계획 확인
terraform plan -var-file="variables.tfvars"

# 인프라 배포 (5-10분 소요)
terraform apply -var-file="variables.tfvars"
# 'yes' 입력하여 배포 승인
```

### 3단계: Azure OpenAI 모델 배포 (수동)

1. **Azure Portal 접속**: https://portal.azure.com
2. **OpenAI 리소스 찾기**: `openai-amor-party-dev`
3. **Model deployments** 메뉴 클릭
4. **모델 배포**:

**Embeddings 모델:**
- 모델: `text-embedding-ada-002`
- 배포 이름: `text-embedding-ada-002`
- Capacity: 10 TPM

**Chat 모델:**
- 모델: `gpt-35-turbo`
- 배포 이름: `gpt-35-turbo`
- Capacity: 10 TPM

### 4단계: 환경 변수 설정

```bash
# 프로젝트 루트로 이동
cd ..

# 환경 변수 파일 생성
cp .env.example .env

# Terraform 출력값으로 .env 파일 자동 업데이트 (선택사항)
# 또는 수동으로 Azure Portal에서 값 복사
```

### 5단계: Azure AI Search 인덱스 생성

```bash
# Python 패키지 설치
pip install -r requirements.txt

# 데이터 마이그레이션 실행
python migrate_to_azure_search.py
```

### 6단계: 데이터 업로드

```bash
# CSV 데이터를 Storage Account에 업로드
az storage blob upload-batch \
  --account-name stamorpartydev \
  --destination raw-data \
  --source ./results \
  --pattern "*.csv"
```

### 7단계: 웹 애플리케이션 배포

```bash
# 배포 패키지 생성
zip -r deploy.zip . \
  -x "*.git*" \
  -x "terraform/*" \
  -x "results/*" \
  -x "chrome_profile/*" \
  -x "*.pyc" \
  -x "__pycache__/*"

# App Service에 배포
az webapp deployment source config-zip \
  --resource-group rg-amor-party-dev \
  --name app-amor-party-dev \
  --src deploy.zip

# 배포 로그 확인
az webapp log tail \
  --resource-group rg-amor-party-dev \
  --name app-amor-party-dev
```

## 🌐 접속 확인

### 웹 애플리케이션
```
https://app-amor-party-dev.azurewebsites.net
```

### Health Check
```
https://app-amor-party-dev.azurewebsites.net/health
```

## 🔍 문제 해결

### 일반적인 문제들

**1. OpenAI 모델 미배포**
```
오류: "The API deployment for this resource does not exist"
해결: Azure Portal에서 OpenAI 모델 수동 배포 필요
```

**2. 검색 인덱스 없음**
```
오류: "Index 'amor-party-reviews' not found"
해결: python migrate_to_azure_search.py 실행
```

**3. Redis 연결 실패**
```
오류: "Redis connection failed"
해결: 환경 변수 REDIS_CONNECTION_STRING 확인
```

**4. CSV 파일 없음**
```
오류: "CSV 파일을 찾을 수 없습니다"
해결: ./results/ 폴더에 CSV 파일 배치
```

### 로그 확인 명령어

```bash
# App Service 로그
az webapp log tail --resource-group rg-amor-party-dev --name app-amor-party-dev

# Redis 상태
az redis show --resource-group rg-amor-party-dev --name redis-amor-party-dev

# Search Service 상태
az search service show --resource-group rg-amor-party-dev --name search-amor-party-dev
```

## 💰 비용 모니터링

### 예상 월간 비용: $105-125

- Azure AI Search: $75
- Azure OpenAI: $10-25 (캐시 효과)
- App Service B1: $13
- Redis Cache C0: $16
- 기타: $1-6

### 비용 확인
```bash
# 리소스 그룹별 비용 확인
az consumption usage list --resource-group rg-amor-party-dev
```

## 🗑️ 리소스 정리

### 전체 삭제
```bash
cd terraform
terraform destroy -var-file="variables.tfvars"
# 'yes' 입력하여 삭제 승인
```

### 개별 리소스 중지 (비용 절감)
```bash
# App Service 중지
az webapp stop --name app-amor-party-dev --resource-group rg-amor-party-dev

# Redis Cache는 중지 불가 (삭제만 가능)
```

## 📞 지원

문제 발생 시:
1. 이 가이드의 문제 해결 섹션 확인
2. Azure Portal에서 리소스 상태 확인
3. 로그 확인 명령어로 상세 오류 파악

---

**배포 완료 후 예상 결과:**
- ⚡ 응답 시간: 5-10ms (캐시) / 20-50ms (검색)
- 🚀 동시 사용자: 200명+
- 💾 데이터 처리: 100만+ documents
- 📈 Auto-scaling: 1-3 인스턴스