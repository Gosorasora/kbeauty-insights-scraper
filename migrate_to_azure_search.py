"""
Azure AI Search Migration Tool v2.0
===================================

CSV 리뷰 데이터를 Azure AI Search Vector 인덱스로 마이그레이션

주요 기능:
- CSV 데이터 자동 로드 및 정제
- Azure OpenAI로 임베딩 생성 (text-embedding-ada-002)
- Vector Search 인덱스 생성
- 배치 업로드로 성능 최적화
- 업로드 진행률 표시

사용법:
1. 환경 변수 설정 (.env 파일)
2. CSV 파일을 results/ 폴더에 배치
3. python migrate_to_azure_search.py 실행

지원 파일: amazon_reviews.csv, kbeauty_reviews.csv
"""

import os
import pandas as pd
import json
from typing import List, Dict, Any
from datetime import datetime

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticSearch,
    SemanticField,
    SemanticPrioritizedFields
)
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from tqdm import tqdm
import time

class AzureSearchMigrator:
    """Azure AI Search 마이그레이션 클래스"""
    
    def __init__(self):
        """초기화"""
        
        # 환경 변수 확인
        self.search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.search_key = os.getenv("AZURE_SEARCH_API_KEY")
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.index_name = os.getenv("SEARCH_INDEX_NAME", "amor-party-reviews")
        
        if not all([self.search_endpoint, self.search_key, self.openai_endpoint, self.openai_key]):
            raise ValueError("필수 환경 변수가 설정되지 않았습니다.")
        
        # 클라이언트 초기화
        self.credential = AzureKeyCredential(self.search_key)
        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=self.credential
        )
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=self.credential
        )
        
        # OpenAI 클라이언트
        self.openai_client = AzureOpenAI(
            api_key=self.openai_key,
            api_version="2024-02-15-preview",
            azure_endpoint=self.openai_endpoint
        )
        
        print("✓ Azure AI Search 마이그레이터 초기화 완료")
    
    def create_search_index(self) -> None:
        """검색 인덱스 생성"""
        
        print(f"🔧 검색 인덱스 생성 중: {self.index_name}")
        
        # Vector Search 설정
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="myHnsw",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="myHnswProfile",
                    algorithm_configuration_name="myHnsw"
                )
            ]
        )
        
        # Semantic Search 설정
        semantic_config = SemanticConfiguration(
            name="my-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="review_text")],
                keywords_fields=[SemanticField(field_name="product_name")]
            )
        )
        
        semantic_search = SemanticSearch(configurations=[semantic_config])
        
        # 필드 정의
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="product_name", type=SearchFieldDataType.String),
            SearchableField(name="review_text", type=SearchFieldDataType.String),
            SimpleField(name="rating", type=SearchFieldDataType.Double),
            SimpleField(name="date", type=SearchFieldDataType.String),
            SimpleField(name="helpful_count", type=SearchFieldDataType.Int32),
            SimpleField(name="verified_purchase", type=SearchFieldDataType.Boolean),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="myHnswProfile"
            )
        ]
        
        # 인덱스 생성
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )
        
        try:
            result = self.index_client.create_or_update_index(index)
            print(f"✓ 인덱스 생성 완료: {result.name}")
        except Exception as e:
            print(f"❌ 인덱스 생성 실패: {e}")
            raise
    
    def get_embedding(self, text: str) -> List[float]:
        """텍스트 임베딩 생성"""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ 임베딩 생성 실패: {e}")
            return [0.0] * 1536  # 기본값
    
    def load_csv_data(self, csv_path: str) -> pd.DataFrame:
        """CSV 데이터 로드"""
        
        print(f"📂 CSV 데이터 로드 중: {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            print(f"✓ 데이터 로드 완료: {len(df):,}개 리뷰")
            
            # 필수 컬럼 확인
            required_columns = ['product_name', 'review_text', 'rating', 'date']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"필수 컬럼 누락: {missing_columns}")
            
            # 데이터 정제
            df = df.dropna(subset=['review_text'])
            df['helpful_count'] = df.get('helpful_count', 0).fillna(0).astype(int)
            df['verified_purchase'] = df.get('verified_purchase', True).fillna(True).astype(bool)
            
            print(f"✓ 데이터 정제 완료: {len(df):,}개 리뷰")
            return df
            
        except Exception as e:
            print(f"❌ CSV 로드 실패: {e}")
            raise
    
    def prepare_documents(self, df: pd.DataFrame, batch_size: int = 100) -> List[List[Dict[str, Any]]]:
        """문서 준비 (배치 단위)"""
        
        print(f"📝 문서 준비 중 (배치 크기: {batch_size})")
        
        documents = []
        batches = []
        
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="임베딩 생성"):
            # 리뷰 텍스트 임베딩 생성
            review_text = str(row['review_text'])[:2000]  # 길이 제한
            embedding = self.get_embedding(review_text)
            
            # 문서 생성
            doc = {
                "id": f"review_{idx}",
                "product_name": str(row['product_name'])[:500],
                "review_text": review_text,
                "rating": float(row['rating']),
                "date": str(row['date']),
                "helpful_count": int(row['helpful_count']),
                "verified_purchase": bool(row['verified_purchase']),
                "embedding": embedding
            }
            
            documents.append(doc)
            
            # 배치 크기에 도달하면 배치 생성
            if len(documents) >= batch_size:
                batches.append(documents.copy())
                documents.clear()
            
            # API 속도 제한 고려
            if idx % 10 == 0:
                time.sleep(0.1)
        
        # 마지막 배치 추가
        if documents:
            batches.append(documents)
        
        print(f"✓ 문서 준비 완료: {len(batches)}개 배치")
        return batches
    
    def upload_documents(self, document_batches: List[List[Dict[str, Any]]]) -> None:
        """문서 업로드"""
        
        print(f"⬆️ 문서 업로드 시작: {len(document_batches)}개 배치")
        
        total_uploaded = 0
        
        for i, batch in enumerate(tqdm(document_batches, desc="배치 업로드")):
            try:
                result = self.search_client.upload_documents(documents=batch)
                
                # 성공/실패 카운트
                succeeded = sum(1 for r in result if r.succeeded)
                failed = len(batch) - succeeded
                
                total_uploaded += succeeded
                
                if failed > 0:
                    print(f"⚠️ 배치 {i+1}: {succeeded}개 성공, {failed}개 실패")
                
                # API 속도 제한 고려
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ 배치 {i+1} 업로드 실패: {e}")
                continue
        
        print(f"✓ 업로드 완료: {total_uploaded:,}개 문서")
    
    def verify_index(self) -> None:
        """인덱스 검증"""
        
        print("🔍 인덱스 검증 중...")
        
        try:
            # 문서 수 확인
            stats = self.search_client.get_search_index_statistics()
            print(f"✓ 인덱스 통계:")
            print(f"  - 문서 수: {stats.document_count:,}개")
            print(f"  - 저장 크기: {stats.storage_size:,} bytes")
            
            # 샘플 검색 테스트
            results = self.search_client.search(
                search_text="moisturizer",
                top=3,
                select=["product_name", "review_text", "rating"]
            )
            
            print(f"✓ 샘플 검색 결과:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['product_name'][:50]}... (★{result['rating']})")
            
        except Exception as e:
            print(f"❌ 인덱스 검증 실패: {e}")
    
    def migrate(self, csv_path: str, batch_size: int = 50) -> None:
        """전체 마이그레이션 실행"""
        
        print("🚀 Azure AI Search 마이그레이션 시작")
        print("=" * 50)
        
        try:
            # 1. 인덱스 생성
            self.create_search_index()
            
            # 2. CSV 데이터 로드
            df = self.load_csv_data(csv_path)
            
            # 3. 문서 준비
            document_batches = self.prepare_documents(df, batch_size)
            
            # 4. 문서 업로드
            self.upload_documents(document_batches)
            
            # 5. 인덱스 검증
            self.verify_index()
            
            print("=" * 50)
            print("✅ 마이그레이션 완료!")
            
        except Exception as e:
            print(f"❌ 마이그레이션 실패: {e}")
            raise

def main():
    """메인 실행 함수"""
    
    # 환경 변수 확인
    required_vars = [
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_API_KEY", 
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ 필수 환경 변수가 설정되지 않았습니다:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\n.env 파일을 생성하고 Azure 서비스 정보를 입력하세요.")
        return
    
    # CSV 파일 경로 확인
    csv_files = [
        "results/amazon_reviews.csv",
        "results/kbeauty_reviews.csv", 
        "amazon_reviews.csv",
        "kbeauty_reviews.csv"
    ]
    
    csv_path = None
    for path in csv_files:
        if os.path.exists(path):
            csv_path = path
            break
    
    if not csv_path:
        print("❌ CSV 파일을 찾을 수 없습니다.")
        print("다음 위치 중 하나에 CSV 파일을 배치하세요:")
        for path in csv_files:
            print(f"  - {path}")
        return
    
    # 마이그레이션 실행
    try:
        migrator = AzureSearchMigrator()
        migrator.migrate(csv_path, batch_size=50)
        
    except Exception as e:
        print(f"❌ 실행 실패: {e}")

if __name__ == "__main__":
    main()