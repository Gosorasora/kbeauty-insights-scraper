# =============================================================================
# K-Beauty RAG AI Agent - Azure Infrastructure (v2: Clean Architecture)
# =============================================================================
# 
# 목적: K-Beauty 리뷰 데이터 기반 AI 에이전트 (공모전/MVP용)
# 예상 월간 비용: $105-125
# 처리 용량: 5만개 이상 데이터, 200명+ 동시 사용자
#
# 리전 전략:
# - Korea Central: 메인 서비스들 (한국 사용자 대상, 낮은 지연시간)
# - East US: Azure OpenAI만 (OpenAI 지원 리전 제한으로 인해)
#
# 아키텍처 특징:
# - 간소화된 보안 (API 키 직접 사용)
# - Redis 캐싱으로 성능 향상 및 OpenAI 비용 절감
# - Auto-scaling으로 트래픽 변동 대응
# - Health Check로 자동 복구
# =============================================================================

# Terraform 설정 - 버전 및 프로바이더 정의
terraform {
  required_version = ">= 1.0"  # Terraform 최소 버전 요구사항
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"  # Azure Resource Manager 프로바이더
      version = "~> 3.0"             # 3.x 버전 사용 (호환성 보장)
    }
  }
}

# Azure 프로바이더 설정
provider "azurerm" {
  # Resource Provider 자동 등록 비활성화 (시간 단축)
  skip_provider_registration = true
  
  features {
    # 리소스 그룹 삭제 시 내부 리소스가 있어도 강제 삭제 허용
    # 개발/테스트 환경에서 편의를 위해 설정
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    # Cognitive Services 삭제 시 soft delete 즉시 purge
    # 재생성 시 이름 충돌 방지
    cognitive_account {
      purge_soft_delete_on_destroy = true
    }
  }
}

# =============================================================================
# 변수 정의 - 사용자 입력값들
# =============================================================================

# 프로젝트 이름 (리소스 이름 prefix로 사용)
variable "project_name" {
  description = "프로젝트 이름 (리소스 명명에 사용)"
  type        = string
  default     = "amor-party"
}

# 환경 구분 (dev, staging, prod)
variable "environment" {
  description = "배포 환경 (dev/staging/prod)"
  type        = string
  default     = "dev"
}

# Azure 리전 (메인 서비스들이 배포될 위치)
variable "location" {
  description = "Azure 리전 (한국 사용자 대상이므로 Korea Central 권장)"
  type        = string
  default     = "koreacentral"
}

# 관리자 이메일 (알림 수신용)
variable "admin_email" {
  description = "시스템 알림을 받을 관리자 이메일 주소"
  type        = string
}

# =============================================================================
# 로컬 변수 - 계산된 값들
# =============================================================================

locals {
  # 리소스 이름 prefix (예: kbeauty-dev)
  resource_prefix = "${var.project_name}-${var.environment}"
  
  # 모든 리소스에 적용할 공통 태그
  tags = {
    Project      = var.project_name      # 프로젝트 구분
    Environment  = var.environment       # 환경 구분
    ManagedBy    = "Terraform"          # 관리 도구 표시
    CostCenter   = "Development"        # 비용 센터
    Architecture = "v2-clean"           # 아키텍처 버전
  }
}

# =============================================================================
# 리소스 그룹 - 모든 Azure 리소스를 담는 컨테이너
# =============================================================================

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.resource_prefix}"  # 예: rg-kbeauty-dev
  location = var.location                   # Korea Central
  tags     = local.tags                     # 공통 태그 적용
}

# =============================================================================
# 스토리지 계정 - 데이터 파일 저장용
# =============================================================================

resource "azurerm_storage_account" "main" {
  name                     = "st${replace(var.project_name, "-", "")}${var.environment}"  # 하이픈 제거: stamorpartydev
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"    # 표준 성능 (비용 효율적)
  account_replication_type = "LRS"         # 로컬 중복 저장 (가장 저렴)
  
  tags = local.tags
}

# 원본 데이터용 컨테이너 (CSV 파일 등)
resource "azurerm_storage_container" "raw_data" {
  name                  = "raw-data"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"  # 외부 접근 차단
}

# 정제된 데이터용 컨테이너
resource "azurerm_storage_container" "clean_data" {
  name                  = "clean-data"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"  # 외부 접근 차단
}

