#!/usr/bin/env python3
"""
YouTube AI 학습용 데이터셋 분석기
===============================

수집된 CSV 데이터셋을 분석하여 데이터 품질, K-Beauty 관련성, 
성과 지표 등을 종합적으로 분석하고 리포트를 생성합니다.

사용법:
    python analyze_dataset.py                           # 최신 파일 자동 분석
    python analyze_dataset.py --file dataset.csv       # 특정 파일 분석
    python analyze_dataset.py --all                    # 모든 파일 분석
"""

import csv
import argparse
import os
import glob
from collections import Counter
import statistics
from datetime import datetime
import sys


class YouTubeDatasetAnalyzer:
    """YouTube 데이터셋 분석기"""
    
    def __init__(self):
        # K-Beauty 관련 키워드 정의
        self.kbeauty_keywords = [
            'korean', 'k-beauty', 'skincare', 'beauty', 'makeup', 'cosmetics',
            'tirtir', 'biodance', 'anua', 'cosrx', 'some by mi', 'beauty of joseon',
            'torriden', 'round lab', 'glass skin', 'routine', 'serum', 'toner',
            'moisturizer', 'cleanser', 'sunscreen', 'mask', 'essence', 'cream',
            'lotion', 'ampoule', 'patch', 'peel', 'exfoliant', 'mist', 'oil'
        ]
    
    def load_dataset(self, file_path: str) -> list:
        """CSV 데이터셋 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                data = list(reader)
            return data
        except Exception as e:
            print(f"❌ 파일 로드 실패: {e}")
            return []
    
    def analyze_basic_stats(self, data: list) -> dict:
        """기본 통계 분석"""
        if not data:
            return {}
        
        return {
            'total_records': len(data),
            'total_columns': len(data[0].keys()),
            'columns': list(data[0].keys()),
            'file_size_kb': len(str(data)) / 1024
        }
    
    def analyze_data_sources(self, data: list) -> dict:
        """데이터 소스별 분포 분석"""
        source_counts = Counter(row['source_type'] for row in data)
        total = len(data)
        
        return {
            'source_distribution': {
                source: {
                    'count': count,
                    'percentage': count / total * 100
                }
                for source, count in source_counts.items()
            }
        }
    
    def analyze_trending_videos(self, data: list) -> dict:
        """트렌딩 영상 분석"""
        trending_count = sum(1 for row in data if row['is_trending_category'] == '1')
        total = len(data)
        
        return {
            'trending_count': trending_count,
            'trending_percentage': trending_count / total * 100,
            'normal_count': total - trending_count,
            'normal_percentage': (total - trending_count) / total * 100
        }
    
    def analyze_performance_metrics(self, data: list) -> dict:
        """성과 지표 분석"""
        # 조회수 분석
        view_counts = []
        engagement_rates = []
        vpv_ratios = []
        velocities = []
        subscriber_counts = []
        durations = []
        
        for row in data:
            try:
                view_counts.append(int(row['view_count']))
                engagement_rates.append(float(row['engagement_rate']))
                vpv_ratios.append(float(row['vpv_ratio']))
                velocities.append(float(row['view_velocity']))
                subscriber_counts.append(int(row['subscriber_count']))
                durations.append(int(row['duration_sec']))
            except (ValueError, KeyError):
                continue
        
        def safe_stats(values):
            if not values:
                return {'mean': 0, 'median': 0, 'max': 0, 'min': 0}
            return {
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'max': max(values),
                'min': min(values)
            }
        
        return {
            'view_counts': safe_stats(view_counts),
            'engagement_rates': safe_stats(engagement_rates),
            'vpv_ratios': safe_stats(vpv_ratios),
            'velocities': safe_stats(velocities),
            'subscriber_counts': safe_stats(subscriber_counts),
            'durations': safe_stats(durations),
            'high_vpv_count': sum(1 for vpv in vpv_ratios if vpv > 2.0)
        }
    
    def analyze_kbeauty_relevance(self, data: list) -> dict:
        """K-Beauty 관련성 분석"""
        kbeauty_count = 0
        keyword_matches = Counter()
        kbeauty_samples = []
        
        for row in data:
            title = row['title'].lower()
            description_keywords = row['description_keywords'].lower()
            
            # K-Beauty 키워드 찾기
            found_keywords = []
            for keyword in self.kbeauty_keywords:
                if keyword in title or keyword in description_keywords:
                    found_keywords.append(keyword)
                    keyword_matches[keyword] += 1
            
            if found_keywords:
                kbeauty_count += 1
                try:
                    kbeauty_samples.append({
                        'title': row['title'],
                        'channel': row['channel_name'],
                        'views': int(row['view_count']),
                        'keywords': row['description_keywords'],
                        'found_keywords': found_keywords
                    })
                except (ValueError, KeyError):
                    pass
        
        # 조회수 순으로 정렬
        kbeauty_samples.sort(key=lambda x: x['views'], reverse=True)
        
        return {
            'kbeauty_count': kbeauty_count,
            'kbeauty_percentage': kbeauty_count / len(data) * 100,
            'normal_count': len(data) - kbeauty_count,
            'normal_percentage': (len(data) - kbeauty_count) / len(data) * 100,
            'top_keywords': keyword_matches.most_common(10),
            'top_samples': kbeauty_samples[:5]
        }
    
    def analyze_data_quality(self, data: list) -> dict:
        """데이터 품질 분석"""
        missing_data = 0
        required_fields = ['title', 'channel_name', 'view_count', 'video_id']
        
        for row in data:
            for field in required_fields:
                if not row.get(field, '').strip():
                    missing_data += 1
                    break
        
        return {
            'missing_data_count': missing_data,
            'missing_data_percentage': missing_data / len(data) * 100,
            'completeness_percentage': (len(data) - missing_data) / len(data) * 100
        }
    
    def analyze_high_performance(self, data: list) -> dict:
        """고성과 영상 분석"""
        high_performance = []
        
        for row in data:
            try:
                vpv = float(row['vpv_ratio'])
                engagement = float(row['engagement_rate'])
                velocity = float(row['view_velocity'])
                views = int(row['view_count'])
                
                # 고성과 기준: VPV > 2.0 또는 참여율 > 5% 또는 시간당 조회수 > 1000
                if vpv > 2.0 or engagement > 0.05 or velocity > 1000:
                    high_performance.append({
                        'title': row['title'],
                        'channel': row['channel_name'],
                        'vpv': vpv,
                        'engagement': engagement,
                        'velocity': velocity,
                        'views': views,
                        'is_trending': row['is_trending_category'] == '1'
                    })
            except (ValueError, KeyError):
                continue
        
        # 조회수 순으로 정렬
        high_performance.sort(key=lambda x: x['views'], reverse=True)
        
        return {
            'high_performance_count': len(high_performance),
            'high_performance_percentage': len(high_performance) / len(data) * 100,
            'top_performers': high_performance[:5]
        }
    
    def analyze_channels(self, data: list) -> dict:
        """채널 분석"""
        channels = [row['channel_name'] for row in data if row['channel_name']]
        channel_counts = Counter(channels)
        
        return {
            'unique_channels': len(set(channels)),
            'top_channels': channel_counts.most_common(5)
        }
    
    def generate_report(self, file_path: str) -> None:
        """종합 분석 리포트 생성"""
        print(f"🔍 YouTube AI 학습용 데이터셋 분석 리포트")
        print(f"📁 파일: {file_path}")
        print(f"📅 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 데이터 로드
        data = self.load_dataset(file_path)
        if not data:
            print("❌ 데이터를 로드할 수 없습니다.")
            return
        
        # 1. 기본 통계
        basic_stats = self.analyze_basic_stats(data)
        print(f"\n📊 1. 기본 통계")
        print(f"   - 총 레코드 수: {basic_stats['total_records']:,}개")
        print(f"   - 컬럼 수: {basic_stats['total_columns']}개")
        print(f"   - 예상 파일 크기: {basic_stats['file_size_kb']:.1f} KB")
        
        # 2. 데이터 소스 분포
        source_analysis = self.analyze_data_sources(data)
        print(f"\n📈 2. 데이터 소스별 분포")
        for source, stats in source_analysis['source_distribution'].items():
            print(f"   - {source}: {stats['count']}개 ({stats['percentage']:.1f}%)")
        
        # 3. 트렌딩 영상 분석
        trending_analysis = self.analyze_trending_videos(data)
        print(f"\n🔥 3. 트렌딩 영상 분석")
        print(f"   - 트렌딩 영상: {trending_analysis['trending_count']}개 ({trending_analysis['trending_percentage']:.1f}%)")
        print(f"   - 일반 영상: {trending_analysis['normal_count']}개 ({trending_analysis['normal_percentage']:.1f}%)")
        
        # 4. 성과 지표 분석
        performance = self.analyze_performance_metrics(data)
        print(f"\n📊 4. 성과 지표 분석")
        
        print(f"   👀 조회수:")
        print(f"      - 평균: {performance['view_counts']['mean']:,.0f}")
        print(f"      - 중간값: {performance['view_counts']['median']:,.0f}")
        print(f"      - 최고: {performance['view_counts']['max']:,.0f}")
        print(f"      - 최저: {performance['view_counts']['min']:,.0f}")
        
        print(f"   💬 참여율:")
        print(f"      - 평균: {performance['engagement_rates']['mean']:.4f} ({performance['engagement_rates']['mean']*100:.2f}%)")
        print(f"      - 중간값: {performance['engagement_rates']['median']:.4f} ({performance['engagement_rates']['median']*100:.2f}%)")
        print(f"      - 최고: {performance['engagement_rates']['max']:.4f} ({performance['engagement_rates']['max']*100:.2f}%)")
        
        print(f"   📊 VPV (구독자 대비 조회수):")
        print(f"      - 평균: {performance['vpv_ratios']['mean']:.3f}")
        print(f"      - 중간값: {performance['vpv_ratios']['median']:.3f}")
        print(f"      - 최고: {performance['vpv_ratios']['max']:.3f}")
        print(f"      - VPV > 2.0 (초강력 바이럴): {performance['high_vpv_count']}개")
        
        print(f"   ⚡ View Velocity (시간당 조회수):")
        print(f"      - 평균: {performance['velocities']['mean']:,.0f} views/hour")
        print(f"      - 중간값: {performance['velocities']['median']:,.0f} views/hour")
        print(f"      - 최고: {performance['velocities']['max']:,.0f} views/hour")
        
        print(f"   📺 채널 구독자:")
        print(f"      - 평균: {performance['subscriber_counts']['mean']:,.0f}")
        print(f"      - 중간값: {performance['subscriber_counts']['median']:,.0f}")
        
        print(f"   ⏱️ 영상 길이:")
        print(f"      - 평균: {performance['durations']['mean']/60:.1f}분")
        print(f"      - 중간값: {performance['durations']['median']/60:.1f}분")
        print(f"      - 최장: {performance['durations']['max']/60:.1f}분")
        print(f"      - 최단: {performance['durations']['min']/60:.1f}분")
        
        # 5. K-Beauty 관련성 분석
        kbeauty_analysis = self.analyze_kbeauty_relevance(data)
        print(f"\n🌸 5. K-Beauty 관련성 분석")
        print(f"   - K-Beauty 관련 영상: {kbeauty_analysis['kbeauty_count']}개 ({kbeauty_analysis['kbeauty_percentage']:.1f}%)")
        print(f"   - 일반 영상: {kbeauty_analysis['normal_count']}개 ({kbeauty_analysis['normal_percentage']:.1f}%)")
        
        print(f"\n   🔥 가장 많이 발견된 K-Beauty 키워드:")
        for keyword, count in kbeauty_analysis['top_keywords']:
            print(f"      - {keyword}: {count}개")
        
        print(f"\n   📋 K-Beauty 관련 영상 샘플 (조회수 순):")
        for i, sample in enumerate(kbeauty_analysis['top_samples'], 1):
            title = sample['title'][:60] + '...' if len(sample['title']) > 60 else sample['title']
            print(f"      {i}. {title}")
            print(f"         채널: {sample['channel']} | 조회수: {sample['views']:,}")
            if sample['keywords']:
                keywords = sample['keywords'][:50] + '...' if len(sample['keywords']) > 50 else sample['keywords']
                print(f"         키워드: {keywords}")
        
        # 6. 데이터 품질 검증
        quality_analysis = self.analyze_data_quality(data)
        print(f"\n🔍 6. 데이터 품질 검증")
        print(f"   - 필수 데이터 누락: {quality_analysis['missing_data_count']}개 ({quality_analysis['missing_data_percentage']:.1f}%)")
        print(f"   - 데이터 완성도: {quality_analysis['completeness_percentage']:.1f}%")
        
        # 7. 고성과 영상 분석
        high_perf_analysis = self.analyze_high_performance(data)
        print(f"\n⭐ 7. 고성과 영상 분석")
        print(f"   - 고성과 영상: {high_perf_analysis['high_performance_count']}개 ({high_perf_analysis['high_performance_percentage']:.1f}%)")
        
        if high_perf_analysis['top_performers']:
            print(f"\n   🏆 상위 고성과 영상:")
            for i, video in enumerate(high_perf_analysis['top_performers'], 1):
                title = video['title'][:50] + '...' if len(video['title']) > 50 else video['title']
                trending_mark = " 🔥" if video['is_trending'] else ""
                print(f"      {i}. {title}{trending_mark}")
                print(f"         조회수: {video['views']:,} | VPV: {video['vpv']:.2f} | 참여율: {video['engagement']*100:.2f}%")
                print(f"         채널: {video['channel']}")
        
        # 8. 채널 분석
        channel_analysis = self.analyze_channels(data)
        print(f"\n📺 8. 채널 분석")
        print(f"   - 고유 채널 수: {channel_analysis['unique_channels']}개")
        print(f"   - 상위 채널 (영상 수 기준):")
        for channel, count in channel_analysis['top_channels']:
            print(f"      - {channel}: {count}개")
        
        # 9. AI 학습 적합성 평가
        print(f"\n🤖 9. AI 학습 적합성 평가")
        
        # 타겟 밸런스 확인
        trending_ratio = trending_analysis['trending_percentage']
        if trending_ratio < 1:
            balance_score = "⚠️ 불균형 (트렌딩 영상 부족)"
        elif trending_ratio > 10:
            balance_score = "⚠️ 불균형 (트렌딩 영상 과다)"
        else:
            balance_score = "✅ 양호"
        
        # 데이터 다양성 확인
        diversity_score = "✅ 우수" if channel_analysis['unique_channels'] > 100 else "⚠️ 보통"
        
        # K-Beauty 관련성 확인
        relevance_score = "✅ 우수" if kbeauty_analysis['kbeauty_percentage'] > 70 else "⚠️ 보통"
        
        print(f"   - 타겟 밸런스: {balance_score} (트렌딩 {trending_ratio:.1f}%)")
        print(f"   - 데이터 다양성: {diversity_score} (채널 {channel_analysis['unique_channels']}개)")
        print(f"   - K-Beauty 관련성: {relevance_score} ({kbeauty_analysis['kbeauty_percentage']:.1f}%)")
        print(f"   - 데이터 품질: {'✅ 우수' if quality_analysis['completeness_percentage'] > 95 else '⚠️ 보통'} ({quality_analysis['completeness_percentage']:.1f}%)")
        
        print(f"\n" + "=" * 80)
        print(f"📋 분석 완료! 총 {basic_stats['total_records']:,}개 레코드 분석됨")


def find_latest_dataset(directory: str = "results") -> str:
    """가장 최근 데이터셋 파일 찾기"""
    pattern = os.path.join(directory, "youtube_viral_dataset_v1_*.csv")
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    # 파일명에서 날짜 추출하여 정렬
    files.sort(key=lambda x: os.path.basename(x).split('_')[-1].replace('.csv', ''), reverse=True)
    return files[0]


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="YouTube AI 학습용 데이터셋 분석기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  %(prog)s                                    # 최신 파일 자동 분석
  %(prog)s --file dataset.csv                # 특정 파일 분석
  %(prog)s --all                             # 모든 파일 분석
        """
    )
    
    parser.add_argument(
        '--file', '-f',
        type=str,
        help='분석할 CSV 파일 경로'
    )
    
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='results 폴더의 모든 데이터셋 파일 분석'
    )
    
    parser.add_argument(
        '--directory', '-d',
        type=str,
        default='results',
        help='데이터셋 파일이 있는 디렉토리 (기본값: results)'
    )
    
    args = parser.parse_args()
    
    analyzer = YouTubeDatasetAnalyzer()
    
    if args.all:
        # 모든 파일 분석
        pattern = os.path.join(args.directory, "youtube_viral_dataset_v1_*.csv")
        files = glob.glob(pattern)
        
        if not files:
            print(f"❌ {args.directory} 폴더에서 데이터셋 파일을 찾을 수 없습니다.")
            return
        
        files.sort()
        print(f"📁 {len(files)}개 파일을 분석합니다...\n")
        
        for i, file_path in enumerate(files, 1):
            print(f"\n{'='*20} 파일 {i}/{len(files)} {'='*20}")
            analyzer.generate_report(file_path)
            
    elif args.file:
        # 특정 파일 분석
        if not os.path.exists(args.file):
            print(f"❌ 파일을 찾을 수 없습니다: {args.file}")
            return
        
        analyzer.generate_report(args.file)
        
    else:
        # 최신 파일 자동 분석
        latest_file = find_latest_dataset(args.directory)
        
        if not latest_file:
            print(f"❌ {args.directory} 폴더에서 데이터셋 파일을 찾을 수 없습니다.")
            print(f"다음 명령으로 데이터를 수집해주세요:")
            print(f"python run_training_collection.py")
            return
        
        print(f"📁 최신 파일을 자동으로 선택했습니다: {os.path.basename(latest_file)}")
        analyzer.generate_report(latest_file)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n사용자가 분석을 중단했습니다.")
    except Exception as e:
        print(f"분석 중 오류 발생: {e}")
        sys.exit(1)