# 글로벌 바이럴 조기 경보 시스템 - 요구사항 명세서

## 소개

해외 바이럴 트렌드를 실시간 감지하여 아모레퍼시픽의 선제적 대응을 지원하는 엔터프라이즈급 바이럴 감지 시스템입니다. 트렌드가 매출로 터지기 전 골든타임을 확보하여 생산(SCM) 및 마케팅 팀의 선제적 대응을 가능하게 합니다.

## 용어 정의

- **Viral_Detection_System**: 글로벌 바이럴 조기 경보 시스템
- **YouTube_API_Client**: YouTube Data API v3 클라이언트
- **Web_Scraper**: Amazon/TikTok 웹 크롤링 엔진
- **Signal_Processor**: 바이럴 신호 분석 및 처리 엔진
- **Alert_Manager**: 알림 생성 및 전송 관리자
- **Data_Pipeline**: 데이터 수집, 처리, 저장 파이프라인
- **Rate_Limiter**: API 호출 제한 관리자
- **Proxy_Manager**: IP 차단 회피 프록시 관리자
- **Golden_Time**: 바이럴 감지 후 대응까지의 최적 시간 (1시간 이내)
- **K_Beauty_Keywords**: 한국 뷰티 관련 핵심 키워드 집합
- **Viral_Score**: 바이럴 가능성을 나타내는 점수 (0-10)

## 요구사항

### 요구사항 1: YouTube 데이터 수집

**사용자 스토리:** 마케팅 분석가로서, YouTube에서 K-Beauty 관련 바이럴 콘텐츠를 실시간으로 감지하고 싶습니다. 이를 통해 트렌드 변화에 빠르게 대응할 수 있습니다.

#### 승인 기준

1. WHEN YouTube_API_Client가 키워드 검색을 수행할 때, THE System SHALL K-Beauty, Glass Skin, Korean Skincare 키워드로 영상을 검색한다
2. WHEN 경쟁사 브랜드 키워드(Biodance, Tirtir)가 감지될 때, THE System SHALL 해당 영상의 메타데이터를 수집한다
3. WHEN 사전 정의된 글로벌 뷰티 인플루언서 채널에서 신규 업로드가 발생할 때, THE System SHALL 실시간으로 감지한다
4. WHEN 영상 메타데이터를 수집할 때, THE System SHALL 조회수, 좋아요 수, 댓글 수, 게시일, 설명 텍스트를 추출한다
5. WHEN 바이럴 판별을 위해, THE System SHALL 1시간 단위로 동일 영상의 통계를 업데이트한다
6. WHEN 조회수 증가 속도를 계산할 때, THE System SHALL Velocity 기반 Viral_Score를 생성한다

### 요구사항 2: Amazon 및 TikTok 웹 크롤링

**사용자 스토리:** 트렌드 분석가로서, Amazon과 TikTok에서 급상승하는 K-Beauty 제품과 해시태그를 모니터링하고 싶습니다. 이를 통해 시장 변화를 조기에 포착할 수 있습니다.

#### 승인 기준

1. WHEN Web_Scraper가 Amazon Movers & Shakers를 크롤링할 때, THE System SHALL 10분 단위로 뷰티 카테고리 페이지를 수집한다
2. WHEN Amazon 제품 랭킹이 급상승할 때, THE System SHALL 제품명과 브랜드명을 파싱한다
3. WHEN TikTok 트렌드를 수집할 때, THE System SHALL Creative Center 또는 해시태그 검색 페이지를 크롤링한다
4. WHEN TikTok 상위 노출 영상을 발견할 때, THE System SHALL 해시태그와 영상 메타데이터를 추출한다
5. WHEN 동적 페이지(Infinite Scroll)를 처리할 때, THE System SHALL Headless Browser를 사용한다
6. WHEN DOM 구조가 변경될 때, THE System SHALL 자동으로 셀렉터를 업데이트한다

### 요구사항 3: 멀티미디어 및 텍스트 처리

**사용자 스토리:** 제품 분석가로서, 영상에서 실제 제품을 식별하고 관련 링크를 추적하고 싶습니다. 이를 통해 정확한 제품 매칭과 판매 채널을 파악할 수 있습니다.

