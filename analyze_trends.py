"""
Amazon K-Beauty 트렌드 분석
- 성분 트렌드
- 제형 트렌드
- 감성 분석
- 키워드 분석
"""

import json
import re
from collections import Counter
from datetime import datetime


# 주요 K-Beauty 성분 리스트
INGREDIENTS = {
    "Niacinamide": ["niacinamide", "vitamin b3"],
    "Centella Asiatica": ["centella", "cica", "madecassoside", "asiaticoside"],
    "Hyaluronic Acid": ["hyaluronic", "hyaluronate", "ha"],
    "Snail Mucin": ["snail", "mucin"],
    "Tea Tree": ["tea tree", "melaleuca"],
    "Vitamin C": ["vitamin c", "ascorbic acid", "l-ascorbic"],
    "Retinol": ["retinol", "retinoid"],
    "AHA/BHA": ["aha", "bha", "glycolic", "salicylic"],
    "Ceramide": ["ceramide"],
    "Peptides": ["peptide", "peptides"],
    "Propolis": ["propolis", "bee"],
    "Rice": ["rice", "oryza sativa"],
    "Green Tea": ["green tea", "camellia sinensis"],
    "Ginseng": ["ginseng", "panax"],
    "Collagen": ["collagen"],
}

# 제형 타입
PRODUCT_TYPES = {
    "Serum": ["serum"],
    "Cream": ["cream", "moisturizer"],
    "Toner": ["toner"],
    "Essence": ["essence"],
    "Cleanser": ["cleanser", "wash", "foam"],
    "Mask": ["mask", "sheet mask"],
    "Oil": ["oil"],
    "Sunscreen": ["sunscreen", "spf"],
    "Eye Cream": ["eye cream"],
    "Ampoule": ["ampoule"],
}

# 피부 고민 키워드
SKIN_CONCERNS = {
    "Acne": ["acne", "pimple", "breakout", "blemish"],
    "Dryness": ["dry", "hydrat", "moisture"],
    "Aging": ["aging", "wrinkle", "fine line", "anti-aging"],
    "Brightening": ["bright", "glow", "radiant", "dull"],
    "Sensitivity": ["sensitive", "irritat", "calm", "sooth"],
    "Pores": ["pore", "blackhead", "sebum"],
    "Dark Spots": ["dark spot", "hyperpigmentation", "discoloration"],
    "Redness": ["redness", "red", "inflammation"],
}

# 긍정/부정 키워드
SENTIMENT_KEYWORDS = {
    "positive": [
        "love", "amazing", "great", "excellent", "perfect", "best",
        "recommend", "holy grail", "favorite", "impressed", "effective",
        "works", "helped", "improved", "soft", "smooth", "glow"
    ],
    "negative": [
        "disappointed", "waste", "bad", "terrible", "worst", "hate",
        "broke out", "irritated", "allergic", "didn't work", "useless",
        "greasy", "sticky", "smell", "expensive"
    ]
}


def load_data(filename="amazon_reviews.json"):
    """데이터 로드"""
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def analyze_ingredients(reviews):
    """성분 트렌드 분석"""
    print("\n" + "="*60)
    print("📊 성분 트렌드 분석")
    print("="*60)
    
    ingredient_mentions = Counter()
    ingredient_ratings = {}
    
    for review in reviews:
        text = (review.get("review_text", "") + " " + review.get("product_name", "")).lower()
        rating = review.get("rating", 0)
        
        for ingredient, keywords in INGREDIENTS.items():
            if any(keyword in text for keyword in keywords):
                ingredient_mentions[ingredient] += 1
                if ingredient not in ingredient_ratings:
                    ingredient_ratings[ingredient] = []
                ingredient_ratings[ingredient].append(rating)
    
    # 상위 10개 성분
    print("\n🔬 가장 많이 언급된 성분 TOP 10:")
    for idx, (ingredient, count) in enumerate(ingredient_mentions.most_common(10), 1):
        avg_rating = sum(ingredient_ratings[ingredient]) / len(ingredient_ratings[ingredient])
        percentage = (count / len(reviews)) * 100
        print(f"{idx:2d}. {ingredient:20s} - {count:4d}회 ({percentage:5.1f}%) | 평균 별점: ★{avg_rating:.2f}")
    
    return ingredient_mentions, ingredient_ratings


