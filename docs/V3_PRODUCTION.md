# Version 3: 프로덕션 아키텍처 (상용 서비스)

## 📋 개요

**월간 비용**: $700-1,000  
**권장 대상**: 상용 서비스, 엔터프라이즈, 대규모 사용자  
**배포 시간**: 2-3시간  
**SLA**: 99.95% (Multi-AZ)  
**지원 사용자**: 1,000+ DAU

---

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Azure Cloud (Korea Central)                               │
│                    Virtual Network: 10.0.0.0/16                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │
│  │  Availability Zone 1 │  │  Availability Zone 2 │  │  Availability Zone 3 │ │
│  ├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤ │
│  │                     │  │                     │  │                     │ │
│  │  App Service P1v3   │  │  App Service P1v3   │  │  Redis Cache C1     │ │
│  │  (Primary)          │  │  (Secondary)        │  │  (Caching)          │ │
│  │  - 2 vCPU, 8GB      │  │  - 2 vCPU, 8GB      │  │  - 1GB              │ │
│  │  - Auto Scale       │  │  - Auto Scale       │  │                     │ │
│  │                     │  │                     │  │  API Management     │ │
│  │  Azure Functions    │  │  Azure OpenAI       │  │  (Developer)        │ │
│  │  (Vectorization)    │  │  - Embeddings       │  │  - Rate Limiting    │ │
│  │  - Premium Plan     │  │  - GPT-4            │  │  - Auth             │ │
│  │                     │  │  - Private Endpoint │  │                     │ │
│  │  Blob Storage       │  │                     │  │  Key Vault          │ │
│  │  (GRS)              │  │  Cognitive Search   │  │  (Secrets)          │ │
│  │  - raw-data         │  │  - Vector Search    │  │                     │ │
│  │  - clean-data       │  │  - 5,621 docs       │  │  Monitor            │ │
│  │                     │  │  - Auto Scale       │  │  (Insights)         │ │
│  │  SQL Database S3    │  │                     │  │                     │ │
│  │  (100 DTU)          │  │                     │  │                     │ │
│  │  - 250GB            │  │                     │  │                     │ │
│  │                     │  │                     │  │                     │ │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Azure Front Door (Global CDN)                                       │   │
│  │  - SSL/TLS Termination                                               │   │
│  │  - DDoS Protection                                                   │   │
│  │  - WAF (Web Application Firewall)                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

