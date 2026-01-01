#!/usr/bin/env python3
"""
YouTube AI 학습용 데이터 수집 실행 스크립트
========================================

일별 배치로 YouTube 학습 데이터를 수집하여 CSV 파일을 생성합니다.

실행 방법:
    # 오늘 날짜로 수집
    python run_training_collection.py
    
    # 특정 날짜로 수집
    python run_training_collection.py --date 2026-01-01
    
    # 날짜 범위로 배치 수집
    python run_training_collection.py --start-date 2025-12-28 --end-date 2025-12-31

환경변수 설정:
    export YOUTUBE_API_KEYS="your_api_key1,your_api_key2"
"""

import asyncio
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.viral_detection_system import YouTubeTrainingSystem, load_config_from_env
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(
        description="YouTube AI 학습용 데이터 수집 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  %(prog)s                                    # 오늘 날짜로 수집
  %(prog)s --date 2026-01-01                  # 특정 날짜로 수집
  %(prog)s --start-date 2025-12-28 --end-date 2025-12-31  # 배치 수집
        """
    )
    
    parser.add_argument(
        '--date',
        type=str,
        help='수집할 날짜 (YYYY-MM-DD 형식)'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        help='배치 수집 시작 날짜 (YYYY-MM-DD 형식)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        help='배치 수집 종료 날짜 (YYYY-MM-DD 형식)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='results',
        help='결과 파일 저장 디렉토리 (기본값: results)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )
    
    return parser.parse_args()


def validate_date(date_str: str) -> bool:
    """날짜 형식 검증"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def generate_date_range(start_date: str, end_date: str) -> list:
    """날짜 범위 생성"""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start > end:
            raise ValueError("시작 날짜가 종료 날짜보다 늦습니다")
        
        date_list = []
        current = start
        while current <= end:
            date_list.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        return date_list
        
    except ValueError as e:
        logger.error(f"날짜 범위 생성 실패: {e}")
        return []


async def run_single_collection(system: YouTubeTrainingSystem, target_date: str):
    """단일 날짜 데이터 수집"""
    logger.info(f"🚀 단일 수집 시작: {target_date}")
    
    stats = await system.run_daily_collection(target_date)
    
    if stats.csv_file_path:
        logger.info(f"✅ 수집 완료: {stats.csv_file_path}")
        logger.info(f"   - 처리된 영상: {stats.total_videos_processed}개")
        logger.info(f"   - 트렌딩 영상: {stats.trending_videos_count}개")
        logger.info(f"   - 파일 크기: {stats.file_size_bytes:,} bytes")
        return True
    else:
        logger.error("❌ 데이터 수집 실패")
        return False


async def run_batch_collection(system: YouTubeTrainingSystem, date_range: list):
    """배치 데이터 수집"""
    logger.info(f"🚀 배치 수집 시작: {len(date_range)}개 날짜")
    logger.info(f"   - 날짜 범위: {date_range[0]} ~ {date_range[-1]}")
    
    all_stats = await system.run_batch_collection(date_range)
    
    if all_stats:
        successful_collections = [stats for stats in all_stats if stats.csv_file_path]
        total_videos = sum(stats.total_videos_processed for stats in successful_collections)
        total_trending = sum(stats.trending_videos_count for stats in successful_collections)
        
        logger.info(f"✅ 배치 수집 완료")
        logger.info(f"   - 성공한 수집: {len(successful_collections)}/{len(date_range)}")
        logger.info(f"   - 총 영상 수: {total_videos:,}개")
        logger.info(f"   - 총 트렌딩: {total_trending:,}개")
        
        # 생성된 파일 목록
        logger.info("📁 생성된 파일:")
        for stats in successful_collections:
            if stats.csv_file_path:
                logger.info(f"   - {stats.csv_file_path}")
        
        return len(successful_collections) > 0
    else:
        logger.error("❌ 배치 수집 실패")
        return False


async def main():
    """메인 실행 함수"""
    args = parse_arguments()
    
    # 로깅 레벨 설정
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("🎯 YouTube AI 학습용 데이터 수집 시스템")
    logger.info("=" * 50)
    
    try:
        # 설정 로드
        config = load_config_from_env()
        
        # 출력 디렉토리 설정
        if args.output_dir:
            config.output_directory = args.output_dir
        
        # 시스템 초기화
        system = YouTubeTrainingSystem(config)
        
        logger.info(f"📋 시스템 설정:")
        logger.info(f"   - API 키 개수: {len(config.youtube_api_keys)}")
        logger.info(f"   - 출력 디렉토리: {config.output_directory}")
        logger.info(f"   - 배치 크기: {config.batch_size}")
        
        # 실행 모드 결정
        if args.start_date and args.end_date:
            # 배치 수집 모드
            if not validate_date(args.start_date) or not validate_date(args.end_date):
                logger.error("❌ 잘못된 날짜 형식입니다. YYYY-MM-DD 형식을 사용하세요.")
                return False
            
            date_range = generate_date_range(args.start_date, args.end_date)
            if not date_range:
                return False
            
            if len(date_range) > 7:
                confirm = input(f"⚠️ {len(date_range)}일간의 데이터를 수집합니다. 계속하시겠습니까? (y/N): ")
                if confirm.lower() != 'y':
                    logger.info("수집이 취소되었습니다.")
                    return False
            
            success = await run_batch_collection(system, date_range)
            
        else:
            # 단일 수집 모드
            target_date = args.date
            
            if target_date:
                if not validate_date(target_date):
                    logger.error("❌ 잘못된 날짜 형식입니다. YYYY-MM-DD 형식을 사용하세요.")
                    return False
            else:
                target_date = datetime.now().strftime('%Y-%m-%d')
                logger.info(f"📅 날짜가 지정되지 않아 오늘 날짜로 수집합니다: {target_date}")
            
            success = await run_single_collection(system, target_date)
        
        if success:
            logger.info("🎉 데이터 수집이 성공적으로 완료되었습니다!")
        else:
            logger.error("❌ 데이터 수집에 실패했습니다.")
            return False
            
    except KeyboardInterrupt:
        logger.info("사용자가 수집을 중단했습니다.")
        return False
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}")
        return False
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"프로그램 실행 실패: {e}")
        sys.exit(1)