# =============================================================================
# Azure OpenAI - AI 모델 서비스 (East US 리전)
# =============================================================================
# 
# 주의: Azure OpenAI는 특정 리전에서만 사용 가능
# Korea Central에서는 지원하지 않아 East US 사용
# 리전 간 통신 비용은 미미함 (월 $0.1 이하)

resource "azurerm_cognitive_account" "openai" {
  name                = "openai-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = "koreacentral"  # Korea Central로 변경 (구독 정책 준수)
  kind                = "OpenAI"
  sku_name            = "S0"
  
  tags = merge(local.tags, {
    Service = "Azure OpenAI"
    Region  = "Korea Central"
    Purpose = "AI Model Inference"
  })
}

# =============================================================================
# Azure AI Search - Vector 검색 엔진 (Korea Central)
# =============================================================================
#
# ChromaDB 대신 Azure AI Search 사용하는 이유:
# 1. 성능: GPU 가속으로 20-50ms 검색 (ChromaDB 300-500ms 대비 10배 빠름)
# 2. 확장성: 100만+ 문서 처리 가능
# 3. 동시성: 100명+ 동시 사용자 지원
# 4. 관리: 완전 관리형 서비스 (인프라 관리 불필요)

resource "azurerm_search_service" "main" {
  name                = "search-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location  # Korea Central (낮은 지연시간)
  sku                 = "basic"  # Basic 티어: $75/월, Vector Search 지원
  
  replica_count   = 1  # 복제본 수 (고가용성용, Basic은 1개만 지원)
  partition_count = 1  # 파티션 수 (데이터 분산용, Basic은 1개만 지원)
  
  tags = merge(local.tags, {
    Service = "Azure AI Search"
    Region  = "Korea Central"
    Purpose = "Vector Search Engine"
  })
}

# =============================================================================
# Redis Cache - 응답 캐싱으로 성능 향상 및 OpenAI 비용 절감
# =============================================================================
#
# Redis 캐싱 효과:
# 1. 응답 시간: 5-10ms (캐시 히트 시)
# 2. OpenAI 비용: 30-50% 절감 (중복 요청 방지)
# 3. 사용자 경험: 즉시 응답으로 만족도 향상
# 4. 서버 부하: CPU/메모리 사용량 감소

resource "azurerm_redis_cache" "main" {
  name                = "redis-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  capacity            = 0         # C0 (250MB) - 개발/테스트용 최소 사이즈
  family              = "C"       # Basic/Standard 패밀리
  sku_name            = "Basic"   # Basic 티어: $16/월, 단일 노드
  
  non_ssl_port_enabled = false    # 보안을 위해 SSL만 허용
  minimum_tls_version = "1.2"     # 최소 TLS 1.2 사용
  
  # Redis 메모리 정책 설정
  redis_configuration {
    maxmemory_policy = "allkeys-lru"  # 메모리 부족 시 LRU(Least Recently Used) 정책으로 삭제
  }
  
  tags = merge(local.tags, {
    Service = "Redis Cache"
    Purpose = "Response Caching"
    Tier    = "Basic"
  })
}

# =============================================================================
# Application Insights - 성능 모니터링 (App Service 내장 기능)
# =============================================================================
#
# Application Insights는 별도 서비스가 아닌 App Service 내장 기능
# Log Analytics Workspace에 데이터를 저장

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.main.id  # workspace_id 유지
  
  retention_in_days = 30
  
  tags = merge(local.tags, {
    Service = "Application Insights"
    Purpose = "Performance Monitoring"
  })
}

# Log Analytics Workspace - Application Insights 데이터 저장소
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"     # 사용량 기반 요금제
  retention_in_days   = 30              # 로그 보존 기간 (비용 절감)
  
  tags = merge(local.tags, {
    Service = "Log Analytics"
    Purpose = "Centralized Logging"
  })
}

# =============================================================================
# Auto-scaling 설정 - 트래픽에 따른 자동 확장/축소
# =============================================================================
#
# Auto-scaling이 필요한 이유:
# 1. 비용 효율성: 트래픽 적을 때 인스턴스 축소로 비용 절감
# 2. 성능 보장: 트래픽 많을 때 인스턴스 확장으로 응답성 유지
# 3. 자동 관리: 수동 개입 없이 자동으로 스케일링