🌐 External
├── Custom Domain (kbeauty.yourdomain.com)
├── SSL Certificate (Let's Encrypt or Azure)
└── CI/CD Pipeline (GitHub Actions / Azure DevOps)
```

---

## 💰 비용 구성

| 서비스 | SKU | 수량 | 월간 비용 | 비고 |
|--------|-----|------|----------|------|
| **컴퓨팅** | | | | |
| App Service | P1v3 | 2 | $292 | 고가용성 (2 인스턴스) |
| Azure Functions | Premium EP1 | 1 | $50 | 서버리스 |
| **AI/ML** | | | | |
| Azure OpenAI | S0 | 1 | $200-400 | 높은 사용량 |
| Cognitive Search | S1 | 1 | $250 | Vector Search |
| **데이터** | | | | |
| SQL Database | S3 | 1 | $200 | 100 DTU, 250GB |
| Blob Storage | Standard GRS | 1 | $20 | 지역 중복 |
| Redis Cache | C1 | 1 | $75 | 1GB 캐싱 |
| **네트워크/보안** | | | | |
| API Management | Developer | 1 | $50 | API 게이트웨이 |
| Front Door | Standard | 1 | $35 | CDN + WAF |
| Key Vault | Standard | 1 | $0.03 | 비밀 관리 |
| **모니터링** | | | | |
| Application Insights | Standard | 1 | $20 | APM |
| Log Analytics | Pay-as-you-go | 1 | $10 | 로그 수집 |
| **백업** | | | | |
| Backup Storage | GRS | 1 | $10 | 재해 복구 |
| **총 비용** | | | **$700-1,000** | |

### 트래픽별 비용 예측

| 일일 사용자 | 월간 질문 | OpenAI 비용 | 총 비용 |
|------------|----------|-------------|---------|
| 100 | 3,000 | $50 | $700 |
| 500 | 15,000 | $150 | $800 |
| 1,000 | 30,000 | $300 | $950 |
| 5,000 | 150,000 | $1,500 | $2,150 |

---

## 🚀 배포 방법

### Terraform 자동 배포

#### 1. 사전 준비

```bash
# Azure CLI 로그인
az login

# 적절한 구독 선택
az account list --output table
az account set --subscription "<subscription-id>"

# Terraform 초기화
cd terraform/v3-production
terraform init
```

#### 2. 변수 설정

`variables.tfvars`:
```hcl
project_name = "kbeauty"
environment  = "prod"
location     = "koreacentral"
admin_email  = "admin@yourdomain.com"

# 고급 설정
enable_auto_scale     = true
min_instances         = 2
max_instances         = 10
enable_backup         = true
enable_monitoring     = true
enable_waf            = true

# 도메인 설정
custom_domain         = "kbeauty.yourdomain.com"
ssl_certificate_name  = "kbeauty-ssl"

# 네트워크 설정
vnet_address_space    = "10.0.0.0/16"
subnet_web            = "10.0.1.0/24"
subnet_data           = "10.0.2.0/24"
subnet_ai             = "10.0.3.0/24"
```

#### 3. 배포 실행

```bash
# 계획 확인
terraform plan -var-file="variables.tfvars" -out=tfplan

# 배포 (약 30-60분 소요)
terraform apply tfplan

# 출력 확인
terraform output
```

#### 4. 사후 설정

```bash
# 1. Azure OpenAI 모델 배포
# Portal에서 수동 배포 필요

# 2. Cognitive Search 인덱스 생성
az search index create \
  --service-name search-kbeauty-prod \
  --name kbeauty-reviews \
  --fields @search-schema.json

# 3. SQL Database 스키마 생성
sqlcmd -S sql-kbeauty-prod.database.windows.net \
  -d kbeauty-db \
  -U sqladmin \
  -P <password> \
  -i schema.sql

# 4. 데이터 마이그레이션
python migrate_to_production.py
```

---

## 🔧 고급 기능 설정

### 1. 자동 확장 (Auto Scaling)

```bash
# App Service 자동 확장 규칙
az monitor autoscale create \
  --resource-group rg-kbeauty-prod \
  --resource /subscriptions/<sub-id>/resourceGroups/rg-kbeauty-prod/providers/Microsoft.Web/serverfarms/asp-kbeauty-prod \
  --name autoscale-kbeauty \
  --min-count 2 \
  --max-count 10 \
  --count 2

# CPU 기반 확장
az monitor autoscale rule create \
  --resource-group rg-kbeauty-prod \
  --autoscale-name autoscale-kbeauty \
  --condition "Percentage CPU > 70 avg 5m" \
  --scale out 1

# 메모리 기반 확장
az monitor autoscale rule create \
  --resource-group rg-kbeauty-prod \
  --autoscale-name autoscale-kbeauty \
  --condition "Memory Percentage > 80 avg 5m" \
  --scale out 1
```

### 2. Private Endpoints

```bash
# Azure OpenAI Private Endpoint
az network private-endpoint create \
  --resource-group rg-kbeauty-prod \
  --name pe-openai \
  --vnet-name vnet-kbeauty-prod \
  --subnet subnet-ai \
  --private-connection-resource-id /subscriptions/<sub-id>/resourceGroups/rg-kbeauty-prod/providers/Microsoft.CognitiveServices/accounts/openai-kbeauty-prod \
  --group-id account \
  --connection-name openai-connection

# SQL Database Private Endpoint
az network private-endpoint create \
  --resource-group rg-kbeauty-prod \
  --name pe-sql \
  --vnet-name vnet-kbeauty-prod \
  --subnet subnet-data \
  --private-connection-resource-id /subscriptions/<sub-id>/resourceGroups/rg-kbeauty-prod/providers/Microsoft.Sql/servers/sql-kbeauty-prod \
  --group-id sqlServer \
  --connection-name sql-connection
```

### 3. WAF (Web Application Firewall)

```bash
# WAF 정책 생성
az network front-door waf-policy create \
  --resource-group rg-kbeauty-prod \
  --name waf-kbeauty \
  --mode Prevention

# OWASP 규칙 추가
az network front-door waf-policy managed-rules add \
  --policy-name waf-kbeauty \
  --resource-group rg-kbeauty-prod \
  --type Microsoft_DefaultRuleSet \
  --version 2.1

# Rate Limiting
az network front-door waf-policy rule create \
  --policy-name waf-kbeauty \
  --resource-group rg-kbeauty-prod \
  --name RateLimitRule \
  --rule-type RateLimitRule \
  --rate-limit-threshold 100 \
  --rate-limit-duration-in-minutes 1
```

### 4. CI/CD 파이프라인

#### GitHub Actions

`.github/workflows/deploy-production.yml`:
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements_azure.txt
    
    - name: Run tests
      run: |
        pytest tests/
    
    - name: Azure Login
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}
    
    - name: Deploy to App Service
      uses: azure/webapps-deploy@v2
      with:
        app-name: 'app-kbeauty-prod'
        package: .
    
    - name: Run smoke tests
      run: |
        python tests/smoke_test.py
```

---

## 🔒 보안 강화

### 1. VNet 통합

```bash
# App Service VNet 통합
az webapp vnet-integration add \
  --resource-group rg-kbeauty-prod \
  --name app-kbeauty-prod \
  --vnet vnet-kbeauty-prod \
  --subnet subnet-web

# 아웃바운드 트래픽 제한
az webapp config set \
  --resource-group rg-kbeauty-prod \
  --name app-kbeauty-prod \
  --vnet-route-all-enabled true
```

### 2. Managed Identity

```bash
# System-assigned Identity 활성화
az webapp identity assign \
  --resource-group rg-kbeauty-prod \
  --name app-kbeauty-prod

# Key Vault 접근 권한
az keyvault set-policy \
  --name kv-kbeauty-prod \
  --object-id <identity-id> \
  --secret-permissions get list

# SQL Database 접근 권한
az sql server ad-admin create \
  --resource-group rg-kbeauty-prod \
  --server-name sql-kbeauty-prod \
  --display-name app-kbeauty-prod \
  --object-id <identity-id>
```

### 3. DDoS Protection

```bash
# DDoS Protection Plan
az network ddos-protection create \
  --resource-group rg-kbeauty-prod \
  --name ddos-kbeauty \
  --location koreacentral

# VNet에 연결
az network vnet update \
  --resource-group rg-kbeauty-prod \
  --name vnet-kbeauty-prod \
  --ddos-protection true \
  --ddos-protection-plan /subscriptions/<sub-id>/resourceGroups/rg-kbeauty-prod/providers/Microsoft.Network/ddosProtectionPlans/ddos-kbeauty
```

### 4. 감사 로깅

```bash
# SQL Database 감사
az sql server audit-policy update \
  --resource-group rg-kbeauty-prod \
  --name sql-kbeauty-prod \
  --state Enabled \
  --storage-account stkbeautyprod \
  --retention-days 90

# Key Vault 진단 설정
az monitor diagnostic-settings create \
  --resource /subscriptions/<sub-id>/resourceGroups/rg-kbeauty-prod/providers/Microsoft.KeyVault/vaults/kv-kbeauty-prod \
  --name kv-diagnostics \
  --logs '[{"category": "AuditEvent", "enabled": true}]' \
  --workspace /subscriptions/<sub-id>/resourceGroups/rg-kbeauty-prod/providers/Microsoft.OperationalInsights/workspaces/log-kbeauty-prod
```

---

## 📊 모니터링 및 알림

### 1. Application Insights 설정

```bash
# Application Insights 생성
az monitor app-insights component create \
  --app app-kbeauty-prod \
  --location koreacentral \
  --resource-group rg-kbeauty-prod \
  --application-type web

# App Service 연결
az webapp config appsettings set \
  --resource-group rg-kbeauty-prod \
  --name app-kbeauty-prod \
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING="<connection-string>"
```

### 2. 알림 규칙

```bash
# 높은 응답 시간 알림
az monitor metrics alert create \
  --name "High Response Time" \
  --resource-group rg-kbeauty-prod \
  --scopes /subscriptions/<sub-id>/resourceGroups/rg-kbeauty-prod/providers/Microsoft.Web/sites/app-kbeauty-prod \
  --condition "avg ResponseTime > 5000" \
  --description "Response time is above 5 seconds" \
  --evaluation-frequency 1m \
  --window-size 5m \
  --severity 2

# 높은 오류율 알림
az monitor metrics alert create \
  --name "High Error Rate" \
  --resource-group rg-kbeauty-prod \
  --scopes /subscriptions/<sub-id>/resourceGroups/rg-kbeauty-prod/providers/Microsoft.Web/sites/app-kbeauty-prod \
  --condition "avg Http5xx > 10" \
  --description "5xx errors are above 10 per minute" \
  --evaluation-frequency 1m \
  --window-size 5m \
  --severity 1

# 비용 알림
az consumption budget create \
  --budget-name kbeauty-prod-budget \
  --amount 1200 \
  --time-grain Monthly \
  --resource-group rg-kbeauty-prod \
  --notifications \
    threshold=80 \
    operator=GreaterThan \
    contact-emails="admin@yourdomain.com"
```

### 3. 대시보드

```bash
# Azure Dashboard 생성
az portal dashboard create \
  --resource-group rg-kbeauty-prod \
  --name kbeauty-dashboard \
  --input-path dashboard.json
```

---

## 🔄 백업 및 재해 복구

### 1. 자동 백업

```bash
# SQL Database 자동 백업 (기본 활성화)
az sql db show \
  --resource-group rg-kbeauty-prod \
  --server sql-kbeauty-prod \
  --name kbeauty-db \
  --query "earliestRestoreDate"

# Blob Storage 백업
az storage blob copy start-batch \
  --source-account-name stkbeautyprod \
  --source-container clean-data \
  --destination-account-name stkbeautybackup \
  --destination-container backup-$(date +%Y%m%d)

# App Service 백업
az webapp config backup create \
  --resource-group rg-kbeauty-prod \
  --webapp-name app-kbeauty-prod \
  --container-url "https://stkbeautybackup.blob.core.windows.net/backups?<sas-token>" \
  --backup-name backup-$(date +%Y%m%d)
```

### 2. 재해 복구 계획

```bash
# 지역 간 복제 (Geo-Replication)
az sql db replica create \
  --resource-group rg-kbeauty-prod \
  --server sql-kbeauty-prod \
  --name kbeauty-db \
  --partner-server sql-kbeauty-dr \
  --partner-resource-group rg-kbeauty-dr \
  --partner-location japaneast

# 장애 조치 그룹
az sql failover-group create \
  --resource-group rg-kbeauty-prod \
  --server sql-kbeauty-prod \
  --name fg-kbeauty \
  --partner-server sql-kbeauty-dr \
  --partner-resource-group rg-kbeauty-dr \
  --failover-policy Automatic \
  --grace-period 1
```

### 3. 복구 테스트

```bash
# SQL Database 복원 테스트
az sql db restore \
  --resource-group rg-kbeauty-prod \
  --server sql-kbeauty-prod \
  --name kbeauty-db-restored \
  --source-database kbeauty-db \
  --time "2025-12-24T00:00:00Z"

# 장애 조치 테스트
az sql failover-group set-primary \
  --resource-group rg-kbeauty-dr \
  --server sql-kbeauty-dr \
  --name fg-kbeauty
```

---

## 🎯 성능 최적화

### 1. Redis 캐싱

```python
import redis
from functools import wraps

# Redis 연결
redis_client = redis.Redis(
    host='redis-kbeauty-prod.redis.cache.windows.net',
    port=6380,
    password=os.getenv('REDIS_PASSWORD'),
    ssl=True
)

def cache_result(ttl=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 캐시 확인
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # 함수 실행
            result = func(*args, **kwargs)
            
            # 캐시 저장
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result)
            )
            
            return result
        return wrapper
    return decorator

# 사용
@cache_result(ttl=1800)  # 30분 캐싱
def ask_question(question):
    return agent.ask(question)
```

### 2. CDN 최적화

```bash
# Front Door 캐싱 규칙
az network front-door routing-rule create \
  --resource-group rg-kbeauty-prod \
  --front-door-name fd-kbeauty \
  --name caching-rule \
  --patterns "/static/*" \
  --caching-duration "P1D"  # 1일 캐싱
```

### 3. 데이터베이스 최적화

```sql
-- 인덱스 생성
CREATE INDEX idx_product_name ON reviews(product_name);
CREATE INDEX idx_rating ON reviews(rating);
CREATE INDEX idx_date ON reviews(date);

-- 통계 업데이트
UPDATE STATISTICS reviews;

-- 쿼리 성능 분석
SET STATISTICS TIME ON;
SET STATISTICS IO ON;
```

---

## 📈 확장 전략

### 수평 확장 (Scale Out)

```bash
# App Service 인스턴스 증가
az appservice plan update \
  --resource-group rg-kbeauty-prod \
  --name asp-kbeauty-prod \
  --number-of-workers 5

# Cognitive Search 파티션 증가
az search service update \
  --resource-group rg-kbeauty-prod \
  --name search-kbeauty-prod \
  --partition-count 3 \
  --replica-count 3
```

### 수직 확장 (Scale Up)

```bash
# App Service SKU 업그레이드
az appservice plan update \
  --resource-group rg-kbeauty-prod \
  --name asp-kbeauty-prod \
  --sku P2v3  # P1v3 → P2v3

# SQL Database DTU 증가
az sql db update \
  --resource-group rg-kbeauty-prod \
  --server sql-kbeauty-prod \
  --name kbeauty-db \
  --service-objective S6  # S3 → S6 (400 DTU)
```

---

## 🐛 트러블슈팅

### 고급 디버깅

```bash
# Application Insights 쿼리
az monitor app-insights query \
  --app app-kbeauty-prod \
  --analytics-query "requests | where timestamp > ago(1h) | summarize count() by resultCode"

# 느린 쿼리 분석
az sql db show-query-performance \
  --resource-group rg-kbeauty-prod \
  --server sql-kbeauty-prod \
  --database kbeauty-db \
  --top 10
```

---

## 📚 운영 매뉴얼

### 일일 체크리스트

- [ ] Application Insights 대시보드 확인
- [ ] 오류율 < 1%
- [ ] 평균 응답 시간 < 2초
- [ ] CPU 사용률 < 70%
- [ ] 메모리 사용률 < 80%

### 주간 체크리스트

- [ ] 비용 리포트 검토
- [ ] 백업 상태 확인
- [ ] 보안 업데이트 적용
- [ ] 성능 트렌드 분석

### 월간 체크리스트

- [ ] 재해 복구 테스트
- [ ] 용량 계획 검토
- [ ] 비용 최적화 검토
- [ ] SLA 달성률 확인

---

**작성일**: 2025-12-24  
**버전**: v3 (프로덕션)  
**이전 문서**: `V2_OPTIMIZED.md`  
**관련 문서**: `COST_COMPARISON.md`
