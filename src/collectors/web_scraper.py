"""
Web Scraping Service
===================

Amazon/TikTok 웹 크롤링을 담당하는 서비스
스펙 요구사항 2: Amazon 및 TikTok 웹 크롤링 구현

주요 기능:
- Amazon Movers & Shakers 크롤링
- TikTok Creative Center 트렌드 수집
- 프록시 로테이션 및 IP 차단 회피
- 동적 페이지 처리 (Headless Browser)
- 적응형 셀렉터 자동 업데이트

사용법:
    from src.collectors.web_scraper import WebScraper
    
    scraper = WebScraper()
    products = await scraper.scrape_amazon_movers()
    trends = await scraper.scrape_tiktok_trends()
"""

import asyncio
import aiohttp
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProductData:
    """Amazon 제품 데이터 구조"""
    asin: str
    title: str
    brand: str
    price: float
    rank: int
    category: str
    movers_rank_change: int
    korean_brand_detected: bool
    url: str
    collected_at: str


@dataclass
class TrendData:
    """TikTok 트렌드 데이터 구조"""
    hashtag: str
    platform: str
    view_count: int
    post_count: int
    engagement_rate: float
    related_keywords: List[str]
    detected_at: str


@dataclass
class ProxyConfig:
    """프록시 설정 구조"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    is_blocked: bool = False


class ProxyManager:
    """프록시 로테이션 관리자"""
    
    def __init__(self, proxy_list: List[ProxyConfig]):
        self.proxy_list = proxy_list
        self.current_index = 0
        self.blocked_proxies = set()
    
    async def get_proxy(self) -> Optional[ProxyConfig]:
        """사용 가능한 프록시 반환"""
        attempts = 0
        while attempts < len(self.proxy_list):
            proxy = self.proxy_list[self.current_index]
            
            if not proxy.is_blocked:
                return proxy
            
            self._rotate_proxy()
            attempts += 1
        
        logger.warning("모든 프록시가 차단됨")
        return None
    
    async def mark_proxy_blocked(self, proxy: ProxyConfig):
        """프록시를 차단된 것으로 표시"""
        proxy.is_blocked = True
        self.blocked_proxies.add(proxy)
        logger.warning(f"프록시 차단됨: {proxy.host}:{proxy.port}")
        self._rotate_proxy()
    
    def _rotate_proxy(self):
        """다음 프록시로 로테이션"""
        self.current_index = (self.current_index + 1) % len(self.proxy_list)
    
    async def rotate_user_agent(self) -> str:
        """User-Agent 로테이션"""
        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]
        return random.choice(user_agents)


class BrowserPool:
    """Headless Browser 풀 관리"""
    
    def __init__(self, pool_size: int = 3):
        self.pool_size = pool_size
        self.browsers = []
        self.available_browsers = []
    
    async def initialize(self):
        """브라우저 풀 초기화"""
        for i in range(self.pool_size):
            browser = await self._create_browser()
            self.browsers.append(browser)
            self.available_browsers.append(browser)
        
        logger.info(f"브라우저 풀 초기화 완료: {self.pool_size}개")
    
    async def _create_browser(self) -> webdriver.Chrome:
        """새 브라우저 인스턴스 생성"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # User-Agent 설정
        user_agent = await ProxyManager([]).rotate_user_agent()
        options.add_argument(f"--user-agent={user_agent}")
        
        return webdriver.Chrome(options=options)
    
    async def get_browser(self) -> Optional[webdriver.Chrome]:
        """사용 가능한 브라우저 반환"""
        if self.available_browsers:
            return self.available_browsers.pop()
        return None
    
    async def return_browser(self, browser: webdriver.Chrome):
        """브라우저를 풀에 반환"""
        self.available_browsers.append(browser)
    
    async def cleanup(self):
        """브라우저 풀 정리"""
        for browser in self.browsers:
            try:
                browser.quit()
            except Exception as e:
                logger.error(f"브라우저 종료 실패: {e}")


class SelectorConfig:
    """사이트별 셀렉터 설정"""
    
    AMAZON_SELECTORS = {
        "movers_products": [
            "#zg-ordered-list .zg-item-immersion",
            ".zg-item-immersion",
            "[data-testid='product-item']"
        ],
        "product_title": [
            ".p13n-sc-truncate",
            ".zg-item h3 a",
            ".s-size-mini .a-link-normal"
        ],
        "product_rank": [
            ".zg-badge-text",
            ".zg-rank",
            "[data-testid='rank']"
        ],
        "product_price": [
            ".p13n-sc-price",
            ".a-price .a-offscreen",
            ".zg-item .a-price"
        ]
    }
    
    TIKTOK_SELECTORS = {
        "trending_hashtags": [
            "[data-e2e='hashtag-item']",
            ".hashtag-card",
            ".trend-item"
        ],
        "hashtag_name": [
            "[data-e2e='hashtag-name']",
            ".hashtag-title",
            ".trend-name"
        ],
        "view_count": [
            "[data-e2e='view-count']",
            ".view-count",
            ".trend-stats"
        ]
    }