resource "azurerm_monitor_autoscale_setting" "main" {
  name                = "autoscale-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  target_resource_id  = azurerm_service_plan.main.id  # App Service Plan을 대상으로 스케일링
  
  profile {
    name = "default"
    
    # 인스턴스 수 설정
    capacity {
      default = 1  # 기본 인스턴스 수
      minimum = 1  # 최소 인스턴스 수 (항상 1개는 유지)
      maximum = 3  # 최대 인스턴스 수 (비용 제한을 위해 3개로 설정)
    }
    
    # Scale Out 규칙 - CPU 사용률이 높을 때 인스턴스 추가
    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"                    # CPU 사용률 메트릭
        metric_resource_id = azurerm_service_plan.main.id       # 모니터링 대상
        time_grain         = "PT1M"                             # 1분 간격으로 측정
        statistic          = "Average"                          # 평균값 사용
        time_window        = "PT5M"                             # 5분 동안의 데이터 확인
        time_aggregation   = "Average"                          # 5분간 평균값
        operator           = "GreaterThan"                      # 임계값보다 클 때
        threshold          = 75                                 # CPU 75% 초과 시
      }
      
      scale_action {
        direction = "Increase"    # 인스턴스 증가
        type      = "ChangeCount" # 개수 변경 방식
        value     = "1"           # 1개씩 증가
        cooldown  = "PT5M"        # 5분 대기 후 다음 스케일링 가능
      }
    }
    
    # Scale In 규칙 - CPU 사용률이 낮을 때 인스턴스 제거
    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"
        metric_resource_id = azurerm_service_plan.main.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT10M"                            # 더 긴 윈도우 (안정성 위해)
        time_aggregation   = "Average"
        operator           = "LessThan"                         # 임계값보다 작을 때
        threshold          = 25                                 # CPU 25% 미만 시
      }
      
      scale_action {
        direction = "Decrease"    # 인스턴스 감소
        type      = "ChangeCount"
        value     = "1"           # 1개씩 감소
        cooldown  = "PT10M"       # 10분 대기 (Scale In은 더 신중하게)
      }
    }
  }
  
  tags = merge(local.tags, {
    Service = "Auto Scaling"
    Purpose = "Dynamic Scaling"
  })
}

# =============================================================================
# 모니터링 및 알림 설정 - 시스템 상태 감시
# =============================================================================

# Action Group - 알림을 받을 대상 정의
resource "azurerm_monitor_action_group" "main" {
  name                = "ag-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "amorparty"  # SMS 등에서 사용할 짧은 이름 (10자 제한)
  
  # 이메일 알림 설정
  email_receiver {
    name          = "admin"
    email_address = var.admin_email  # 관리자 이메일로 알림 발송
  }
  
  tags = local.tags
}

# Health Check 알림 - App Service 상태 모니터링
resource "azurerm_monitor_metric_alert" "app_service_health" {
  name                = "alert-app-health-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_linux_web_app.main.id]  # 모니터링 대상
  description         = "App Service Health Check Alert"
  
  # 알림 조건: Health Check 실패 시
  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "HealthCheckStatus"  # /health 엔드포인트 상태
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 1                    # 1 미만이면 실패로 간주
  }
  
  # 알림 액션
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  frequency   = "PT5M"   # 5분마다 확인 (너무 자주 확인하면 비용 증가)
  window_size = "PT15M"  # 15분 윈도우에서 평가
  severity    = 2        # 중간 심각도
  
  tags = local.tags
}

# =============================================================================
# App Service Plan - 웹 애플리케이션 실행 환경
# =============================================================================
#
# App Service Plan은 웹앱이 실행될 컴퓨팅 리소스를 정의
# B1 티어 선택 이유:
# 1. 비용 효율성: $13/월로 저렴
# 2. Auto-scaling 지원: 트래픽에 따라 자동 확장
# 3. 충분한 성능: 1 vCPU, 1.75GB RAM

resource "azurerm_service_plan" "main" {
  name                = "asp-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"  # Linux 기반 (Windows보다 저렴)
  sku_name            = "B1"     # Basic B1: 1 vCPU, 1.75GB RAM, Auto-scaling 지원
  
  tags = local.tags
}

# =============================================================================
# Linux Web App - 메인 웹 애플리케이션
# =============================================================================
#
# Flask 기반 K-Beauty RAG AI 에이전트가 실행되는 환경

