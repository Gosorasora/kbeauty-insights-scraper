"""
YouTube Training Data Collector
==============================

AI 모델 학습용 데이터셋 구축을 위한 YouTube 데이터 수집기

주요 기능:
- 소스 A: 거시 트렌드 (videos.list - mostPopular)
- 소스 B: 키워드 발굴 (search.list - Korean Skincare 등)
- 소스 C: 타겟 채널 (주요 인플루언서 채널 모니터링)
- 피처 엔지니어링 (View Velocity, VPV, Engagement Rate)
- CSV 데이터셋 생성 (UTF-8-SIG, 일별 적재)

사용법:
    from src.collectors.youtube_training_data_collector import YouTubeTrainingDataCollector
    
    collector = YouTubeTrainingDataCollector(api_keys=['your_api_key'])
    dataset = await collector.collect_daily_dataset()
"""

import asyncio
import aiohttp
import csv
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class VideoTrainingData:
    """AI 학습용 영상 데이터 구조 (CSV 스키마와 일치)"""
    # 식별자
    collection_date: str  # YYYY-MM-DD
    video_id: str
    
    # 기본 정보
    title: str
    channel_name: str
    upload_date: str  # ISO format
    duration_sec: int
    
    # 성과 지표
    subscriber_count: int
    view_count: int
    like_count: int
    comment_count: int
    
    # 파생 피처
    view_velocity: float  # 시간당 조회수 증가량
    vpv_ratio: float     # 구독자 대비 조회수 비율
    engagement_rate: float # 조회수 대비 반응율
    
    # 텍스트 데이터
    top_comments_text: str  # 파이프(|)로 구분된 상위 댓글
    description_keywords: str  # 쉼표로 구분된 키워드
    
    # 타겟값
    is_trending_category: int  # 인기 급상승 차트 진입 여부 (1/0)
    
    # 메타데이터
    source_type: str  # 'macro_trend', 'keyword_discovery', 'channel_performance'


class APIQuotaManager:
    """YouTube API 할당량 관리자"""
    
    def __init__(self, api_keys: List[str], daily_quota: int = 10000):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.daily_quota = daily_quota
        self.usage_per_key = {key: 0 for key in api_keys}
        self.last_reset = datetime.now().date()
    
    def get_current_api_key(self) -> str:
        """현재 사용할 API 키 반환"""
        self._check_daily_reset()
        return self.api_keys[self.current_key_index]
    
    def record_usage(self, cost: int):
        """API 사용량 기록"""
        current_key = self.get_current_api_key()
        self.usage_per_key[current_key] += cost
        
        # 할당량 90% 초과시 다음 키로 로테이션
        if self.usage_per_key[current_key] > self.daily_quota * 0.9:
            self._rotate_api_key()
    
    def _rotate_api_key(self):
        """API 키 로테이션"""
        old_index = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        
        if self.current_key_index == old_index:
            logger.warning("모든 API 키의 할당량이 소진되었습니다")
            raise Exception("API quota exhausted for all keys")
        
        logger.info(f"API 키 로테이션: {self.current_key_index + 1}/{len(self.api_keys)}")
    
    def _check_daily_reset(self):
        """일일 할당량 리셋 확인"""
        today = datetime.now().date()
        if today > self.last_reset:
            self.usage_per_key = {key: 0 for key in self.api_keys}
            self.last_reset = today
            self.current_key_index = 0
            logger.info("일일 API 할당량 리셋")
    
    def get_remaining_quota(self) -> int:
        """남은 할당량 반환"""
        current_key = self.get_current_api_key()
        return max(0, self.daily_quota - self.usage_per_key[current_key])