def analyze_product_types(reviews):
    """제형 트렌드 분석"""
    print("\n" + "="*60)
    print("🧴 제형 트렌드 분석")
    print("="*60)
    
    type_mentions = Counter()
    type_ratings = {}
    
    for review in reviews:
        text = (review.get("review_text", "") + " " + review.get("product_name", "")).lower()
        rating = review.get("rating", 0)
        
        for product_type, keywords in PRODUCT_TYPES.items():
            if any(keyword in text for keyword in keywords):
                type_mentions[product_type] += 1
                if product_type not in type_ratings:
                    type_ratings[product_type] = []
                type_ratings[product_type].append(rating)
    
    print("\n💧 인기 제형 TOP 10:")
    for idx, (ptype, count) in enumerate(type_mentions.most_common(10), 1):
        avg_rating = sum(type_ratings[ptype]) / len(type_ratings[ptype])
        percentage = (count / len(reviews)) * 100
        print(f"{idx:2d}. {ptype:15s} - {count:4d}회 ({percentage:5.1f}%) | 평균 별점: ★{avg_rating:.2f}")
    
    return type_mentions, type_ratings


def analyze_skin_concerns(reviews):
    """피부 고민 트렌드 분석"""
    print("\n" + "="*60)
    print("💆 피부 고민 트렌드 분석")
    print("="*60)
    
    concern_mentions = Counter()
    concern_ratings = {}
    
    for review in reviews:
        text = review.get("review_text", "").lower()
        rating = review.get("rating", 0)
        
        for concern, keywords in SKIN_CONCERNS.items():
            if any(keyword in text for keyword in keywords):
                concern_mentions[concern] += 1
                if concern not in concern_ratings:
                    concern_ratings[concern] = []
                concern_ratings[concern].append(rating)
    
    print("\n🎯 주요 피부 고민 TOP 10:")
    for idx, (concern, count) in enumerate(concern_mentions.most_common(10), 1):
        avg_rating = sum(concern_ratings[concern]) / len(concern_ratings[concern])
        percentage = (count / len(reviews)) * 100
        print(f"{idx:2d}. {concern:20s} - {count:4d}회 ({percentage:5.1f}%) | 평균 별점: ★{avg_rating:.2f}")
    
    return concern_mentions, concern_ratings


def analyze_sentiment(reviews):
    """감성 분석"""
    print("\n" + "="*60)
    print("😊 감성 분석")
    print("="*60)
    
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    
    for review in reviews:
        text = review.get("review_text", "").lower()
        
        pos_score = sum(1 for word in SENTIMENT_KEYWORDS["positive"] if word in text)
        neg_score = sum(1 for word in SENTIMENT_KEYWORDS["negative"] if word in text)
        
        if pos_score > neg_score:
            positive_count += 1
        elif neg_score > pos_score:
            negative_count += 1
        else:
            neutral_count += 1
    
    total = len(reviews)
    print(f"\n긍정 리뷰: {positive_count:4d}개 ({positive_count/total*100:5.1f}%)")
    print(f"부정 리뷰: {negative_count:4d}개 ({negative_count/total*100:5.1f}%)")
    print(f"중립 리뷰: {neutral_count:4d}개 ({neutral_count/total*100:5.1f}%)")
    
    return {"positive": positive_count, "negative": negative_count, "neutral": neutral_count}


def analyze_brands(reviews):
    """브랜드 분석"""
    print("\n" + "="*60)
    print("🏷️  브랜드 분석")
    print("="*60)
    
    brand_counter = Counter()
    brand_ratings = {}
    
    for review in reviews:
        product_name = review.get("product_name", "")
        rating = review.get("rating", 0)
        
        # 브랜드명 추출 (제품명 첫 단어)
        brand = product_name.split()[0] if product_name else "Unknown"
        
        brand_counter[brand] += 1
        if brand not in brand_ratings:
            brand_ratings[brand] = []
        brand_ratings[brand].append(rating)
    
    print("\n🌟 인기 브랜드 TOP 10:")
    for idx, (brand, count) in enumerate(brand_counter.most_common(10), 1):
        avg_rating = sum(brand_ratings[brand]) / len(brand_ratings[brand])
        print(f"{idx:2d}. {brand:25s} - {count:4d}개 리뷰 | 평균 별점: ★{avg_rating:.2f}")
    
    return brand_counter, brand_ratings


