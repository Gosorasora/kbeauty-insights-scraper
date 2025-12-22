# K-Beauty 리테일 인사이트 분석

Amazon K-Beauty 제품 리뷰 데이터를 수집하고 분석하는 프로젝트입니다.

## 🚀 빠른 시작

### 1. 환경 설정
```bash
pip install -r requirements.txt
```

### 2. Chrome 디버그 모드 실행
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_debug_profile
```

### 3. Amazon 로그인 후 크롤러 실행
```bash
python3 amazon_scraper.py
```

## 📊 수집 데이터

- **리뷰 데이터**: `results/amazon_reviews.csv`
- **제품 데이터**: `results/amazon_products.csv`

## 📈 분석

```bash
python3 analyze_trends.py
```

## 📁 프로젝트 구조

```
.
├── amazon_scraper.py      # 메인 크롤러
├── analyze_trends.py      # 트렌드 분석
├── requirements.txt       # 필요 라이브러리
├── results/              # 크롤링 결과 (gitignore)
└── docs/                 # 문서 (gitignore)
```

## 💡 주요 기능

- ✅ Amazon 제품 검색 및 리뷰 수집
- ✅ 별점, 유용함 투표, 검증된 구매 정보 수집
- ✅ 성분/제형 트렌드 분석
- ✅ Ctrl+C 중단 시 자동 저장

## 📝 상세 문서

자세한 내용은 `docs/` 폴더를 참고하세요.

---

**프로젝트**: 아모레퍼시픽 K-Beauty 인사이트 분석  
**작성일**: 2025.12
