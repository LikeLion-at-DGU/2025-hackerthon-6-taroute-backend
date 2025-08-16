"""
Wiki 앱 URL 설정
- 위키 검색, 장소 정보, 리뷰, 신고 관련 API 엔드포인트
"""

from django.urls import path, include
from rest_framework import routers
from django.conf import settings
from django.conf.urls.static import static

from .views import WikiViewSet
from .review_views import WikiReviewViewSet, WikiReportViewSet

app_name = "wiki"

# 메인 위키 라우터 (검색, 상세정보)
wiki_router = routers.SimpleRouter(trailing_slash=False)
wiki_router.register("wiki", WikiViewSet, basename="wiki")

# 리뷰 라우터
review_router = routers.SimpleRouter(trailing_slash=False)
review_router.register("reviews", WikiReviewViewSet, basename="wiki-reviews")

# 신고 라우터  
report_router = routers.SimpleRouter(trailing_slash=False)
report_router.register("reports", WikiReportViewSet, basename="wiki-reports")

urlpatterns = [
    # 위키 메인 기능 (검색, 상세정보, 인기검색어)
    # GET /wiki/search - 3.1 위키 검색
    # GET /wiki/detail - 3.2.1 결과 화면 (정보 안내)  
    # GET /wiki/popular_keywords - 인기 검색어
    path("", include(wiki_router.urls)),
    
    # 리뷰 기능
    # GET /reviews/by_place - 3.2.2 후기 조회
    # POST /reviews - 3.2.2 후기 작성
    path("", include(review_router.urls)),
    
    # 신고 기능
    # GET /reports - 3.2.3 신고 목록 조회 (관리자용)
    # POST /reports - 3.2.3 후기 신고
    path("", include(report_router.urls)),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

"""
API 엔드포인트 정리:

### 3.1 위키 검색
GET /wiki/search
- 파라미터: place_name, location_name, longitude, latitude, radius, page, size, session_key
- 응답: 검색 결과 리스트 (place_name, location_name, longitude, latitude, place_location, review_score)

### 3.2.1 결과 화면 - 정보 안내  
GET /wiki/detail
- 파라미터: place_name, location_name, longitude, latitude
- 응답: AI 요약 + 기본 정보 + 후기 (shop_name, shop_image, AI_summation, AI_summation_info, basic_information, basic_information_info, reviews)

### 3.2.2 후기 작성
GET /reviews/by_place
- 파라미터: place_id, page, size
- 응답: 리뷰 목록 (reviews, reviews_score)

POST /reviews  
- 요청: place_id, review_content, review_score, review_image
- 응답: 생성된 리뷰 정보

### 3.2.3 후기 신고
GET /reports (관리자용)
- 응답: 신고 목록

POST /reports
- 요청: review_id, reason, report_title, report_content  
- 응답: 생성된 신고 정보

### 기타
GET /wiki/popular_keywords
- 파라미터: limit
- 응답: 인기 검색어 목록
"""
