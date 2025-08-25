"""
OpenAI API 없이 크롤링 데이터만 확인하는 임시 테스트
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .service import google

logger = logging.getLogger(__name__)


class CrawlingOnlyTestViewSet(viewsets.ViewSet):
    """AI 요약 없이 크롤링 데이터만 확인하는 테스트 뷰셋"""
    
    @extend_schema(
        tags=["🔧디버깅"],
        parameters=[
            OpenApiParameter(name="place_id", description="구글 Place ID", required=True, type=str),
            OpenApiParameter(name="place_name", description="장소명", required=True, type=str),
        ],
        summary="크롤링 데이터만 확인 (AI 요약 제외)"
    )
    @action(detail=False, methods=["GET"])
    def test_crawling_data_only(self, request):
        """크롤링 데이터만 확인 - OpenAI API 사용 안함"""
        place_id = request.query_params.get('place_id')
        place_name = request.query_params.get('place_name')
        
        if not place_id or not place_name:
            return Response(
                {"error": "place_id와 place_name 파라미터가 모두 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 1. 구글맵 리뷰만 크롤링
            logger.info(f"구글맵 리뷰 크롤링 시작 (place_id: {place_id})")
            google_review_data = google.get_google_reviews(place_id, limit=10)
            
            # 2. AI 요약 없이 데이터만 반환
            return Response({
                "place_id": place_id,
                "place_name": place_name,
                "google_review_count": google_review_data["review_count"],
                "google_reviews": google_review_data["reviews"],
                "google_average_rating": google_review_data["average_rating"],  # 구글맵 평균 별점 추가
                "total_reviews": google_review_data["review_count"],
                "message": "구글맵 리뷰 수집 완료 (AI 요약 제외)",
                "is_real_data": True,
                "no_ai_summary": "OpenAI API 할당량 절약을 위해 AI 요약 제외",
                "no_blog_reviews": "블로그 리뷰는 제외, 구글맵 리뷰만 사용",
                "crawling_success": True
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"크롤링 테스트 실패: {e}")
            return Response(
                {"error": f"크롤링 실패: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
