"""
K-Beauty RAG AI Agent - Flask Web Application
==============================================

Azure App Service에서 실행되는 K-Beauty 추천 AI 웹 애플리케이션

주요 기능:
- Azure OpenAI 기반 자연어 처리
- Azure AI Search 기반 Vector 검색
- Redis 캐싱으로 성능 최적화
- Health Check 및 모니터링

아키텍처: v2 Clean Architecture
성능 목표: 응답시간 2초 이내, 캐시 히트율 60%+
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

import redis
from flask import Flask, request, jsonify, render_template_string
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 환경 변수 로드
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
REDIS_CONNECTION_STRING = os.getenv("REDIS_CONNECTION_STRING")

# 애플리케이션 설정
SEARCH_INDEX_NAME = os.getenv("SEARCH_INDEX_NAME", "amor-party-reviews")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
ENABLE_RESPONSE_CACHE = os.getenv("ENABLE_RESPONSE_CACHE", "true").lower() == "true"
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))

# 글로벌 클라이언트 초기화
redis_client = None
openai_client = None
search_client = None

def init_clients():
    """클라이언트 초기화"""
    global redis_client, openai_client, search_client
    
    try:
        # Redis 클라이언트
        if REDIS_CONNECTION_STRING and ENABLE_RESPONSE_CACHE:
            redis_client = redis.from_url(REDIS_CONNECTION_STRING, decode_responses=True)
            logger.info("Redis 클라이언트 초기화 완료")
        
        # Azure OpenAI 클라이언트
        openai_client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        logger.info("Azure OpenAI 클라이언트 초기화 완료")
        
        # Azure Search 클라이언트
        search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=SEARCH_INDEX_NAME,
            credential=AzureKeyCredential(AZURE_SEARCH_API_KEY)
        )
        logger.info("Azure Search 클라이언트 초기화 완료")
            
    except Exception as e:
        logger.error(f"클라이언트 초기화 실패: {e}")
        raise

def get_cache_key(query: str, n_results: int = 10) -> str:
    """캐시 키 생성"""
    content = f"{query}:{n_results}"
    return f"kbeauty:response:{hashlib.md5(content.encode()).hexdigest()}"

def get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    """캐시된 응답 조회"""
    if not redis_client or not ENABLE_RESPONSE_CACHE:
        return None
    
    try:
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"캐시 히트: {cache_key}")
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"캐시 조회 실패: {e}")
    
    return None

def set_cached_response(cache_key: str, response: Dict[str, Any]) -> None:
    """응답 캐싱"""
    if not redis_client or not ENABLE_RESPONSE_CACHE:
        return
    
    try:
        redis_client.setex(
            cache_key,
            CACHE_TTL_SECONDS,
            json.dumps(response, ensure_ascii=False)
        )
        logger.info(f"캐시 저장: {cache_key}")
    except Exception as e:
        logger.warning(f"캐시 저장 실패: {e}")

def get_embedding(text: str) -> list:
    """텍스트 임베딩 생성"""
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def search_reviews(query: str, n_results: int = 10) -> Dict[str, Any]:
    """Azure AI Search에서 관련 리뷰 검색"""
    
    # 쿼리 임베딩
    query_embedding = get_embedding(query)
    
    # Vector 검색
    search_results = search_client.search(
        search_text=None,
        vector_queries=[{
            "vector": query_embedding,
            "k_nearest_neighbors": n_results,
            "fields": "embedding"
        }],
        select=["product_name", "review_text", "rating", "date", "helpful_count", "verified_purchase"],
        top=n_results
    )
    
    results = []
    for result in search_results:
        results.append({
            "product_name": result.get("product_name", ""),
            "review_text": result.get("review_text", ""),
            "rating": result.get("rating", 0),
            "date": result.get("date", ""),
            "helpful_count": result.get("helpful_count", 0),
            "verified_purchase": result.get("verified_purchase", False),
            "score": result.get("@search.score", 0)
        })
    
    return {"results": results}

def format_context(search_results: Dict[str, Any]) -> str:
    """검색 결과를 컨텍스트로 포맷팅"""
    
    context_parts = []
    
    for i, result in enumerate(search_results["results"], 1):
        context_parts.append(
            f"[리뷰 {i}]\n"
            f"제품: {result['product_name']}\n"
            f"별점: ★{result['rating']}\n"
            f"날짜: {result['date']}\n"
            f"유용함: {result['helpful_count']}명\n"
            f"검증된 구매: {'예' if result['verified_purchase'] else '아니오'}\n"
            f"내용: {result['review_text']}\n"
        )
    
    return "\n".join(context_parts)

def generate_answer(query: str, context: str) -> str:
    """Azure OpenAI로 답변 생성"""
    
    system_prompt = """당신은 K-Beauty 전문가 AI 에이전트입니다.