class YouTubeTrainingDataCollector:
    """YouTube AI 학습용 데이터 수집기"""
    
    # YouTube Data API v3 엔드포인트
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    # SRS 요구사항에 따른 키워드 셋
    TARGET_KEYWORDS = [
        "Korean Skincare", "Glass Skin", "K-Beauty Routine",
        "Korean Beauty", "Korean Makeup", "Korean Cosmetics",
        "Tirtir", "Biodance", "Anua", "COSRX", "Some By Mi",
        "Beauty of Joseon", "Torriden", "Round Lab"
    ]
    
    # 뷰티 관련 필터링 키워드
    BEAUTY_FILTER_KEYWORDS = [
        "makeup", "skincare", "beauty", "routine", "review",
        "tutorial", "haul", "unboxing", "korean", "k-beauty",
        "serum", "toner", "moisturizer", "cleanser", "sunscreen"
    ]
    
    # 주요 글로벌 뷰티 인플루언서 채널 ID
    TARGET_CHANNELS = [
        "UCdKuE7a2QZeHPhDntXVZ91w",  # James Welsh
        "UCQhwBjjWuLrcE0tJOjq4rKw",  # Gothamista
        "UC2sYit3cZ2B04MGgy0It6dQ",  # Liah Yoo
        "UCsyn_0Fx8w8eZlASIUkamBg",  # Hyram
        "UCBJycsmduvYEL83R_U4JriQ",  # Mixed Makeup
        # 실제 운영시 더 많은 채널 추가
    ]
    
    def __init__(self, api_keys: List[str], output_dir: str = "results"):
        """
        YouTube 학습 데이터 수집기 초기화
        
        Args:
            api_keys: YouTube Data API v3 키 목록
            output_dir: CSV 파일 저장 디렉토리
        """
        if not api_keys:
            raise ValueError("최소 하나의 API 키가 필요합니다")
        
        self.quota_manager = APIQuotaManager(api_keys)
        self.session = None
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 중복 제거를 위한 캐시
        self.processed_videos = set()
        
        # 트렌딩 영상 ID 캐시 (is_trending_category 판별용)
        self.trending_video_ids = set()
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        import ssl
        import certifi
        
        # SSL 컨텍스트 생성 (인증서 검증 문제 해결)
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # aiohttp 커넥터 생성
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    async def collect_daily_dataset(self, target_date: Optional[str] = None) -> str:
        """
        일별 학습 데이터셋 수집 및 CSV 생성
        
        Args:
            target_date: 수집 대상 날짜 (YYYY-MM-DD), None이면 오늘 날짜
            
        Returns:
            생성된 CSV 파일 경로
        """
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"🚀 YouTube 학습 데이터 수집 시작 (날짜: {target_date})")
        
        try:
            # 1단계: 트렌딩 영상 ID 수집 (타겟값 생성용)
            logger.info("📊 1단계: 트렌딩 영상 ID 수집")
            await self._collect_trending_video_ids()
            
            # 2단계: 다중 소스 데이터 수집
            logger.info("🔍 2단계: 다중 소스 데이터 수집")
            
            collection_tasks = [
                self._collect_macro_trends(),      # 소스 A: 거시적 트렌드
                self._collect_keyword_discovery(), # 소스 B: 키워드 발굴
                self._collect_channel_performance() # 소스 C: 채널 성과
            ]
            
            macro_data, keyword_data, channel_data = await asyncio.gather(
                *collection_tasks, return_exceptions=True
            )
            
            # 예외 처리
            if isinstance(macro_data, Exception):
                logger.error(f"거시적 트렌드 수집 실패: {macro_data}")
                macro_data = []
            
            if isinstance(keyword_data, Exception):
                logger.error(f"키워드 발굴 실패: {keyword_data}")
                keyword_data = []
            
            if isinstance(channel_data, Exception):
                logger.error(f"채널 성과 수집 실패: {channel_data}")
                channel_data = []
            
            # 데이터 통합
            all_raw_data = macro_data + keyword_data + channel_data
            logger.info(f"원시 데이터 수집 완료: 총 {len(all_raw_data)}개 (거시 {len(macro_data)}, 키워드 {len(keyword_data)}, 채널 {len(channel_data)})")
            
            if not all_raw_data:
                logger.warning("수집된 데이터가 없습니다")
                return ""
            
            # 3단계: 데이터 정제 및 피처 엔지니어링
            logger.info("⚙️ 3단계: 데이터 정제 및 피처 엔지니어링")
            training_data = []
            
            for raw_video in all_raw_data:
                try:
                    processed_video = await self._process_video_for_training(raw_video, target_date)
                    if processed_video:
                        training_data.append(processed_video)
                except Exception as e:
                    logger.error(f"영상 처리 실패 ({raw_video.get('id', 'unknown')}): {e}")
                    continue
            
            # 중복 제거 (video_id 기준)
            unique_training_data = self._deduplicate_training_data(training_data)
            logger.info(f"데이터 처리 완료: {len(unique_training_data)}개 (중복 제거 후)")
            
            # 4단계: CSV 파일 생성
            logger.info("💾 4단계: CSV 데이터셋 생성")
            csv_path = await self._save_training_dataset_csv(unique_training_data, target_date)
            
            logger.info(f"✅ 학습 데이터셋 생성 완료: {csv_path}")
            logger.info(f"   - 총 레코드 수: {len(unique_training_data)}")
            logger.info(f"   - 트렌딩 영상 수: {sum(1 for data in unique_training_data if data.is_trending_category == 1)}")
            
            return csv_path
            
        except Exception as e:
            logger.error(f"학습 데이터 수집 실패: {e}")
            return ""
    
    async def _collect_trending_video_ids(self):
        """트렌딩 영상 ID 수집 (타겟값 생성용)"""
        try:
            api_key = self.quota_manager.get_current_api_key()
            
            params = {
                'part': 'id',
                'chart': 'mostPopular',
                'regionCode': 'US',
                'categoryId': '26',  # Howto & Style (뷰티 포함)
                'maxResults': 50,
                'key': api_key
            }
            
            url = f"{self.BASE_URL}/videos"
            
            async with self.session.get(url, params=params) as response:
                self.quota_manager.record_usage(1)  # Videos API 비용
                
                if response.status == 200:
                    data = await response.json()
                    video_ids = [item['id'] for item in data.get('items', [])]
                    self.trending_video_ids.update(video_ids)
                    logger.info(f"트렌딩 영상 ID {len(video_ids)}개 수집 완료")
                else:
                    logger.error(f"트렌딩 영상 ID 수집 실패: {response.status}")
                    
        except Exception as e:
            logger.error(f"트렌딩 영상 ID 수집 실패: {e}")
    
    async def _collect_macro_trends(self) -> List[Dict[str, Any]]:
        """소스 A: 거시적 트렌드 감지"""
        try:
            api_key = self.quota_manager.get_current_api_key()
            
            params = {
                'part': 'snippet,statistics,contentDetails',
                'chart': 'mostPopular',
                'regionCode': 'US',
                'categoryId': '26',  # Howto & Style
                'maxResults': 50,
                'key': api_key
            }
            
            url = f"{self.BASE_URL}/videos"
            
            async with self.session.get(url, params=params) as response:
                self.quota_manager.record_usage(1)
                
                if response.status == 200:
                    data = await response.json()
                    videos = data.get('items', [])
                    
                    # 뷰티 관련 영상만 필터링
                    filtered_videos = []
                    for video in videos:
                        if self._is_beauty_related(video):
                            video['source_type'] = 'macro_trend'
                            filtered_videos.append(video)
                    
                    logger.info(f"거시적 트렌드 수집: {len(filtered_videos)}개 (전체 {len(videos)}개 중)")
                    return filtered_videos
                else:
                    logger.error(f"거시적 트렌드 수집 실패: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"거시적 트렌드 수집 실패: {e}")
            return []
    
    async def _collect_keyword_discovery(self) -> List[Dict[str, Any]]:
        """소스 B: 마이크로 키워드 발굴"""
        all_videos = []
        
        for keyword in self.TARGET_KEYWORDS:
            try:
                api_key = self.quota_manager.get_current_api_key()
                
                # 검색 API 호출
                search_params = {
                    'part': 'snippet',
                    'q': keyword,
                    'type': 'video',
                    'maxResults': 20,
                    'order': 'viewCount',
                    'publishedAfter': (datetime.now() - timedelta(days=7)).isoformat() + 'Z',
                    'key': api_key
                }
                
                search_url = f"{self.BASE_URL}/search"
                
                async with self.session.get(search_url, params=search_params) as response:
                    self.quota_manager.record_usage(100)  # Search API 비용
                    
                    if response.status != 200:
                        logger.error(f"키워드 '{keyword}' 검색 실패: {response.status}")
                        continue
                    
                    search_data = await response.json()
                    video_ids = [item['id']['videoId'] for item in search_data.get('items', [])]
                    
                    if not video_ids:
                        continue
                
                # 영상 상세 정보 가져오기
                videos_params = {
                    'part': 'snippet,statistics,contentDetails',
                    'id': ','.join(video_ids),
                    'key': api_key
                }
                
                videos_url = f"{self.BASE_URL}/videos"
                
                async with self.session.get(videos_url, params=videos_params) as response:
                    self.quota_manager.record_usage(1)
                    
                    if response.status == 200:
                        data = await response.json()
                        videos = data.get('items', [])
                        
                        for video in videos:
                            video['source_type'] = 'keyword_discovery'
                            video['discovered_keyword'] = keyword
                        
                        all_videos.extend(videos)
                        logger.debug(f"키워드 '{keyword}': {len(videos)}개 영상 수집")
                    
                # API 호출 간 딜레이
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"키워드 '{keyword}' 발굴 실패: {e}")
                continue
        
        logger.info(f"키워드 발굴 완료: {len(all_videos)}개 영상")
        return all_videos
    
    async def _collect_channel_performance(self) -> List[Dict[str, Any]]:
        """소스 C: 타겟 채널 성과 기반 감지"""
        all_videos = []
        
        for channel_id in self.TARGET_CHANNELS:
            try:
                api_key = self.quota_manager.get_current_api_key()
                
                # 채널의 업로드 플레이리스트 ID 가져오기
                channel_params = {
                    'part': 'contentDetails',
                    'id': channel_id,
                    'key': api_key
                }
                
                channel_url = f"{self.BASE_URL}/channels"
                
                async with self.session.get(channel_url, params=channel_params) as response:
                    self.quota_manager.record_usage(1)
                    
                    if response.status != 200:
                        logger.error(f"채널 {channel_id} 정보 조회 실패: {response.status}")
                        continue
                    
                    channel_data = await response.json()
                    items = channel_data.get('items', [])
                    
                    if not items:
                        continue
                    
                    uploads_playlist_id = items[0]['contentDetails']['relatedPlaylists']['uploads']
                
                # 최신 업로드 영상 가져오기
                playlist_params = {
                    'part': 'snippet',
                    'playlistId': uploads_playlist_id,
                    'maxResults': 10,
                    'key': api_key
                }
                
                playlist_url = f"{self.BASE_URL}/playlistItems"
                
                async with self.session.get(playlist_url, params=playlist_params) as response:
                    self.quota_manager.record_usage(1)
                    
                    if response.status != 200:
                        continue
                    
                    playlist_data = await response.json()
                    video_ids = [
                        item['snippet']['resourceId']['videoId'] 
                        for item in playlist_data.get('items', [])
                    ]
                    
                    if not video_ids:
                        continue
                
                # 영상 상세 정보 가져오기
                videos_params = {
                    'part': 'snippet,statistics,contentDetails',
                    'id': ','.join(video_ids),
                    'key': api_key
                }
                
                videos_url = f"{self.BASE_URL}/videos"
                
                async with self.session.get(videos_url, params=videos_params) as response:
                    self.quota_manager.record_usage(1)
                    
                    if response.status == 200:
                        data = await response.json()
                        videos = data.get('items', [])
                        
                        # 뷰티 관련 영상만 필터링
                        filtered_videos = []
                        for video in videos:
                            if self._is_beauty_related(video):
                                video['source_type'] = 'channel_performance'
                                video['monitored_channel_id'] = channel_id
                                filtered_videos.append(video)
                        
                        all_videos.extend(filtered_videos)
                        logger.debug(f"채널 {channel_id}: {len(filtered_videos)}개 뷰티 영상 수집")
                
                # API 호출 간 딜레이
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"채널 {channel_id} 성과 수집 실패: {e}")
                continue
        
        logger.info(f"채널 성과 수집 완료: {len(all_videos)}개 영상")
        return all_videos
    
    def _is_beauty_related(self, video: Dict[str, Any]) -> bool:
        """영상이 뷰티 관련인지 판별"""
        try:
            snippet = video.get('snippet', {})
            title = snippet.get('title', '').lower()
            description = snippet.get('description', '').lower()
            tags = [tag.lower() for tag in snippet.get('tags', [])]
            
            # 제목, 설명, 태그에서 뷰티 키워드 검색
            text_to_check = f"{title} {description} {' '.join(tags)}"
            
            for keyword in self.BEAUTY_FILTER_KEYWORDS:
                if keyword in text_to_check:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"뷰티 관련성 판별 실패: {e}")
            return False
    
    async def _process_video_for_training(self, raw_video: Dict[str, Any], collection_date: str) -> Optional[VideoTrainingData]:
        """원시 영상 데이터를 학습용 데이터로 변환"""
        try:
            snippet = raw_video.get('snippet', {})
            statistics = raw_video.get('statistics', {})
            content_details = raw_video.get('contentDetails', {})
            
            video_id = raw_video.get('id', '')
            if not video_id:
                return None
            
            # 기본 정보 추출
            title = self._clean_text(snippet.get('title', ''))
            channel_name = self._clean_text(snippet.get('channelTitle', ''))
            upload_date = snippet.get('publishedAt', '')
            
            # 영상 길이 파싱 (PT4M13S -> 253초)
            duration_sec = self._parse_duration(content_details.get('duration', 'PT0S'))
            
            # 통계 정보 추출 (결측치 처리)
            view_count = int(statistics.get('viewCount', 0))
            like_count = int(statistics.get('likeCount', -1)) if statistics.get('likeCount') is not None else -1
            comment_count = int(statistics.get('commentCount', -1)) if statistics.get('commentCount') is not None else -1
            
            # 채널 구독자 수 조회 (별도 API 호출 필요)
            subscriber_count = await self._get_channel_subscriber_count(snippet.get('channelId', ''))
            
            # 파생 피처 계산
            view_velocity = self._calculate_view_velocity(view_count, upload_date)
            vpv_ratio = self._calculate_vpv_ratio(view_count, subscriber_count)
            engagement_rate = self._calculate_engagement_rate(view_count, like_count, comment_count)
            
            # 댓글 데이터 수집
            top_comments = await self._get_top_comments(video_id)
            top_comments_text = '|'.join(top_comments) if top_comments else ''
            
            # 키워드 추출
            description_keywords = self._extract_keywords(snippet.get('description', ''))
            
            # 타겟값 설정 (트렌딩 차트 진입 여부)
            is_trending_category = 1 if video_id in self.trending_video_ids else 0
            
            return VideoTrainingData(
                collection_date=collection_date,
                video_id=video_id,
                title=title,
                channel_name=channel_name,
                upload_date=upload_date,
                duration_sec=duration_sec,
                subscriber_count=subscriber_count,
                view_count=view_count,
                like_count=like_count,
                comment_count=comment_count,
                view_velocity=view_velocity,
                vpv_ratio=vpv_ratio,
                engagement_rate=engagement_rate,
                top_comments_text=top_comments_text,
                description_keywords=description_keywords,
                is_trending_category=is_trending_category,
                source_type=raw_video.get('source_type', 'unknown')
            )
            
        except Exception as e:
            logger.error(f"영상 데이터 처리 실패: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """텍스트 정제 (CSV 깨짐 방지)"""
        if not text:
            return ""
        
        # 이모지, 특수문자, 개행문자 제거/치환
        text = re.sub(r'[^\w\s가-힣]', ' ', text)  # 특수문자 제거
        text = re.sub(r'\s+', ' ', text)  # 연속 공백 제거
        text = text.strip()
        
        return text
    
    def _parse_duration(self, duration_str: str) -> int:
        """YouTube 영상 길이를 초 단위로 변환 (PT4M13S -> 253)"""
        try:
            if not duration_str or duration_str == 'PT0S':
                return 0
            
            # PT4M13S 형태 파싱
            pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
            match = re.match(pattern, duration_str)
            
            if not match:
                return 0
            
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            
            return hours * 3600 + minutes * 60 + seconds
            
        except Exception as e:
            logger.error(f"영상 길이 파싱 실패: {e}")
            return 0
    
    async def _get_channel_subscriber_count(self, channel_id: str) -> int:
        """채널 구독자 수 조회"""
        try:
            if not channel_id:
                return 0
            
            api_key = self.quota_manager.get_current_api_key()
            
            params = {
                'part': 'statistics',
                'id': channel_id,
                'key': api_key
            }
            
            url = f"{self.BASE_URL}/channels"
            
            async with self.session.get(url, params=params) as response:
                self.quota_manager.record_usage(1)
                
                if response.status == 200:
                    data = await response.json()
                    items = data.get('items', [])
                    
                    if items:
                        stats = items[0].get('statistics', {})
                        return int(stats.get('subscriberCount', 0))
                
                return 0
                
        except Exception as e:
            logger.error(f"채널 구독자 수 조회 실패: {e}")
            return 0
    
    def _calculate_view_velocity(self, view_count: int, upload_date: str) -> float:
        """시간당 조회수 증가량 계산"""
        try:
            if not upload_date:
                return 0.0
            
            # 업로드 시간과 현재 시간의 차이 계산
            upload_time = datetime.fromisoformat(upload_date.replace('Z', '+00:00'))
            current_time = datetime.now(upload_time.tzinfo)
            
            hours_elapsed = (current_time - upload_time).total_seconds() / 3600
            
            if hours_elapsed <= 0:
                return 0.0
            
            return view_count / hours_elapsed
            
        except Exception as e:
            logger.error(f"조회수 속도 계산 실패: {e}")
            return 0.0
    
    def _calculate_vpv_ratio(self, view_count: int, subscriber_count: int) -> float:
        """구독자 대비 조회수 비율 계산"""
        try:
            if subscriber_count <= 0:
                return 0.0
            
            return view_count / subscriber_count
            
        except Exception as e:
            logger.error(f"VPV 비율 계산 실패: {e}")
            return 0.0
    
    def _calculate_engagement_rate(self, view_count: int, like_count: int, comment_count: int) -> float:
        """참여율 계산"""
        try:
            if view_count <= 0:
                return 0.0
            
            # 결측치 처리 (-1인 경우 0으로 처리)
            likes = max(0, like_count)
            comments = max(0, comment_count)
            
            engagement = likes + comments
            return engagement / view_count
            
        except Exception as e:
            logger.error(f"참여율 계산 실패: {e}")
            return 0.0
    
    async def _get_top_comments(self, video_id: str, max_comments: int = 30) -> List[str]:
        """상위 댓글 수집"""
        try:
            api_key = self.quota_manager.get_current_api_key()
            
            params = {
                'part': 'snippet',
                'videoId': video_id,
                'maxResults': max_comments,
                'order': 'relevance',
                'key': api_key
            }
            
            url = f"{self.BASE_URL}/commentThreads"
            
            async with self.session.get(url, params=params) as response:
                self.quota_manager.record_usage(1)
                
                if response.status == 200:
                    data = await response.json()
                    comments = []
                    
                    for item in data.get('items', []):
                        comment_text = item['snippet']['topLevelComment']['snippet']['textDisplay']
                        clean_comment = self._clean_text(comment_text)
                        if clean_comment:
                            comments.append(clean_comment)
                    
                    return comments
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"댓글 수집 실패 ({video_id}): {e}")
            return []
    
    def _extract_keywords(self, description: str) -> str:
        """설명란에서 주요 키워드 추출"""
        try:
            if not description:
                return ""
            
            # 뷰티 관련 키워드만 추출
            found_keywords = []
            description_lower = description.lower()
            
            for keyword in self.BEAUTY_FILTER_KEYWORDS:
                if keyword in description_lower:
                    found_keywords.append(keyword)
            
            # 브랜드명 추출
            for keyword in self.TARGET_KEYWORDS:
                if keyword.lower() in description_lower:
                    found_keywords.append(keyword)
            
            # 중복 제거 및 정렬
            unique_keywords = list(set(found_keywords))
            return ', '.join(sorted(unique_keywords))
            
        except Exception as e:
            logger.error(f"키워드 추출 실패: {e}")
            return ""
    
    def _deduplicate_training_data(self, training_data: List[VideoTrainingData]) -> List[VideoTrainingData]:
        """중복 데이터 제거 (video_id 기준)"""
        seen_ids = set()
        unique_data = []
        
        for data in training_data:
            if data.video_id not in seen_ids:
                seen_ids.add(data.video_id)
                unique_data.append(data)
        
        return unique_data
    
    async def _save_training_dataset_csv(self, training_data: List[VideoTrainingData], target_date: str) -> str:
        """학습 데이터셋을 CSV 파일로 저장"""
        try:
            # 파일명 생성 (SRS 요구사항에 따라)
            filename = f"youtube_viral_dataset_v1_{target_date.replace('-', '')}.csv"
            csv_path = os.path.join(self.output_dir, filename)
            
            # CSV 헤더 정의 (SRS 스키마와 일치)
            fieldnames = [
                'collection_date', 'video_id', 'title', 'channel_name', 'upload_date', 'duration_sec',
                'subscriber_count', 'view_count', 'like_count', 'comment_count',
                'view_velocity', 'vpv_ratio', 'engagement_rate',
                'top_comments_text', 'description_keywords', 'is_trending_category', 'source_type'
            ]
            
            # UTF-8-SIG 인코딩으로 CSV 저장 (Excel 호환)
            with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for data in training_data:
                    # dataclass를 dict로 변환
                    row = asdict(data)
                    writer.writerow(row)
            
            # 파일 정보 로깅
            file_size = os.path.getsize(csv_path)
            logger.info(f"CSV 파일 저장 완료:")
            logger.info(f"  - 파일 경로: {csv_path}")
            logger.info(f"  - 파일 크기: {file_size:,} bytes")
            logger.info(f"  - 레코드 수: {len(training_data)}")
            
            # 데이터 품질 요약
            trending_count = sum(1 for data in training_data if data.is_trending_category == 1)
            avg_view_count = sum(data.view_count for data in training_data) / len(training_data) if training_data else 0
            avg_engagement = sum(data.engagement_rate for data in training_data) / len(training_data) if training_data else 0
            
            logger.info(f"데이터 품질 요약:")
            logger.info(f"  - 트렌딩 영상: {trending_count}/{len(training_data)} ({trending_count/len(training_data)*100:.1f}%)")
            logger.info(f"  - 평균 조회수: {avg_view_count:,.0f}")
            logger.info(f"  - 평균 참여율: {avg_engagement:.4f}")
            
            return csv_path
            
        except Exception as e:
            logger.error(f"CSV 저장 실패: {e}")
            return ""


# 사용 예시 및 테스트 함수
async def main():
    """사용 예시"""
    # 환경변수에서 API 키 로드
    api_keys_str = os.getenv("YOUTUBE_API_KEYS", "")
    api_keys = [key.strip() for key in api_keys_str.split(",") if key.strip()]
    
    if not api_keys:
        logger.error("YOUTUBE_API_KEYS 환경변수를 설정해주세요")
        return
    
    # 학습 데이터 수집기 초기화 및 실행
    async with YouTubeTrainingDataCollector(api_keys, "results") as collector:
        logger.info("YouTube 학습 데이터 수집 시작")
        
        # 오늘 날짜로 데이터셋 생성
        csv_path = await collector.collect_daily_dataset()
        
        if csv_path:
            logger.info(f"✅ 학습 데이터셋 생성 성공: {csv_path}")
            
            # 생성된 CSV 파일 미리보기
            try:
                import pandas as pd
                df = pd.read_csv(csv_path)
                logger.info(f"📊 데이터셋 미리보기:")
                logger.info(f"   - 컬럼 수: {len(df.columns)}")
                logger.info(f"   - 행 수: {len(df)}")
                logger.info(f"   - 컬럼 목록: {list(df.columns)}")
                
                if len(df) > 0:
                    logger.info(f"   - 첫 번째 레코드 제목: {df.iloc[0]['title']}")
                    logger.info(f"   - 최고 조회수: {df['view_count'].max():,}")
                    logger.info(f"   - 트렌딩 비율: {df['is_trending_category'].mean():.2%}")
                    
            except ImportError:
                logger.info("pandas가 설치되지 않아 미리보기를 건너뜁니다")
            except Exception as e:
                logger.error(f"데이터셋 미리보기 실패: {e}")
        else:
            logger.error("❌ 학습 데이터셋 생성 실패")


if __name__ == "__main__":
    asyncio.run(main())