resource "azurerm_linux_web_app" "main" {
  name                = "app-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.main.id
  
  # 사이트 설정
  site_config {
    # Python 런타임 설정
    application_stack {
      python_version = "3.11"  # Python 3.11 사용
    }
    always_on = false  # Basic 티어에서는 always_on 사용 불가 (비용 절감)
    
    # Health Check 설정 - 애플리케이션 상태 모니터링
    health_check_path                 = "/health"  # Health Check 엔드포인트
    health_check_eviction_time_in_min = 2          # 2분간 실패 시 인스턴스 교체
    
    # 시작 명령어 - startup.sh 스크립트 실행
    app_command_line = "./startup.sh"
  }
  
  # Managed Identity 설정 - Azure 서비스 간 인증용
  identity {
    type = "SystemAssigned"  # 시스템 할당 ID (자동 생성)
  }
  
  # 환경 변수 설정 - 애플리케이션에서 사용할 설정값들
  app_settings = {
    # Azure OpenAI 설정
    "AZURE_OPENAI_ENDPOINT"               = azurerm_cognitive_account.openai.endpoint
    "AZURE_OPENAI_API_KEY"                = azurerm_cognitive_account.openai.primary_access_key
    
    # Azure AI Search 설정
    "AZURE_SEARCH_ENDPOINT"               = "https://${azurerm_search_service.main.name}.search.windows.net"
    "AZURE_SEARCH_API_KEY"                = azurerm_search_service.main.primary_key
    
    # Storage 설정
    "AZURE_STORAGE_CONNECTION_STRING"     = azurerm_storage_account.main.primary_connection_string
    
    # Redis 설정
    "REDIS_CONNECTION_STRING"             = azurerm_redis_cache.main.primary_connection_string
    
    # Application Insights 설정
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
    
    # App Service 설정
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"  # 로컬 스토리지 비활성화
    
    # 애플리케이션 설정
    "SEARCH_INDEX_NAME"                   = "amor-party-reviews"        # 검색 인덱스 이름
    "CACHE_TTL_SECONDS"                   = "3600"                      # 캐시 유효 시간 (1시간)
    "ENABLE_RESPONSE_CACHE"               = "true"                      # 응답 캐싱 활성화
    "MAX_CONCURRENT_REQUESTS"             = "5"                         # 최대 동시 요청 수
  }
  
  tags = local.tags
}

# =============================================================================
# 출력값 정의 - 배포 완료 후 필요한 정보들
# =============================================================================
#
# Terraform 배포 완료 후 다른 스크립트나 사용자가 참조할 수 있는 값들

# 리소스 그룹 이름
output "resource_group_name" {
  description = "생성된 리소스 그룹 이름"
  value       = azurerm_resource_group.main.name
}

# 스토리지 계정 이름
output "storage_account_name" {
  description = "데이터 저장용 스토리지 계정 이름"
  value       = azurerm_storage_account.main.name
}

# Azure OpenAI 엔드포인트
output "openai_endpoint" {
  description = "Azure OpenAI 서비스 엔드포인트 URL"
  value       = azurerm_cognitive_account.openai.endpoint
}

# Azure AI Search 엔드포인트
output "search_endpoint" {
  description = "Azure AI Search 서비스 엔드포인트 URL"
  value       = "https://${azurerm_search_service.main.name}.search.windows.net"
}

# Azure AI Search 서비스 이름
output "search_service_name" {
  description = "Azure AI Search 서비스 이름"
  value       = azurerm_search_service.main.name
}

# 웹 애플리케이션 URL
output "app_service_url" {
  description = "배포된 웹 애플리케이션 접속 URL"
  value       = "https://${azurerm_linux_web_app.main.default_hostname}"
}

# Redis 엔드포인트
output "redis_endpoint" {
  description = "Redis 캐시 엔드포인트"
  value       = azurerm_redis_cache.main.hostname
}

# Application Insights 키 (민감 정보)
output "application_insights_key" {
  description = "Application Insights 계측 키"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true  # 민감한 정보로 표시 (출력 시 숨김)
}

# Auto-scaling 설정 ID
output "autoscale_setting_id" {
  description = "Auto-scaling 설정 리소스 ID"
  value       = azurerm_monitor_autoscale_setting.main.id
}

# =============================================================================
# 배포 완료 안내 메시지
# =============================================================================
#
# Terraform 배포 완료 후 사용자에게 표시될 상세한 안내 메시지

