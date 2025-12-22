"""
K-Beauty Amazon Review Scraper
- Target: Amazon US 'Korean Skincare' 검색 결과
- 상위 500개 제품의 최근 리뷰 20개씩 수집

사용법:
1. 먼저 Chrome을 디버그 모드로 실행:
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

2. 열린 Chrome에서 Amazon 로그인

3. 스크립트 실행:
   python3 amazon_scraper.py
"""

import csv
import time
import random
import ssl
import os
from datetime import datetime
from typing import Optional

# macOS SSL 인증서 문제 우회
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['WDM_SSL_VERIFY'] = '0'

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException
)
from bs4 import BeautifulSoup


class AmazonKBeautyScraper:
    """Amazon K-Beauty 리뷰 크롤러"""
    
    BASE_URL = "https://www.amazon.com"
    SEARCH_KEYWORD = "Korean Skincare"
    MAX_PRODUCTS = 500  # 상위 500개 제품
    MAX_REVIEWS_PER_PRODUCT = 20  # 제품당 리뷰 수
    DEBUG_PORT = 9222
    
    def __init__(self):
        self.driver = None
        self.reviews_data = []
        self.products_data = []  # 제품 메타데이터 저장
    
    def _random_delay(self, min_sec: float = 2, max_sec: float = 5):
        """사람처럼 보이게 랜덤 딜레이"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def _init_driver(self):
        """기존 Chrome 창에 연결"""
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.DEBUG_PORT}")
        
        try:
            self.driver = webdriver.Chrome(options=options)
            print(f"[INFO] Connected to existing Chrome (port {self.DEBUG_PORT})")
            print(f"[INFO] Current URL: {self.driver.current_url}")
        except Exception as e:
            print(f"[ERROR] Chrome 연결 실패: {e}")
            print("\n" + "="*60)
            print("먼저 Chrome을 디버그 모드로 실행하세요:")
            print("="*60)
            print('/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222')
            print("="*60)
            raise
    
    def _close_driver(self):
        """드라이버 연결 해제 (브라우저는 닫지 않음)"""
        if self.driver:
            # quit() 대신 연결만 해제 - 브라우저는 계속 열려있음
            print("[INFO] Chrome driver disconnected (browser stays open)")

    def search_products(self) -> list[str]:
        """Korean Skincare 검색 후 상위 제품 URL 수집 (페이지네이션 포함)"""
        product_urls = []
        page = 1
        no_new_products_count = 0  # 연속으로 새 제품이 없는 페이지 수
        
        try:
            while len(product_urls) < self.MAX_PRODUCTS:
                # 검색 페이지로 이동 (페이지네이션)
                search_url = f"{self.BASE_URL}/s?k={self.SEARCH_KEYWORD.replace(' ', '+')}&page={page}"
                print(f"\n[INFO] Navigating to page {page}: {search_url}")
                self.driver.get(search_url)
                self._random_delay(4, 7)
                
                # 첫 페이지만 스크린샷
                if page == 1:
                    self.driver.save_screenshot("debug_search_page.png")
                    print("[DEBUG] Screenshot saved: debug_search_page.png")
                
                print(f"[DEBUG] Page title: {self.driver.title}")
                
                # 페이지 소스
                page_source = self.driver.page_source
                
                # 페이지 끝 체크 (Amazon의 "No more results" 메시지)
                if "No results for" in page_source or "did not match any products" in page_source:
                    print(f"[INFO] Reached end of search results at page {page}")
                    break
                
                # CAPTCHA 체크
                soup_check = BeautifulSoup(page_source, "html.parser")
                captcha_form = soup_check.find("form", {"action": lambda x: x and "validateCaptcha" in x if x else False})
                has_captcha = captcha_form is not None
                
                if has_captcha:
                    print("\n" + "="*60)
                    print("[CAPTCHA] CAPTCHA가 감지되었습니다!")
                    print("브라우저에서 CAPTCHA를 풀어주세요.")
                    print("완료 후 Enter를 눌러주세요...")
                    print("="*60)
                    input()
                    page_source = self.driver.page_source
                    print("[INFO] CAPTCHA 해결 후 계속 진행합니다.")
                
                # 여러 셀렉터 시도
                selectors = [
                    "[data-component-type='s-search-result']",
                    "div.s-result-item[data-asin]",
                    ".s-main-slot .s-result-item",
                    "[data-cel-widget^='search_result']",
                    "div[data-asin]"
                ]
                
                soup = BeautifulSoup(page_source, "html.parser")
                product_cards = []
                
                for selector in selectors:
                    try:
                        product_cards = soup.select(selector)
                        product_cards = [c for c in product_cards if c.get("data-asin")]
                        if product_cards:
                            print(f"[INFO] Found {len(product_cards)} products on page {page}")
                            break
                    except Exception as e:
                        continue
                
                if not product_cards:
                    print(f"[WARN] No products found on page {page}")
                    no_new_products_count += 1
                    # 연속 3페이지 제품 없으면 종료
                    if no_new_products_count >= 3:
                        print("[INFO] No products found for 3 consecutive pages, stopping")
                        break
                    page += 1
                    continue
                
                # 제품 URL 추출
                page_products = 0
                for card in product_cards:
                    if len(product_urls) >= self.MAX_PRODUCTS:
                        break
                    try:
                        link_tag = (
                            card.select_one("h2 a.a-link-normal") or
                            card.select_one("a.a-link-normal.s-no-outline") or
                            card.select_one("a.a-link-normal[href*='/dp/']") or
                            card.select_one("a[href*='/dp/']") or
                            card.select_one("a[href]")
                        )
                        if link_tag and link_tag.get("href"):
                            href = link_tag["href"]
                            if "/dp/" not in href and "/gp/" not in href:
                                continue
                            full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                            if full_url not in product_urls:
                                product_urls.append(full_url)
                                page_products += 1
                    except Exception as e:
                        continue
                
                print(f"[INFO] Collected {page_products} products from page {page} (Total: {len(product_urls)})")
                
                # 새 제품이 없으면 카운트 증가
                if page_products == 0:
                    no_new_products_count += 1
                    if no_new_products_count >= 3:
                        print("[INFO] No new products for 3 consecutive pages, stopping")
                        break
                else:
                    no_new_products_count = 0  # 리셋
                
                # 목표 달성 체크
                if len(product_urls) >= self.MAX_PRODUCTS:
                    print(f"[INFO] Reached target of {self.MAX_PRODUCTS} products")
                    break
                
                # 다음 페이지로
                page += 1
                
                # 안전장치: 최대 100페이지까지만
                if page > 100:
                    print("[WARN] Reached maximum page limit (100), stopping")
                    break
                
                self._random_delay(3, 5)
            
            print(f"\n[INFO] Total {len(product_urls)} products collected")
            
        except Exception as e:
            print(f"[ERROR] Search failed: {e}")
            import traceback
            traceback.print_exc()
        
        return product_urls
    
    def _get_product_name(self) -> str:
        """제품명 추출"""
        try:
            title_elem = self.driver.find_element(By.ID, "productTitle")
            return title_elem.text.strip()
        except NoSuchElementException:
            return "Unknown Product"
    
    def _navigate_to_reviews(self) -> bool:
        """리뷰 페이지로 이동"""
        try:
            # 'See all reviews' 링크 찾기
            review_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-hook='see-all-reviews-link-foot']"))
            )
            review_link.click()
            self._random_delay(2, 4)
            return True
        except (TimeoutException, NoSuchElementException):
            # 대체 방법: URL 직접 수정
            try:
                current_url = self.driver.current_url
                if "/dp/" in current_url:
                    asin = current_url.split("/dp/")[1].split("/")[0].split("?")[0]
                    reviews_url = f"{self.BASE_URL}/product-reviews/{asin}"
                    self.driver.get(reviews_url)
                    self._random_delay(2, 4)
                    return True
            except Exception as e:
                print(f"[WARN] Could not navigate to reviews: {e}")
        return False

    def _parse_reviews(self, product_name: str) -> list[dict]:
        """현재 페이지에서 리뷰 파싱"""
        reviews = []
        
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            review_cards = soup.select("[data-hook='review']")
            
            for card in review_cards:
                if len(reviews) >= self.MAX_REVIEWS_PER_PRODUCT:
                    break
                
                try:
                    review = self._extract_review_data(card, product_name)
                    if review:
                        reviews.append(review)
                        print(f"  [OK] Review #{len(reviews)} collected")
                except Exception as e:
                    print(f"  [WARN] Failed to parse review: {e}")
                    continue
                    
        except Exception as e:
            print(f"[ERROR] Review parsing failed: {e}")
        
        return reviews
    
    def _extract_review_data(self, card, product_name: str) -> Optional[dict]:
        """개별 리뷰 데이터 추출"""
        import re
        from datetime import datetime
        
        # 리뷰 본문
        review_body = card.select_one("[data-hook='review-body']")
        review_text = review_body.get_text(strip=True) if review_body else ""
        
        if not review_text:
            return None
        
        # 별점 추출 (여러 방법 시도)
        rating = 0.0
        
        # 방법 1: i 태그의 class에서 추출 (가장 정확)
        rating_elem = card.select_one("i[data-hook='review-star-rating'], i[data-hook='cmps-review-star-rating']")
        if rating_elem:
            # class="a-icon a-icon-star a-star-4" 형식에서 숫자 추출
            class_str = rating_elem.get("class", [])
            if isinstance(class_str, list):
                class_str = " ".join(class_str)
            
            # a-star-4, a-star-4-5 등의 패턴 찾기
            match = re.search(r'a-star-(\d+(?:-\d+)?)', class_str)
            if match:
                star_value = match.group(1)
                if "-" in star_value:
                    # "4-5" -> 4.5
                    parts = star_value.split("-")
                    rating = float(f"{parts[0]}.{parts[1]}")
                else:
                    # "4" -> 4.0
                    rating = float(star_value)
        
        # 방법 2: span 텍스트에서 추출
        if rating == 0.0:
            rating_elem = card.select_one("[data-hook='review-star-rating'] span, [data-hook='cmps-review-star-rating'] span")
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                # "4.0 out of 5 stars" 형식에서 첫 번째 숫자 추출
                match = re.search(r'^(\d+\.?\d*)', rating_text)
                if match:
                    rating = float(match.group(1))
        
        # 방법 3: 전체 텍스트에서 추출
        if rating == 0.0:
            rating_elem = card.select_one("[data-hook='review-star-rating'], [data-hook='cmps-review-star-rating']")
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                match = re.search(r'^(\d+\.?\d*)', rating_text)
                if match:
                    rating = float(match.group(1))
        
        # 날짜 추출 및 변환
        date_elem = card.select_one("[data-hook='review-date']")
        review_date_raw = date_elem.get_text(strip=True) if date_elem else ""
        
        # 날짜를 YYYY-MM-DD 형식으로 변환
        review_date = ""
        if review_date_raw:
            try:
                # "Reviewed in the United States on December 20, 2025" 형식
                # 또는 "미국에서 2025년 11월 24일에 검토됨" 형식
                
                # 영어 날짜 파싱
                if " on " in review_date_raw:
                    date_part = review_date_raw.split(" on ")[-1]
                    parsed_date = datetime.strptime(date_part, "%B %d, %Y")
                    review_date = parsed_date.strftime("%Y-%m-%d")
                # 한국어 날짜 파싱
                elif "년" in review_date_raw and "월" in review_date_raw:
                    # "2025년 11월 24일" 추출
                    match = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', review_date_raw)
                    if match:
                        year, month, day = match.groups()
                        review_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                else:
                    review_date = review_date_raw  # 파싱 실패시 원본 유지
            except Exception as e:
                print(f"  [DEBUG] Date parsing failed: {review_date_raw} - {e}")
                review_date = review_date_raw
        
        # "유용함" 투표 수 추출
        helpful_count = 0
        helpful_elem = card.select_one("[data-hook='helpful-vote-statement']")
        if helpful_elem:
            helpful_text = helpful_elem.get_text(strip=True)
            # "123 people found this helpful" 형식
            match = re.search(r'([\d,]+)\s+people', helpful_text)
            if match:
                helpful_count = int(match.group(1).replace(",", ""))
            # "One person found this helpful" 형식
            elif "One person" in helpful_text or "1 person" in helpful_text:
                helpful_count = 1
        
        # 검증된 구매 여부
        verified_purchase = False
        verified_elem = card.select_one("[data-hook='avp-badge']")
        if verified_elem:
            verified_purchase = True
        
        return {
            "product_name": product_name,
            "review_text": review_text,
            "rating": rating,
            "date": review_date,
            "helpful_count": helpful_count,
            "verified_purchase": verified_purchase,
            "source": "amazon"
        }
    
    def _load_more_reviews(self) -> bool:
        """다음 페이지 리뷰 로드"""
        try:
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "li.a-last a")
            if next_btn:
                next_btn.click()
                self._random_delay(2, 4)
                return True
        except NoSuchElementException:
            pass
        return False

    def scrape_product_reviews(self, product_url: str) -> list[dict]:
        """단일 제품의 리뷰 수집 + 제품 메타데이터"""
        reviews = []
        
        try:
            print(f"\n[INFO] Scraping product: {product_url[:60]}...")
            self.driver.get(product_url)
            self._random_delay(3, 5)
            
            # 제품 메타데이터 수집
            product_metadata = self._extract_product_metadata()
            self.products_data.append(product_metadata)
            
            product_name = product_metadata.get("product_name", "Unknown Product")
            print(f"[INFO] Product: {product_name[:50]}...")
            print(f"[INFO] Price: {product_metadata.get('price', 'N/A')}")
            print(f"[INFO] Rating: {product_metadata.get('avg_rating', 'N/A')} ({product_metadata.get('review_count', 0)} reviews)")
            
            # 리뷰 페이지로 이동
            if not self._navigate_to_reviews():
                print("[WARN] Could not navigate to reviews page")
                return reviews
            
            # 리뷰 수집 (페이지네이션 포함)
            page = 1
            while len(reviews) < self.MAX_REVIEWS_PER_PRODUCT:
                print(f"[INFO] Parsing reviews page {page}...")
                
                page_reviews = self._parse_reviews(product_name)
                if not page_reviews:
                    break
                
                reviews.extend(page_reviews)
                
                if len(reviews) >= self.MAX_REVIEWS_PER_PRODUCT:
                    break
                
                if not self._load_more_reviews():
                    break
                
                page += 1
                self._random_delay(2, 4)
            
            print(f"[INFO] Collected {len(reviews)} reviews for this product")
            
        except Exception as e:
            print(f"[ERROR] Failed to scrape product: {e}")
        
        return reviews[:self.MAX_REVIEWS_PER_PRODUCT]
    
    def _extract_product_metadata(self) -> dict:
        """제품 메타데이터 추출 (가격, 평점, 리뷰 수, 판매량 등)"""
        metadata = {
            "product_name": "Unknown Product",
            "price": None,
            "avg_rating": None,
            "review_count": 0,
            "brand": None,
            "category": None,
            "bought_last_month": 0,  # 지난달 구매 수
            "url": self.driver.current_url
        }
        
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            
            # 제품명
            title_elem = soup.select_one("#productTitle")
            if title_elem:
                metadata["product_name"] = title_elem.get_text(strip=True)
            
            # 가격
            price_elem = (
                soup.select_one(".a-price .a-offscreen") or
                soup.select_one("#priceblock_ourprice") or
                soup.select_one("#priceblock_dealprice")
            )
            if price_elem:
                metadata["price"] = price_elem.get_text(strip=True)
            
            # 평균 별점
            rating_elem = soup.select_one("[data-hook='rating-out-of-text']")
            if rating_elem:
                import re
                rating_text = rating_elem.get_text(strip=True)
                match = re.search(r'(\d+\.?\d*)', rating_text)
                if match:
                    metadata["avg_rating"] = float(match.group(1))
            
            # 리뷰 수
            review_count_elem = soup.select_one("#acrCustomerReviewText")
            if review_count_elem:
                import re
                count_text = review_count_elem.get_text(strip=True)
                match = re.search(r'([\d,]+)', count_text)
                if match:
                    metadata["review_count"] = int(match.group(1).replace(",", ""))
            
            # 브랜드
            brand_elem = soup.select_one("#bylineInfo")
            if brand_elem:
                metadata["brand"] = brand_elem.get_text(strip=True).replace("Visit the ", "").replace(" Store", "")
            
            # 지난달 구매 수 (예: "10K+ bought in past month")
            # 여러 셀렉터 시도
            bought_selectors = [
                "#social-proofing-faceout-title-tk_bought",
                "[id*='social-proofing']",
                ".social-proofing-widget-text"
            ]
            
            bought_elem = None
            for selector in bought_selectors:
                bought_elem = soup.select_one(selector)
                if bought_elem:
                    break
            
            # 텍스트에서 직접 찾기
            if not bought_elem:
                bought_elem = soup.find(string=re.compile(r'bought in past month', re.IGNORECASE))
            
            if bought_elem:
                bought_text = bought_elem if isinstance(bought_elem, str) else bought_elem.get_text(strip=True)
                print(f"[DEBUG] Found bought text: {bought_text}")
                
                # "10K+ bought" 또는 "500+ bought" 형식
                match = re.search(r'([\d.]+)([KM])?\+?\s*bought', bought_text, re.IGNORECASE)
                if match:
                    number = float(match.group(1))
                    multiplier = match.group(2)
                    if multiplier == 'K':
                        number *= 1000
                    elif multiplier == 'M':
                        number *= 1000000
                    metadata["bought_last_month"] = int(number)
                    print(f"[DEBUG] Extracted bought_last_month: {metadata['bought_last_month']}")
                else:
                    # 숫자만 있는 경우
                    match = re.search(r'([\d,]+)', bought_text)
                    if match:
                        metadata["bought_last_month"] = int(match.group(1).replace(",", ""))
                        print(f"[DEBUG] Extracted bought_last_month: {metadata['bought_last_month']}")
            else:
                print("[DEBUG] No 'bought in past month' data found")
            
        except Exception as e:
            print(f"[DEBUG] Metadata extraction failed: {e}")
        
        return metadata
    
    def run(self):
        """메인 실행 함수"""
        print("=" * 60)
        print("K-Beauty Amazon Review Scraper")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print("\n💡 Tip: Ctrl+C를 눌러 언제든지 중단할 수 있습니다. 지금까지 수집한 데이터는 자동 저장됩니다.\n")
        
        try:
            self._init_driver()
            
            # 1. 제품 검색
            product_urls = self.search_products()
            
            if not product_urls:
                print("[ERROR] No products found")
                return
            
            # 2. 각 제품 리뷰 수집
            for idx, url in enumerate(product_urls, 1):
                print(f"\n{'='*40}")
                print(f"Processing product {idx}/{len(product_urls)}")
                print(f"{'='*40}")
                
                reviews = self.scrape_product_reviews(url)
                self.reviews_data.extend(reviews)
                
                # 제품 간 딜레이
                if idx < len(product_urls):
                    self._random_delay(3, 6)
            
            # 3. 결과 저장
            self._save_results()
            
        except KeyboardInterrupt:
            print("\n\n" + "="*60)
            print("⚠️  사용자가 중단했습니다 (Ctrl+C)")
            print("="*60)
            print(f"[INFO] 지금까지 수집한 데이터를 저장합니다...")
            print(f"[INFO] 수집된 제품: {len(self.products_data)}개")
            print(f"[INFO] 수집된 리뷰: {len(self.reviews_data)}개")
            self._save_results()
            
        except Exception as e:
            print(f"\n[FATAL] Scraper crashed: {e}")
            print(f"[INFO] 지금까지 수집한 데이터를 저장합니다...")
            if self.reviews_data or self.products_data:
                self._save_results()
                
        finally:
            self._close_driver()
    
    def _save_results(self):
        """결과를 CSV로 저장"""
        import csv
        import os
        
        # results 폴더 생성
        os.makedirs("results", exist_ok=True)
        
        # 리뷰 CSV 저장
        reviews_file = "results/amazon_reviews.csv"
        
        if self.reviews_data:
            cleaned_data = []
            for review in self.reviews_data:
                cleaned_review = {
                    "product_name": review.get("product_name", "").replace("\n", " ").replace("\r", " "),
                    "review_text": review.get("review_text", "").replace("\n", " ").replace("\r", " "),
                    "rating": review.get("rating", 0),
                    "date": review.get("date", ""),
                    "helpful_count": review.get("helpful_count", 0),
                    "verified_purchase": review.get("verified_purchase", False),
                    "source": review.get("source", "")
                }
                cleaned_data.append(cleaned_review)
            
            with open(reviews_file, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["product_name", "review_text", "rating", "date", "helpful_count", "verified_purchase", "source"])
                writer.writeheader()
                writer.writerows(cleaned_data)
            
            print(f"\n[SUCCESS] Saved {len(self.reviews_data)} reviews to {reviews_file}")
        
        # 제품 메타데이터 CSV 저장
        products_file = "results/amazon_products.csv"
        
        if self.products_data:
            with open(products_file, "w", encoding="utf-8-sig", newline="") as f:
                fieldnames = ["product_name", "brand", "price", "avg_rating", "review_count", "bought_last_month", "url"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.products_data)
            
            print(f"[SUCCESS] Saved {len(self.products_data)} products to {products_file}")


if __name__ == "__main__":
    scraper = AmazonKBeautyScraper()
    scraper.run()