#### 승인 기준

1. WHEN 영상에서 제품이 등장할 때, THE System SHALL 해당 구간의 프레임을 캡처한다
2. WHEN 프레임이 캡처될 때, THE System SHALL Google Lens 연동을 위한 이미지 형식으로 저장한다
3. WHEN 인플루언서 프로필을 분석할 때, THE System SHALL Bio Link의 Linktree, Amazon Storefront 링크를 추적한다
4. WHEN 영상 설명란을 파싱할 때, THE System SHALL 실제 판매 제품 링크를 식별한다
5. WHEN 해외 댓글을 처리할 때, THE System SHALL 영어, 일본어 텍스트를 추출하고 정제한다
6. WHEN 다국어 텍스트를 분석할 때, THE System SHALL 언어별 감정 분석과 키워드 추출을 수행한다

### 요구사항 4: 실시간 성능 및 적시성

**사용자 스토리:** 운영 관리자로서, 바이럴 트렌드를 골든타임 내에 감지하고 싶습니다. 이를 통해 경쟁사보다 빠른 대응이 가능합니다.

#### 승인 기준

1. WHEN 급상승 데이터가 수집될 때, THE System SHALL 1시간 이내에 최신화한다
2. WHEN 수천 개의 키워드를 처리할 때, THE System SHALL 비동기 처리(AsyncIO)를 사용한다
3. WHEN 대량의 URL을 동시 처리할 때, THE System SHALL 분산 큐(Celery, Kafka)를 적용한다
4. WHEN 병렬 처리를 수행할 때, THE System SHALL CPU 및 메모리 사용량을 최적화한다
5. WHEN 데이터 처리 지연이 발생할 때, THE System SHALL 우선순위 기반 처리 순서를 적용한다
6. WHEN 시스템 부하가 높을 때, THE System SHALL 자동으로 처리 용량을 확장한다

### 요구사항 5: 안정성 및 차단 회피

**사용자 스토리:** 시스템 관리자로서, API 제한과 IP 차단 없이 안정적으로 데이터를 수집하고 싶습니다. 이를 통해 지속적인 모니터링이 가능합니다.

#### 승인 기준

1. WHEN YouTube API를 호출할 때, THE Rate_Limiter SHALL 할당량(Quota) 초과를 방지한다
2. WHEN API 할당량이 부족할 때, THE System SHALL 다중 API 키 로테이션을 수행한다
3. WHEN Amazon/TikTok을 크롤링할 때, THE Proxy_Manager SHALL IP 차단을 회피한다
4. WHEN IP 차단이 감지될 때, THE System SHALL 자동으로 프록시 서버를 변경한다
5. WHEN User-Agent를 설정할 때, THE System SHALL 실제 브라우저와 동일한 헤더를 사용한다
6. WHEN 크롤링 속도를 조절할 때, THE System SHALL 사이트별 최적 딜레이를 적용한다

### 요구사항 6: 데이터 품질 관리

**사용자 스토리:** 데이터 분석가로서, 중복되지 않고 정확한 데이터만 수집하고 싶습니다. 이를 통해 신뢰할 수 있는 분석 결과를 얻을 수 있습니다.

#### 승인 기준

1. WHEN 동일한 콘텐츠가 수집될 때, THE System SHALL 고유 ID(Video ID, ASIN) 기반으로 중복을 제거한다
2. WHEN 스팸 댓글이 감지될 때, THE System SHALL 광고성 콘텐츠를 필터링한다
3. WHEN 관련 없는 영상이 수집될 때, THE System SHALL 오분류를 1차적으로 걸러낸다
4. WHEN 데이터 품질을 검증할 때, THE System SHALL 키워드 관련성 점수를 계산한다
5. WHEN 노이즈 데이터가 발견될 때, THE System SHALL 자동으로 제외하고 로그를 기록한다
6. WHEN 데이터 정확성을 보장할 때, THE System SHALL 수집된 데이터의 품질 메트릭을 제공한다

### 요구사항 7: 바이럴 신호 분석 및 알림