class WebScraper:
    """웹 스크래핑 서비스"""
    
    # K-Beauty 관련 브랜드 목록
    KOREAN_BRANDS = [
        'amorepacific', 'sulwhasoo', 'laneige', 'innisfree',
        'etude house', 'the face shop', 'missha', 'skinfood',
        'tony moly', 'cosrx', 'some by mi', 'purito',
        'beauty of joseon', 'torriden', 'round lab', 'anua',
        'biodance', 'tirtir', 'iope', 'hera', 'mamonde',
        'dear klairs', 'benton', 'klairs', 'neogen'
    ]
    
    def __init__(self, proxy_list: Optional[List[ProxyConfig]] = None):
        """
        웹 스크래퍼 초기화
        
        Args:
            proxy_list: 프록시 설정 목록
        """
        self.proxy_manager = ProxyManager(proxy_list or [])
        self.browser_pool = BrowserPool()
        self.selector_config = SelectorConfig()
        self.session = None
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession()
        await self.browser_pool.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
        await self.browser_pool.cleanup()
    
    async def scrape_amazon_movers(self, category: str = "beauty") -> List[ProductData]:
        """
        Amazon Movers & Shakers 크롤링
        
        Args:
            category: 카테고리 (beauty, skincare 등)
            
        Returns:
            ProductData 객체 리스트
        """
        products = []
        
        try:
            logger.info(f"Amazon Movers & Shakers 크롤링 시작: {category}")
            
            # Amazon Movers & Shakers URL
            url = f"https://www.amazon.com/gp/movers-and-shakers/{category}"
            
            # Headless Browser로 동적 페이지 처리
            browser = await self.browser_pool.get_browser()
            if not browser:
                logger.error("사용 가능한 브라우저가 없음")
                return products
            
            try:
                await self._navigate_with_retry(browser, url)
                
                # 페이지 로딩 대기
                await asyncio.sleep(3)
                
                # 제품 데이터 파싱
                products = await self._parse_amazon_products(browser)
                
                logger.info(f"Amazon에서 {len(products)}개 제품 수집 완료")
                
            finally:
                await self.browser_pool.return_browser(browser)
                
        except Exception as e:
            logger.error(f"Amazon 크롤링 실패: {e}")
        
        return products
    
    async def scrape_tiktok_trends(self) -> List[TrendData]:
        """
        TikTok Creative Center 트렌드 수집
        
        Returns:
            TrendData 객체 리스트
        """
        trends = []
        
        try:
            logger.info("TikTok 트렌드 크롤링 시작")
            
            # TikTok Creative Center URL (해시태그 트렌드)
            url = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
            
            browser = await self.browser_pool.get_browser()
            if not browser:
                logger.error("사용 가능한 브라우저가 없음")
                return trends
            
            try:
                await self._navigate_with_retry(browser, url)
                
                # 동적 콘텐츠 로딩 대기
                await asyncio.sleep(5)
                
                # 무한 스크롤 처리
                await self._handle_infinite_scroll(browser)
                
                # 트렌드 데이터 파싱
                trends = await self._parse_tiktok_trends(browser)
                
                logger.info(f"TikTok에서 {len(trends)}개 트렌드 수집 완료")
                
            finally:
                await self.browser_pool.return_browser(browser)
                
        except Exception as e:
            logger.error(f"TikTok 크롤링 실패: {e}")
        
        return trends
    
    async def handle_dynamic_content(self, url: str) -> BeautifulSoup:
        """
        동적 페이지 처리
        
        Args:
            url: 처리할 URL
            
        Returns:
            BeautifulSoup 객체
        """
        browser = await self.browser_pool.get_browser()
        if not browser:
            raise Exception("사용 가능한 브라우저가 없음")
        
        try:
            await self._navigate_with_retry(browser, url)
            await asyncio.sleep(3)
            
            # JavaScript 실행 완료 대기
            WebDriverWait(browser, 10).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            page_source = browser.page_source
            return BeautifulSoup(page_source, 'html.parser')
            
        finally:
            await self.browser_pool.return_browser(browser)
    
    async def adaptive_selector_update(self, site: str) -> SelectorConfig:
        """
        적응형 셀렉터 자동 업데이트
        
        Args:
            site: 사이트 이름 (amazon, tiktok)
            
        Returns:
            업데이트된 SelectorConfig
        """
        # 실제 구현에서는 ML 모델이나 휴리스틱을 사용하여
        # DOM 구조 변경을 감지하고 셀렉터를 자동 업데이트
        logger.info(f"{site} 셀렉터 업데이트 확인 중...")
        
        # 현재는 기본 설정 반환
        return self.selector_config
    
    async def _navigate_with_retry(self, browser: webdriver.Chrome, url: str, max_retries: int = 3):
        """재시도 로직이 있는 페이지 네비게이션"""
        for attempt in range(max_retries):
            try:
                browser.get(url)
                
                # 페이지 로딩 확인
                WebDriverWait(browser, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # IP 차단 감지
                if await self._detect_ip_block(browser):
                    logger.warning(f"IP 차단 감지, 프록시 변경 시도 ({attempt + 1}/{max_retries})")
                    await self._handle_ip_block()
                    continue
                
                return  # 성공
                
            except TimeoutException:
                logger.warning(f"페이지 로딩 타임아웃 ({attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # 지수 백오프
    
    async def _detect_ip_block(self, browser: webdriver.Chrome) -> bool:
        """IP 차단 감지"""
        page_source = browser.page_source.lower()
        
        # 차단 관련 키워드 감지
        block_indicators = [
            "captcha", "robot", "automated", "blocked",
            "access denied", "rate limit", "too many requests"
        ]
        
        return any(indicator in page_source for indicator in block_indicators)
    
    async def _handle_ip_block(self):
        """IP 차단 처리"""
        # 프록시 변경
        current_proxy = await self.proxy_manager.get_proxy()
        if current_proxy:
            await self.proxy_manager.mark_proxy_blocked(current_proxy)
        
        # 딜레이 증가
        delay = random.uniform(10, 30)
        logger.info(f"IP 차단 회피를 위해 {delay:.1f}초 대기")
        await asyncio.sleep(delay)
    
    async def _handle_infinite_scroll(self, browser: webdriver.Chrome, max_scrolls: int = 5):
        """무한 스크롤 처리"""
        for i in range(max_scrolls):
            # 페이지 끝까지 스크롤
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # 새 콘텐츠 로딩 대기
            await asyncio.sleep(2)
            
            # 더 이상 로딩할 콘텐츠가 없는지 확인
            current_height = browser.execute_script("return document.body.scrollHeight")
            await asyncio.sleep(1)
            new_height = browser.execute_script("return document.body.scrollHeight")
            
            if current_height == new_height:
                logger.info(f"무한 스크롤 완료: {i + 1}회 스크롤")
                break
    
    async def _parse_amazon_products(self, browser: webdriver.Chrome) -> List[ProductData]:
        """Amazon 제품 데이터 파싱"""
        products = []
        
        try:
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            
            # 여러 셀렉터 시도
            product_elements = None
            for selector in self.selector_config.AMAZON_SELECTORS["movers_products"]:
                product_elements = soup.select(selector)
                if product_elements:
                    break
            
            if not product_elements:
                logger.warning("Amazon 제품 요소를 찾을 수 없음")
                return products
            
            for idx, element in enumerate(product_elements[:50]):  # 상위 50개만
                try:
                    product = await self._extract_amazon_product(element, idx + 1)
                    if product and product.korean_brand_detected:
                        products.append(product)
                        logger.debug(f"K-Beauty 제품 발견: {product.title[:50]}...")
                        
                except Exception as e:
                    logger.error(f"제품 파싱 실패: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Amazon 제품 파싱 실패: {e}")
        
        return products
    
    async def _extract_amazon_product(self, element, rank: int) -> Optional[ProductData]:
        """개별 Amazon 제품 데이터 추출"""
        try:
            # 제목 추출
            title_elem = None
            for selector in self.selector_config.AMAZON_SELECTORS["product_title"]:
                title_elem = element.select_one(selector)
                if title_elem:
                    break
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            
            # K-Beauty 브랜드 감지
            title_lower = title.lower()
            korean_brands = [
                brand for brand in self.KOREAN_BRANDS
                if brand in title_lower
            ]
            
            if not korean_brands:
                return None  # K-Beauty 제품이 아님
            
            # 가격 추출
            price = 0.0
            price_elem = None
            for selector in self.selector_config.AMAZON_SELECTORS["product_price"]:
                price_elem = element.select_one(selector)
                if price_elem:
                    break
            
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # $19.99 형식에서 숫자만 추출
                import re
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace('$', ''))
                if price_match:
                    price = float(price_match.group().replace(',', ''))
            
            # URL 추출
            url = ""
            link_elem = element.select_one("a[href]")
            if link_elem:
                href = link_elem.get("href", "")
                url = href if href.startswith("http") else f"https://www.amazon.com{href}"
            
            # ASIN 추출 (URL에서)
            asin = ""
            if "/dp/" in url:
                asin = url.split("/dp/")[1].split("/")[0].split("?")[0]
            
            return ProductData(
                asin=asin,
                title=title,
                brand=korean_brands[0] if korean_brands else "",
                price=price,
                rank=rank,
                category="beauty",
                movers_rank_change=0,  # 실제로는 이전 데이터와 비교 필요
                korean_brand_detected=True,
                url=url,
                collected_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Amazon 제품 데이터 추출 실패: {e}")
            return None
    
    async def _parse_tiktok_trends(self, browser: webdriver.Chrome) -> List[TrendData]:
        """TikTok 트렌드 데이터 파싱"""
        trends = []
        
        try:
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            
            # 해시태그 요소 찾기
            hashtag_elements = None
            for selector in self.selector_config.TIKTOK_SELECTORS["trending_hashtags"]:
                hashtag_elements = soup.select(selector)
                if hashtag_elements:
                    break
            
            if not hashtag_elements:
                logger.warning("TikTok 해시태그 요소를 찾을 수 없음")
                return trends
            
            for element in hashtag_elements[:20]:  # 상위 20개만
                try:
                    trend = await self._extract_tiktok_trend(element)
                    if trend and self._is_beauty_related(trend.hashtag):
                        trends.append(trend)
                        logger.debug(f"뷰티 관련 트렌드 발견: {trend.hashtag}")
                        
                except Exception as e:
                    logger.error(f"트렌드 파싱 실패: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"TikTok 트렌드 파싱 실패: {e}")
        
        return trends
    
    async def _extract_tiktok_trend(self, element) -> Optional[TrendData]:
        """개별 TikTok 트렌드 데이터 추출"""
        try:
            # 해시태그 이름 추출
            hashtag_elem = None
            for selector in self.selector_config.TIKTOK_SELECTORS["hashtag_name"]:
                hashtag_elem = element.select_one(selector)
                if hashtag_elem:
                    break
            
            if not hashtag_elem:
                return None
            
            hashtag = hashtag_elem.get_text(strip=True).replace('#', '')
            
            # 조회수 추출
            view_count = 0
            view_elem = None
            for selector in self.selector_config.TIKTOK_SELECTORS["view_count"]:
                view_elem = element.select_one(selector)
                if view_elem:
                    break
            
            if view_elem:
                view_text = view_elem.get_text(strip=True)
                # "1.2M views" 형식 파싱
                import re
                view_match = re.search(r'([\d.]+)([KMB])?', view_text)
                if view_match:
                    number = float(view_match.group(1))
                    multiplier = view_match.group(2)
                    if multiplier == 'K':
                        view_count = int(number * 1000)
                    elif multiplier == 'M':
                        view_count = int(number * 1000000)
                    elif multiplier == 'B':
                        view_count = int(number * 1000000000)
                    else:
                        view_count = int(number)
            
            return TrendData(
                hashtag=hashtag,
                platform="tiktok",
                view_count=view_count,
                post_count=0,  # TikTok에서 제공하지 않는 경우가 많음
                engagement_rate=0.0,  # 계산 필요
                related_keywords=[],  # 추후 NLP로 추출
                detected_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"TikTok 트렌드 데이터 추출 실패: {e}")
            return None
    
    def _is_beauty_related(self, hashtag: str) -> bool:
        """뷰티 관련 해시태그 판별"""
        beauty_keywords = [
            'beauty', 'skincare', 'makeup', 'cosmetics', 'korean',
            'kbeauty', 'glassskin', 'routine', 'serum', 'toner',
            'cream', 'mask', 'cleanser', 'sunscreen', 'moisturizer'
        ]
        
        hashtag_lower = hashtag.lower()
        return any(keyword in hashtag_lower for keyword in beauty_keywords)


# 사용 예시
async def main():
    """사용 예시"""
    async with WebScraper() as scraper:
        # Amazon Movers & Shakers 크롤링
        products = await scraper.scrape_amazon_movers("beauty")
        print(f"수집된 K-Beauty 제품: {len(products)}개")
        
        # TikTok 트렌드 크롤링
        trends = await scraper.scrape_tiktok_trends()
        print(f"수집된 뷰티 트렌드: {len(trends)}개")


if __name__ == "__main__":
    asyncio.run(main())