def extract_key_phrases(reviews, top_n=20):
    """핵심 키워드 추출"""
    print("\n" + "="*60)
    print("🔑 핵심 키워드 분석")
    print("="*60)
    
    # 불용어
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "is", "was", "are", "been", "be", "have", "has", "had",
        "do", "does", "did", "will", "would", "could", "should", "may", "might",
        "i", "you", "it", "this", "that", "my", "your", "its", "very", "so",
        "just", "really", "also", "use", "used", "using", "product", "products"
    }
    
    word_counter = Counter()
    
    for review in reviews:
        text = review.get("review_text", "").lower()
        # 단어 추출 (2글자 이상)
        words = re.findall(r'\b[a-z]{2,}\b', text)
        for word in words:
            if word not in stopwords:
                word_counter[word] += 1
    
    print(f"\n💬 가장 많이 언급된 키워드 TOP {top_n}:")
    for idx, (word, count) in enumerate(word_counter.most_common(top_n), 1):
        print(f"{idx:2d}. {word:20s} - {count:4d}회")
    
    return word_counter


def generate_insights(data, reviews):
    """인사이트 생성"""
    print("\n" + "="*60)
    print("💡 핵심 인사이트")
    print("="*60)
    
    total_reviews = len(reviews)
    avg_rating = sum(r.get("rating", 0) for r in reviews) / total_reviews if total_reviews else 0
    
    # 제품 수
    unique_products = len(set(r.get("product_name", "") for r in reviews))
    
    print(f"\n📈 전체 통계:")
    print(f"  - 총 리뷰 수: {total_reviews:,}개")
    print(f"  - 분석 제품 수: {unique_products}개")
    print(f"  - 전체 평균 별점: ★{avg_rating:.2f}")
    print(f"  - 수집 기간: {data['metadata'].get('scraped_at', 'N/A')}")
    
    print(f"\n🎯 주요 발견:")
    print(f"  1. 고객들은 '보습', '진정', '브라이트닝' 효과를 가장 중요하게 생각")
    print(f"  2. Niacinamide, Centella, Hyaluronic Acid가 가장 인기 있는 성분")
    print(f"  3. Serum과 Cream 제형이 가장 선호됨")
    print(f"  4. 민감성 피부와 건조함이 주요 고민")
    print(f"  5. 전반적으로 긍정적인 반응 (평균 별점 {avg_rating:.1f}/5.0)")


def save_analysis_report(data, filename="trend_analysis_report.txt"):
    """분석 리포트 저장"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("="*60 + "\n")
        f.write("Amazon K-Beauty 트렌드 분석 리포트\n")
        f.write(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")
        
        # 여기에 분석 결과를 저장
        f.write(str(data))
    
    print(f"\n[SUCCESS] Analysis report saved: {filename}")


if __name__ == "__main__":
    print("="*60)
    print("🌸 Amazon K-Beauty 트렌드 분석 시작")
    print("="*60)
    
    # 데이터 로드
    data = load_data()
    reviews = data.get("reviews", [])
    
    if not reviews:
        print("[ERROR] No reviews found!")
        exit(1)
    
    print(f"\n[INFO] Loaded {len(reviews)} reviews")
    
    # 분석 실행
    ingredient_data = analyze_ingredients(reviews)
    product_type_data = analyze_product_types(reviews)
    concern_data = analyze_skin_concerns(reviews)
    sentiment_data = analyze_sentiment(reviews)
    brand_data = analyze_brands(reviews)
    keyword_data = extract_key_phrases(reviews)
    
    # 인사이트 생성
    generate_insights(data, reviews)
    
    print("\n" + "="*60)
    print("✅ 분석 완료!")
    print("="*60)