Amazon 리뷰 데이터를 분석하여 글로벌 고객들이 K-Beauty 제품에 기대하는 포인트를 알려줍니다.

답변 시 다음을 포함하세요:
1. 주요 트렌드 및 인사이트
2. 구체적인 제품 예시 (리뷰에서 언급된 것)
3. 고객 반응 (별점, 유용함 투표)
4. 추천 사항 또는 시사점

답변은 한국어로 작성하되, 전문적이고 명확하게 작성하세요."""

    user_prompt = f"""다음 리뷰 데이터를 바탕으로 질문에 답변해주세요.

<리뷰 데이터>
{context}

<질문>
{query}

<답변>"""

    response = openai_client.chat.completions.create(
        model="gpt-35-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=1500
    )
    
    return response.choices[0].message.content

@app.route('/health')
def health_check():
    """Health Check 엔드포인트"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "v2.0",
        "services": {}
    }
    
    # Redis 상태 확인
    try:
        if redis_client:
            redis_client.ping()
            health_status["services"]["redis"] = "healthy"
        else:
            health_status["services"]["redis"] = "disabled"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Azure OpenAI 상태 확인
    try:
        # 간단한 임베딩 테스트
        test_response = openai_client.embeddings.create(
            input="health check",
            model="text-embedding-ada-002"
        )
        if test_response.data:
            health_status["services"]["openai"] = "healthy"
        else:
            health_status["services"]["openai"] = "unhealthy"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["services"]["openai"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Azure Search 상태 확인
    try:
        # 인덱스 통계 조회
        stats = search_client.get_search_index_statistics()
        if stats:
            health_status["services"]["search"] = "healthy"
            health_status["services"]["search_documents"] = stats.document_count
        else:
            health_status["services"]["search"] = "unhealthy"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["services"]["search"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # HTTP 상태 코드 결정
    if health_status["status"] == "healthy":
        return jsonify(health_status), 200
    elif health_status["status"] == "degraded":
        return jsonify(health_status), 200  # 부분적 장애는 200
    else:
        return jsonify(health_status), 503  # 서비스 불가

@app.route('/')
def index():
    """메인 페이지"""
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>K-Beauty RAG AI Agent</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .question-form { margin: 20px 0; }
            .question-input { width: 100%; padding: 10px; font-size: 16px; }
            .submit-btn { padding: 10px 20px; font-size: 16px; background: #007cba; color: white; border: none; cursor: pointer; }
            .result { margin: 20px 0; padding: 20px; background: #f5f5f5; border-radius: 5px; }
            .examples { margin: 20px 0; }
            .example { margin: 5px 0; color: #666; cursor: pointer; }
            .example:hover { color: #007cba; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌸 K-Beauty RAG AI Agent</h1>
            <p>Amazon 리뷰 데이터를 기반으로 K-Beauty 트렌드와 인사이트를 제공합니다.</p>
            
            <div class="question-form">
                <form method="POST" action="/ask">
                    <input type="text" name="question" class="question-input" 
                           placeholder="질문을 입력하세요 (예: 요즘 인기 있는 진정 토너는?)" required>
                    <br><br>
                    <button type="submit" class="submit-btn">질문하기</button>
                </form>
            </div>
            
            <div class="examples">
                <h3>💡 예시 질문:</h3>
                <div class="example" onclick="setQuestion(this)">요즘 미국에서 인기 있는 진정 토너는 무엇인가요?</div>
                <div class="example" onclick="setQuestion(this)">Snail Mucin 제품에 대한 고객 반응은 어떤가요?</div>
                <div class="example" onclick="setQuestion(this)">건조한 피부에 좋은 K-Beauty 제품을 추천해주세요.</div>
                <div class="example" onclick="setQuestion(this)">Niacinamide 성분이 들어간 제품 중 평점이 높은 것은?</div>
                <div class="example" onclick="setQuestion(this)">40대 이상 고객들이 선호하는 제품은?</div>
            </div>
            
            <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
                <p>🚀 <strong>v2 Architecture:</strong> Azure AI Search + Redis Cache</p>
                <p>⚡ <strong>Performance:</strong> 5-10ms (cached) / 20-50ms (search)</p>
                <p>📊 <strong>Health Check:</strong> <a href="/health">/health</a></p>
            </div>
        </div>
        
        <script>
            function setQuestion(element) {
                document.querySelector('.question-input').value = element.textContent;
            }
        </script>
    </body>
    </html>
    """
    
    return render_template_string(html_template)

@app.route('/ask', methods=['POST'])
def ask_question():
    """질문 처리 API"""
    
    try:
        # 요청 데이터 추출
        question = request.form.get('question') or request.json.get('question')
        n_results = int(request.form.get('n_results', 10))
        
        if not question:
            return jsonify({"error": "질문이 필요합니다."}), 400
        
        # 캐시 확인
        cache_key = get_cache_key(question, n_results)
        cached_response = get_cached_response(cache_key)
        
        if cached_response:
            cached_response["cached"] = True
            cached_response["cache_key"] = cache_key
            return jsonify(cached_response)
        
        # 검색 및 답변 생성
        start_time = datetime.utcnow()
        
        # 1. 관련 리뷰 검색
        search_results = search_reviews(question, n_results)
        
        # 2. 컨텍스트 생성
        context = format_context(search_results)
        
        # 3. 답변 생성
        answer = generate_answer(question, context)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # 응답 구성
        response = {
            "question": question,
            "answer": answer,
            "sources": search_results["results"][:5],  # 상위 5개만
            "processing_time_seconds": processing_time,
            "cached": False,
            "timestamp": end_time.isoformat(),
            "n_results": n_results
        }
        
        # 캐시 저장
        set_cached_response(cache_key, response)
        
        # HTML 요청인 경우 결과 페이지 반환
        if request.content_type != 'application/json':
            html_result = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>K-Beauty RAG AI - 답변</title>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .container {{ max-width: 800px; margin: 0 auto; }}
                    .question {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                    .answer {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0; line-height: 1.6; }}
                    .sources {{ margin: 20px 0; }}
                    .source {{ margin: 10px 0; padding: 10px; background: #fff; border-left: 3px solid #007cba; }}
                    .meta {{ color: #666; font-size: 14px; margin: 20px 0; }}
                    .back-btn {{ padding: 10px 20px; background: #007cba; color: white; text-decoration: none; border-radius: 3px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🌸 K-Beauty RAG AI Agent</h1>
                    
                    <div class="question">
                        <strong>질문:</strong> {question}
                    </div>
                    
                    <div class="answer">
                        <strong>답변:</strong><br><br>
                        {answer.replace(chr(10), '<br>')}
                    </div>
                    
                    <div class="sources">
                        <h3>📚 참고한 리뷰 (상위 5개)</h3>
                        {''.join([f'''
                        <div class="source">
                            <strong>{source["product_name"][:60]}...</strong><br>
                            ⭐ {source["rating"]} | 📅 {source["date"]} | 👍 {source["helpful_count"]}명<br>
                            "{source["review_text"][:150]}..."
                        </div>
                        ''' for source in response["sources"]])}
                    </div>
                    
                    <div class="meta">
                        ⏱️ 처리 시간: {processing_time:.2f}초 | 
                        🔍 검색된 리뷰: {n_results}개 | 
                        📅 {end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
                    </div>
                    
                    <a href="/" class="back-btn">← 새 질문하기</a>
                </div>
            </body>
            </html>
            """
            return html_result
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"질문 처리 실패: {e}")
        return jsonify({"error": f"처리 중 오류가 발생했습니다: {str(e)}"}), 500

@app.route('/api/ask', methods=['POST'])
def api_ask_question():
    """API 전용 질문 처리 (JSON만)"""
    
    try:
        data = request.get_json()
        question = data.get('question')
        n_results = data.get('n_results', 10)
        
        if not question:
            return jsonify({"error": "질문이 필요합니다."}), 400
        
        # 캐시 확인
        cache_key = get_cache_key(question, n_results)
        cached_response = get_cached_response(cache_key)
        
        if cached_response:
            cached_response["cached"] = True
            return jsonify(cached_response)
        
        start_time = datetime.utcnow()
        search_results = search_reviews(question, n_results)
        context = format_context(search_results)
        answer = generate_answer(question, context)
        end_time = datetime.utcnow()
        
        response = {
            "question": question,
            "answer": answer,
            "sources": search_results["results"][:5],
            "processing_time_seconds": (end_time - start_time).total_seconds(),
            "cached": False,
            "timestamp": end_time.isoformat(),
            "n_results": n_results
        }
        
        set_cached_response(cache_key, response)
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"API 질문 처리 실패: {e}")
        return jsonify({"error": f"처리 중 오류가 발생했습니다: {str(e)}"}), 500

@app.route('/api/result/<request_id>')
def api_get_result(request_id):
    """큐 처리 결과 조회 API"""
    
    try:
        result_key = f"kbeauty:result:{request_id}"
        
        if not redis_client:
            return jsonify({"error": "Redis 캐시가 비활성화되어 있습니다."}), 503
        
        # Redis에서 결과 조회
        result_data = redis_client.get(result_key)
        
        if not result_data:
            return jsonify({
                "request_id": request_id,
                "status": "not_found",
                "message": "결과를 찾을 수 없습니다. 요청이 처리 중이거나 만료되었을 수 있습니다."
            }), 404
        
        result = json.loads(result_data)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"결과 조회 실패: {e}")
        return jsonify({"error": f"결과 조회 중 오류가 발생했습니다: {str(e)}"}), 500

@app.route('/api/stats')
def api_stats():
    """시스템 통계 API"""
    
    stats = {
        "timestamp": datetime.utcnow().isoformat(),
        "version": "v2.0",
        "features": {
            "redis_cache": ENABLE_RESPONSE_CACHE and redis_client is not None,
            "azure_search": search_client is not None,
            "azure_openai": openai_client is not None
        },
        "config": {
            "cache_ttl_seconds": CACHE_TTL_SECONDS,
            "max_concurrent_requests": MAX_CONCURRENT_REQUESTS,
            "search_index": SEARCH_INDEX_NAME
        }
    }
    
    # Redis 통계
    if redis_client and ENABLE_RESPONSE_CACHE:
        try:
            info = redis_client.info()
            stats["redis"] = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            stats["redis"] = {"error": str(e)}
    
    # Search 통계
    try:
        search_stats = search_client.get_search_index_statistics()
        stats["search"] = {
            "document_count": search_stats.document_count,
            "storage_size_bytes": search_stats.storage_size
        }
    except Exception as e:
        stats["search"] = {"error": str(e)}
    
    return jsonify(stats)

# 애플리케이션 초기화
try:
    init_clients()
    logger.info("K-Beauty RAG AI 웹 애플리케이션 시작")
except Exception as e:
    logger.error(f"애플리케이션 초기화 실패: {e}")
    raise

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8000)