**사용자 스토리:** 마케팅 팀장으로서, 바이럴 가능성이 높은 신호를 즉시 알림받고 싶습니다. 이를 통해 신속한 의사결정과 대응이 가능합니다.

#### 승인 기준

1. WHEN 바이럴 신호가 감지될 때, THE Signal_Processor SHALL Viral_Score를 계산한다
2. WHEN Viral_Score가 임계값을 초과할 때, THE Alert_Manager SHALL 즉시 알림을 발송한다
3. WHEN 다중 플랫폼에서 동일 브랜드가 급상승할 때, THE System SHALL 고위험 알림을 생성한다
4. WHEN 아비트라지 기회가 발견될 때, THE System SHALL 가격 차이와 수익률을 계산한다
5. WHEN 알림을 발송할 때, THE System SHALL Slack, 이메일, SMS 등 다중 채널을 지원한다
6. WHEN 알림 내용을 구성할 때, THE System SHALL 액션 가능한 구체적 정보를 포함한다

### 요구사항 8: 시스템 확장성 및 모니터링

**사용자 스토리:** DevOps 엔지니어로서, 시스템의 상태를 모니터링하고 필요시 확장할 수 있기를 원합니다. 이를 통해 안정적인 서비스 운영이 가능합니다.

#### 승인 기준

1. WHEN 시스템 부하가 증가할 때, THE System SHALL 자동으로 워커 인스턴스를 확장한다
2. WHEN 데이터 수집량이 급증할 때, THE System SHALL 스토리지 용량을 자동 확장한다
3. WHEN 시스템 오류가 발생할 때, THE System SHALL 상세한 로그와 메트릭을 기록한다
4. WHEN 성능 지표를 모니터링할 때, THE System SHALL 대시보드를 통해 실시간 현황을 제공한다
5. WHEN 시스템 장애가 감지될 때, THE System SHALL 자동 복구 메커니즘을 실행한다
6. WHEN 백업이 필요할 때, THE System SHALL 수집된 데이터를 안전하게 보관한다

### 요구사항 9: API 통합 및 외부 서비스 연동

**사용자 스토리:** 개발자로서, 다양한 외부 API와 서비스를 안정적으로 연동하고 싶습니다. 이를 통해 풍부한 데이터 소스를 활용할 수 있습니다.

#### 승인 기준

1. WHEN YouTube Data API v3를 호출할 때, THE System SHALL 인증 토큰을 자동 갱신한다
2. WHEN Google Lens API를 사용할 때, THE System SHALL 이미지 인식 결과를 파싱한다
3. WHEN 번역 API를 호출할 때, THE System SHALL 다국어 텍스트를 한국어로 번역한다
4. WHEN 외부 API가 실패할 때, THE System SHALL 재시도 로직과 fallback 메커니즘을 적용한다
5. WHEN API 응답을 처리할 때, THE System SHALL 스키마 검증과 데이터 정제를 수행한다
6. WHEN 서드파티 서비스와 통신할 때, THE System SHALL 보안 프로토콜(HTTPS, OAuth)을 준수한다

### 요구사항 10: 데이터 저장 및 검색

**사용자 스토리:** 데이터 엔지니어로서, 대용량 데이터를 효율적으로 저장하고 빠르게 검색하고 싶습니다. 이를 통해 히스토리 분석과 트렌드 예측이 가능합니다.

#### 승인 기준

1. WHEN 수집된 데이터를 저장할 때, THE System SHALL 시계열 데이터베이스를 사용한다
2. WHEN 대용량 미디어 파일을 저장할 때, THE System SHALL 클라우드 스토리지(S3, Azure Blob)를 활용한다
3. WHEN 데이터를 검색할 때, THE System SHALL 인덱싱을 통해 1초 이내 응답한다
4. WHEN 히스토리 데이터를 조회할 때, THE System SHALL 날짜, 키워드, 플랫폼별 필터링을 지원한다
5. WHEN 데이터 백업을 수행할 때, THE System SHALL 일일 자동 백업과 주간 아카이빙을 실행한다
6. WHEN 데이터 보존 정책을 적용할 때, THE System SHALL 90일 이후 오래된 데이터를 아카이브한다