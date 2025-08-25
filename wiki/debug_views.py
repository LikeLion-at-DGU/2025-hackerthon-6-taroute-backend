"""
디버깅용 뷰 - 크롤링 리뷰 수집 테스트
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .service import google
from .service.openai import create_crawled_reviews_summary

logger = logging.getLogger(__name__)


class ReviewCrawlerDebugViewSet(viewsets.ViewSet):
    """크롤링 리뷰 수집 디버깅용 뷰셋"""
    
    @extend_schema(
        tags=["🔧디버깅"],
        parameters=[
            OpenApiParameter(name="place_id", description="구글 Place ID", required=True, type=str),
        ],
        summary="구글맵 리뷰 크롤링 테스트"
    )
    @action(detail=False, methods=["GET"])
    def test_google_reviews(self, request):
        """구글맵에서 실제 리뷰를 크롤링하는지 테스트"""
        place_id = request.query_params.get('place_id')
        
        if not place_id:
            return Response(
                {"error": "place_id 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            reviews = google.get_google_reviews(place_id, limit=5)
            
            return Response({
                "place_id": place_id,
                "review_count": len(reviews),
                "reviews": reviews,
                "message": f"구글맵에서 {len(reviews)}개의 실제 리뷰를 수집했습니다."
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"구글 리뷰 크롤링 테스트 실패: {e}")
            return Response(
                {"error": f"구글 리뷰 크롤링 실패: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

    
    @extend_schema(
        tags=["🔧디버깅"],
        parameters=[
            OpenApiParameter(name="place_id", description="구글 Place ID", required=True, type=str),
            OpenApiParameter(name="place_name", description="장소명", required=True, type=str),
        ],
        summary="구글맵 리뷰 크롤링 + AI 요약 테스트"
    )
    @action(detail=False, methods=["GET"])
    def test_full_crawling_summary(self, request):
        """구글맵 리뷰 크롤링 + AI 요약 전체 프로세스 테스트"""
        place_id = request.query_params.get('place_id')
        place_name = request.query_params.get('place_name')
        
        if not place_id or not place_name:
            return Response(
                {"error": "place_id와 place_name 파라미터가 모두 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 1. 구글맵 리뷰 크롤링
            logger.info(f"구글맵 리뷰 크롤링 시작 (place_id: {place_id})")
            google_review_data = google.get_google_reviews(place_id, limit=10)
            
            # 2. AI 요약 생성
            ai_summary = None
            if google_review_data["reviews"]:
                logger.info(f"AI 요약 생성 시작 (구글 리뷰: {google_review_data['review_count']}개)")
                ai_summary = create_crawled_reviews_summary(
                    place_name=place_name,
                    google_reviews=google_review_data["reviews"],  # 리뷰 텍스트만 전달
                    blog_reviews=[]  # 빈 리스트로 전달
                )
            
            # 3. 리뷰가 없는 경우 기본 메시지
            is_default_message = False
            if not ai_summary:
                ai_summary = "리뷰가 아직 없습니다! 첫 리뷰의 주인공이 되어주세요! 🌟"
                is_default_message = True
            
            return Response({
                "place_id": place_id,
                "place_name": place_name,
                "google_review_count": google_review_data["review_count"],
                "google_reviews": google_review_data["reviews"],
                "google_average_rating": google_review_data["average_rating"],  # 구글맵 평균 별점 추가
                "ai_summary": ai_summary,
                "is_ai_generated": not is_default_message,  # AI가 생성한 요약인지 여부
                "is_default_message": is_default_message,   # 기본 메시지인지 여부
                "message": "구글맵 리뷰 크롤링 + AI 요약 테스트 완료",
                "is_real_data": True,  # 실제 데이터임을 명시
                "no_blog_reviews": "블로그 리뷰는 제외, 구글맵 리뷰만 사용"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"구글맵 크롤링 테스트 실패: {e}")
            return Response(
                {"error": f"크롤링 테스트 실패: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
