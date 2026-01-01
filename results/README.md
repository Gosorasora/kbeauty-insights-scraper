# YouTube AI 학습용 데이터셋 결과 폴더

이 폴더에는 YouTube AI 학습용 데이터 수집 결과가 저장됩니다.

## 파일 설명

### youtube_viral_dataset_v1_{YYYYMMDD}.csv
- **설명**: 일별 YouTube AI 학습용 데이터셋
- **인코딩**: UTF-8-SIG (Excel 호환)
- **컬럼 (17개)**:
  - `collection_date`: 수집 날짜 (YYYY-MM-DD)
  - `video_id`: YouTube 영상 ID
  - `title`: 영상 제목
  - `channel_name`: 채널명
  - `upload_date`: 업로드 날짜 (ISO format)
  - `duration_sec`: 영상 길이 (초)
  - `subscriber_count`: 채널 구독자 수
  - `view_count`: 조회수
  - `like_count`: 좋아요 수
  - `comment_count`: 댓글 수
  - `view_velocity`: 시간당 조회수 증가량
  - `vpv_ratio`: 구독자 대비 조회수 비율
  - `engagement_rate`: 조회수 대비 반응율
  - `top_comments_text`: 상위 댓글 (파이프 구분)
  - `description_keywords`: 설명란 키워드 (쉼표 구분)
  - `is_trending_category`: 트렌딩 차트 진입 여부 (1/0)
  - `source_type`: 데이터 소스 타입

## 데이터 소스

1. **macro_trend**: 인기 급상승 차트 (거시 트렌드)
2. **keyword_discovery**: 키워드 검색 결과 (K-Beauty 관련)
3. **channel_performance**: 주요 뷰티 인플루언서 채널

## 데이터 수집

```bash
# 오늘 날짜로 수집
python run_training_collection.py

# 특정 날짜로 수집
python run_training_collection.py --date 2026-01-01

# 배치 수집
python run_training_collection.py --start-date 2025-12-28 --end-date 2025-12-31
```

## 데이터 분석

```bash
# 최신 파일 분석
python analyze_dataset.py

# 특정 파일 분석
python analyze_dataset.py --file youtube_viral_dataset_v1_20260101.csv

# 모든 파일 분석
python analyze_dataset.py --all
```