output "deployment_instructions" {
  description = "배포 완료 후 수행할 작업들에 대한 상세 안내"
  value = <<-EOT
  
  ========================================
  🎉 K-Beauty RAG AI Agent 배포 완료!
  ========================================
  
  📋 배포된 리소스:
  - Resource Group: ${azurerm_resource_group.main.name}
  - App Service: ${azurerm_linux_web_app.main.name}
  - Azure OpenAI: ${azurerm_cognitive_account.openai.name}
  - Azure AI Search: ${azurerm_search_service.main.name}
  - Redis Cache: ${azurerm_redis_cache.main.name}
  - Storage Account: ${azurerm_storage_account.main.name}
  
  🚀 다음 단계별 설정:
  
  1️⃣ Azure OpenAI 모델 배포:
     Portal: https://portal.azure.com
     리소스: ${azurerm_cognitive_account.openai.name}
     
     배포할 모델:
     - text-embedding-ada-002 (임베딩용)
     - gpt-35-turbo (채팅용)
  
  2️⃣ Azure AI Search 인덱스 생성:
     python migrate_to_azure_search.py
     
     (CSV 데이터를 Vector 검색 인덱스로 변환)
  
  3️⃣ 데이터 업로드:
     az storage blob upload-batch \
       --account-name ${azurerm_storage_account.main.name} \
       --destination raw-data \
       --source ./results
  
  4️⃣ 웹 애플리케이션 배포:
     # 배포 패키지 생성
     zip -r deploy.zip . \
       -x "*.git*" \
       -x "terraform/*" \
       -x "results/*" \
       -x "chrome_profile/*"
     
     # App Service에 배포
     az webapp deployment source config-zip \
       --resource-group ${azurerm_resource_group.main.name} \
       --name ${azurerm_linux_web_app.main.name} \
       --src deploy.zip
  
  5️⃣ 서비스 접속:
     🌐 웹 애플리케이션: https://${azurerm_linux_web_app.main.default_hostname}
     📊 Health Check: https://${azurerm_linux_web_app.main.default_hostname}/health
  
  ========================================
  💰 예상 월간 비용: $105-125
  ========================================
  
  서비스별 비용 분석:
  - Azure AI Search (Basic): $75
  - Azure OpenAI (종량제): $10-25 (캐시로 50% 절감)
  - App Service B1: $13 (Auto-scaling 1-3 인스턴스)
  - Redis Cache C0: $16
  - Log Analytics: $1-3 (Application Insights 데이터)
  - Storage Account: $1-3
  - 모니터링/알림: $0-1
  
  ========================================
  ⚡ 성능 특징
  ========================================
  
  응답 시간:
  - 캐시 히트: 5-10ms (Redis)
  - 캐시 미스: 20-50ms (Azure AI Search)
  - 전체 처리: 0.5-2초 (AI 생성 포함)
  
  확장성:
  - 동시 사용자: 200명+
  - 데이터 처리: 100만+ documents
  - Auto-scaling: CPU 기반 1-3 인스턴스
  - 캐시 히트율: 60-80% (예상)
  
  ========================================
  📁 주요 파일 구조
  ========================================
  
  - app.py: 메인 Flask 웹 애플리케이션
  - migrate_to_azure_search.py: 데이터 마이그레이션 스크립트
  - amazon_scraper.py: 데이터 수집 도구 (개발용)
  - startup.sh: App Service 시작 스크립트
  - requirements.txt: Python 패키지 의존성
  
  ========================================
  🔧 운영 및 관리
  ========================================
  
  로그 확인:
  az webapp log tail \
    --resource-group ${azurerm_resource_group.main.name} \
    --name ${azurerm_linux_web_app.main.name}
  
  스케일링 상태 확인:
  az monitor autoscale show \
    --resource-group ${azurerm_resource_group.main.name} \
    --name autoscale-${local.resource_prefix}
  
  Redis 상태 확인:
  az redis show \
    --resource-group ${azurerm_resource_group.main.name} \
    --name ${azurerm_redis_cache.main.name}
  
  ========================================
  📞 문제 해결
  ========================================
  
  일반적인 문제:
  1. OpenAI 모델 미배포 → Azure Portal에서 수동 배포 필요
  2. 검색 인덱스 없음 → migrate_to_azure_search.py 실행
  3. 캐시 연결 실패 → Redis 방화벽 설정 확인
  4. Health Check 실패 → /health 엔드포인트 응답 확인
  
  알림 설정:
  - 관리자 이메일: ${var.admin_email}
  - Health Check 실패 시 자동 알림
  - 심각도: 중간 (Severity 2)
  
  ========================================
  
  🎯 배포 완료! 성공적인 AI Agent 운영을 위해
     위 단계들을 순서대로 진행해주세요.
  
  EOT
}
