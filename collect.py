#!/usr/bin/env python3
"""
YouTube AI 학습용 데이터 수집 - 간단 실행 스크립트
==============================================

사용법:
    python collect.py              # 오늘 날짜로 수집
    python collect.py 2026-01-01   # 특정 날짜로 수집
"""

import sys
import os
import asyncio
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

from src.viral_detection_system import YouTubeTrainingSystem, load_config_from_env


async def main():
    """메인 실행 함수"""
    try:
        # 설정 로드
        config = load_config_from_env()
        
        # 날짜 설정
        target_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
        
        print(f"🚀 YouTube AI 학습용 데이터 수집 시작")
        print(f"📅 수집 날짜: {target_date}")
        print(f"🔑 API 키: {len(config.youtube_api_keys)}개")
        print("-" * 50)
        
        # 시스템 초기화 및 실행
        system = YouTubeTrainingSystem(config)
        stats = await system.run_daily_collection(target_date)
        
        if stats.csv_file_path:
            print(f"\n✅ 수집 완료!")
            print(f"📁 파일: {stats.csv_file_path}")
            print(f"📊 영상 수: {stats.total_videos_processed}개")
            print(f"🔥 트렌딩: {stats.trending_videos_count}개")
            print(f"💾 크기: {stats.file_size_bytes:,} bytes")
            
            # 분석 실행 제안
            print(f"\n💡 분석을 실행하려면:")
            print(f"python analyze_dataset.py")
        else:
            print("❌ 데이터 수집 실패")
            
    except KeyboardInterrupt:
        print("\n사용자가 수집을 중단했습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    asyncio.run(main())