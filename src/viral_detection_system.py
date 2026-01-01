"""
YouTube Training Data Collection System
======================================

AI 모델 학습용 YouTube 데이터 수집 시스템
일별 배치로 실행되어 학습 데이터셋(CSV)을 생성

주요 기능:
- YouTube API 기반 다중 소스 데이터 수집 (거시 트렌드, 키워드 발굴, 채널 성과)
- 피처 엔지니어링 (View Velocity, VPV, Engagement Rate)
- 데이터 정제 및 품질 관리
- CSV 데이터셋 생성 (UTF-8-SIG, SRS 스키마 준수)
- 일별 배치 스케줄링 및 통계 리포팅

사용법:
    from src.viral_detection_system import YouTubeTrainingSystem
    
    config = load_config_from_env()
    system = YouTubeTrainingSystem(config)
    stats = await system.run_daily_collection()
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import json
import os

# 내부 모듈 임포트
from src.collectors.youtube_training_data_collector import YouTubeTrainingDataCollector, VideoTrainingData

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('viral_detection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TrainingSystemConfig:
    """학습 데이터 수집 시스템 설정"""
    # API 키
    youtube_api_keys: List[str]
    
    # 수집 설정
    collection_schedule: str = "daily"  # daily, hourly
    batch_size: int = 100
    max_concurrent_tasks: int = 5
    
    # 데이터 저장 설정
    output_directory: str = "results"
    csv_encoding: str = "utf-8-sig"
    
    # 품질 관리 설정
    min_view_count: int = 1000  # 최소 조회수 필터
    enable_data_validation: bool = True


@dataclass
class CollectionStats:
    """수집 통계"""
    start_time: str
    end_time: str
    total_videos_collected: int
    total_videos_processed: int
    trending_videos_count: int
    csv_file_path: str
    file_size_bytes: int
    api_quota_used: int
    error_count: int


class YouTubeTrainingSystem:
    """YouTube AI 학습용 데이터 수집 시스템"""
    
    def __init__(self, config: TrainingSystemConfig):
        """
        학습 데이터 수집 시스템 초기화
        
        Args:
            config: 시스템 설정
        """
        self.config = config
        self.is_running = False
        self.stats = CollectionStats(
            start_time="",
            end_time="",
            total_videos_collected=0,
            total_videos_processed=0,
            trending_videos_count=0,
            csv_file_path="",
            file_size_bytes=0,
            api_quota_used=0,
            error_count=0
        )
        
        # 컴포넌트 초기화
        self.data_collector = None
        
        # 결과 저장 디렉토리 생성
        os.makedirs(self.config.output_directory, exist_ok=True)
    
    async def run_daily_collection(self, target_date: Optional[str] = None) -> CollectionStats:
        """
        일별 학습 데이터 수집 실행
        
        Args:
            target_date: 수집 대상 날짜 (YYYY-MM-DD), None이면 오늘 날짜
            
        Returns:
            수집 통계
        """
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"🚀 YouTube 학습 데이터 일별 수집 시작 (날짜: {target_date})")
        
        start_time = datetime.now()
        self.stats.start_time = start_time.isoformat()
        self.is_running = True
        
        try:
            # 데이터 수집기 초기화
            await self._initialize_collector()
            
            # 학습 데이터 수집 및 CSV 생성
            csv_path = await self.data_collector.collect_daily_dataset(target_date)
            
            if csv_path:
                # 통계 업데이트
                await self._update_collection_stats(csv_path)
                
                logger.info("✅ 일별 학습 데이터 수집 완료")
                logger.info(f"   - CSV 파일: {self.stats.csv_file_path}")
                logger.info(f"   - 수집된 영상: {self.stats.total_videos_collected}개")
                logger.info(f"   - 처리된 영상: {self.stats.total_videos_processed}개")
                logger.info(f"   - 트렌딩 영상: {self.stats.trending_videos_count}개")
                logger.info(f"   - 파일 크기: {self.stats.file_size_bytes:,} bytes")
                
            else:
                logger.error("❌ 학습 데이터 수집 실패")
                self.stats.error_count += 1
            
        except Exception as e:
            logger.error(f"일별 수집 실행 실패: {e}")
            self.stats.error_count += 1
            
        finally:
            await self._cleanup_collector()
            self.is_running = False
            self.stats.end_time = datetime.now().isoformat()
        
        return self.stats
    
    async def run_batch_collection(self, date_range: List[str]) -> List[CollectionStats]:
        """
        여러 날짜에 대한 배치 수집 실행
        
        Args:
            date_range: 수집할 날짜 목록 (YYYY-MM-DD 형식)
            
        Returns:
            각 날짜별 수집 통계 리스트
        """
        logger.info(f"📅 배치 수집 시작: {len(date_range)}개 날짜")
        
        all_stats = []
        
        for target_date in date_range:
            try:
                logger.info(f"📊 {target_date} 데이터 수집 중...")
                stats = await self.run_daily_collection(target_date)
                all_stats.append(stats)
                
                # 배치 간 딜레이 (API 할당량 관리)
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"{target_date} 수집 실패: {e}")
                continue
        
        # 배치 수집 요약
        total_videos = sum(stats.total_videos_processed for stats in all_stats)
        total_trending = sum(stats.trending_videos_count for stats in all_stats)
        total_errors = sum(stats.error_count for stats in all_stats)
        
        logger.info(f"🎯 배치 수집 완료:")
        logger.info(f"   - 처리된 날짜: {len(all_stats)}/{len(date_range)}")
        logger.info(f"   - 총 영상 수: {total_videos:,}개")
        logger.info(f"   - 총 트렌딩: {total_trending:,}개")
        logger.info(f"   - 총 오류: {total_errors}개")
        
        return all_stats
    
    def get_stats(self) -> CollectionStats:
        """수집 통계 반환"""
        return self.stats
    
    async def _initialize_collector(self):
        """데이터 수집기 초기화"""
        logger.info("데이터 수집기 초기화 중...")
        
        self.data_collector = YouTubeTrainingDataCollector(
            api_keys=self.config.youtube_api_keys,
            output_dir=self.config.output_directory
        )
        await self.data_collector.__aenter__()
        
        logger.info("데이터 수집기 초기화 완료")
    
    async def _cleanup_collector(self):
        """데이터 수집기 정리"""
        logger.info("데이터 수집기 정리 중...")
        
        if self.data_collector:
            await self.data_collector.__aexit__(None, None, None)
        
        logger.info("데이터 수집기 정리 완료")
    
    async def _update_collection_stats(self, csv_path: str):
        """수집 통계 업데이트"""
        try:
            self.stats.csv_file_path = csv_path
            
            # 파일 크기 확인
            if os.path.exists(csv_path):
                self.stats.file_size_bytes = os.path.getsize(csv_path)
                
                # CSV 파일에서 통계 추출
                try:
                    import csv as csv_module
                    with open(csv_path, 'r', encoding='utf-8-sig') as f:
                        reader = csv_module.DictReader(f)
                        rows = list(reader)
                        
                        self.stats.total_videos_processed = len(rows)
                        self.stats.trending_videos_count = sum(
                            1 for row in rows if row.get('is_trending_category') == '1'
                        )
                        
                except Exception as e:
                    logger.error(f"CSV 통계 추출 실패: {e}")
            
            # API 사용량 업데이트
            if self.data_collector:
                remaining_quota = self.data_collector.quota_manager.get_remaining_quota()
                self.stats.api_quota_used = 10000 - remaining_quota  # 기본 할당량에서 차감
                
        except Exception as e:
            logger.error(f"통계 업데이트 실패: {e}")
    
# 설정 로드 함수
def load_config_from_env() -> TrainingSystemConfig:
    """환경변수에서 설정 로드"""
    youtube_api_keys = os.getenv("YOUTUBE_API_KEYS", "").split(",")
    youtube_api_keys = [key.strip() for key in youtube_api_keys if key.strip()]
    
    if not youtube_api_keys:
        raise ValueError("YOUTUBE_API_KEYS 환경변수가 설정되지 않았습니다")
    
    return TrainingSystemConfig(
        youtube_api_keys=youtube_api_keys,
        collection_schedule=os.getenv("COLLECTION_SCHEDULE", "daily"),
        batch_size=int(os.getenv("BATCH_SIZE", "100")),
        output_directory=os.getenv("OUTPUT_DIRECTORY", "results"),
        min_view_count=int(os.getenv("MIN_VIEW_COUNT", "1000")),
        enable_data_validation=os.getenv("ENABLE_DATA_VALIDATION", "true").lower() == "true"
    )


# 메인 실행 함수
async def main():
    """메인 실행 함수"""
    try:
        # 설정 로드
        config = load_config_from_env()
        
        # 시스템 초기화
        system = YouTubeTrainingSystem(config)
        
        # 일별 데이터 수집 실행
        stats = await system.run_daily_collection()
        
        if stats.csv_file_path:
            logger.info("🎉 YouTube 학습 데이터 수집 성공!")
            logger.info(f"생성된 CSV: {stats.csv_file_path}")
        else:
            logger.error("❌ 데이터 수집 실패")
        
    except KeyboardInterrupt:
        logger.info("사용자가 프로그램을 중단했습니다")
    except Exception as e:
        logger.error(f"시스템 실행 실패: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())