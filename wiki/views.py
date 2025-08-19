"""
Wiki 앱 뷰 - 메인 검색 및 정보 안내
"""

from datetime import timezone
from django.shortcuts import get_object_or_404
# from django.db import transaction
# from django.utils import timezone
from django.db.models import Avg

import requests
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

# from places.models import Place
from .models import WikiPlace, WikiSearchHistory, Review, Report
from .serializers import (
    WikiSearchQuerySerializer,
    WikiPlaceSearchResultSerializer, 
    WikiPlaceDetailSerializer,
    WikiReviewSerializer,
    PopularKeywordSerializer
)
from typing import List, Dict, Optional, Tuple
# from .services import (
#     # search_places_by_keyword,
#     # parse_kakao_place_data,
#     get_popular_search_keywords
# )

from .service import google, openai

import logging

logger = logging.getLogger(__name__)


class WikiViewSet(viewsets.GenericViewSet):
    """위키 메인 뷰셋 - 장소 검색, 상세 정보, 인기 검색어"""
    queryset = WikiPlace.objects.all()

    @extend_schema(
        tags=["🔥위키페이지"],
        parameters=[WikiSearchQuerySerializer],
        responses={200: WikiPlaceSearchResultSerializer(many=True)},
        summary="3.1 위키 검색 - 장소 및 지역 검색 가능 → 핫한 장소, 지역 안내"
    )
    @action(detail=False, methods=["GET"])
    def search(self, request):
        """위키 검색 기능 - 카카오 -> 구글 API 활용"""
        # 요청 파라미터 유효성 검사
        query_serializer = WikiSearchQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        
        search_data = query_serializer.validated_data
        
        try:
            # 구글 API 호출
            google_places = google.search_place(**search_data)
                        
            # # 검색 기록 저장 (세션 키가 있는 경우)
            # if session_key:
            #     try:
            #         search_type = 'mixed'
            #         if place_name and not location_name:
            #             search_type = 'place_name'
            #         elif location_name and not place_name:
            #             search_type = 'location_name'
                    
            #         WikiSearchHistory.objects.create(
            #             search_query=search_query,
            #             search_type=search_type,
            #             result_count=len(search_results),
            #             session_key=session_key,
            #             search_longitude=user_longitude,
            #             search_latitude=user_latitude
            #         )
            #     except Exception as e:
            #         logger.warning(f"검색 기록 저장 실패: {e}")
        

            
        except Exception as e:
            logger.error(f"위키 검색 중 오류: {e}")
            return Response(
                {'detail': f'검색 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
        return Response({"google_place" : google_places}, status=200)

    @extend_schema(
        tags=["🔥위키페이지"],
        parameters=[
            OpenApiParameter(name="place_id", description="장소ID", required=True, type=str)
        ],
        responses={200: WikiPlaceDetailSerializer},
        summary="3.2.1 결과 화면 - AI 요약 + 기본 정보 + 후기"
    )
    @action(detail=False, methods=["GET"], url_path='detail')
    def place_detail(self, request):
        """장소 상세 정보 제공 - OpenAI API 활용 AI 요약"""
        # 요청 파라미터 검증
        place_id = request.query_params.get('place_id')
        
        if not place_id:
            return Response(
                {'detail': 'place_id는 필수 파라미터입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ai_summary = None
        try:
            search_details = google.search_detail(place_id=place_id) 
            shop_name =search_details.get("place_name")  
        
            # ID에 해당하는 위키 모델의 별점에 접근
            # WikiPlace 조회
            wiki_place = None
            
            
            wiki_place, created = WikiPlace.objects.get_or_create(
                google_place_id = place_id,
                defaults={
                    'shop_name': shop_name
                }
            )

            if not created: #등록은 됐는데 이름이 비어있다면! 리뷰 먼저 쓴 경우.. 디버깅용.
                if shop_name and not (wiki_place.shop_name and wiki_place.shop_name.strip()):
                    wiki_place.shop_name = shop_name
                    wiki_place.save(update_fields=["shop_name"])
        

            # 평점 정보 계산
            reviews = Review.objects.filter(wiki_place=wiki_place)
            review_score = 0.00
            if wiki_place:
                review_score = wiki_place.average_review_score
            else:
                # 실시간 평점 계산
                if reviews.exists():
                    avg_score = reviews.aggregate(avg=Avg('review_score'))['avg']
                    review_score = float(avg_score) if avg_score else 0.00
                else:
                    review_score = search_details.get("rating") #없다면 구글 평점

            # 게시판 리뷰 조회 (최신순/추천순)
            reviews_content = wiki_place.reviews.order_by('-created_at')
            reviews_count = wiki_place.reviews.count()
            reviews_data = WikiReviewSerializer(
                reviews_content, many=True, context={'request': request}
            ).data #직렬화

            ############################################################################################
            # 리뷰 데이터 수집
            review_texts = [reviews.review_content for reviews in reviews_content if reviews.review_content]
            input_text = "\n\n".join(review_texts) #리스트를 문자열로 합침

            if review_texts:
                try:
                    ai_summary = openai.openai_summary(input_text = input_text)
                
                except requests.HTTPError as e:
                    status_code = e.response.status_code if e.response else "NoStatus"
                    detail = e.response.text if e.response else str(e)
                    return Response(
                        {"detail": f"OpenAI API 호출 실패: {status_code} - {detail}"},
                        status=502
                    )
                except requests.RequestException as e:
                    return Response({"detail": f"openAI API 호출 실패(네트워크): {e}"}, status=502)

        except Exception as e:
            logger.error(f"위키 상세 정보 조회 중 오류: {e}")
            return Response(
                {'detail': f'정보 조회 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(
            {
                "search_detail":search_details, # 구글 api 조회
                "average_review_score":review_score, # 위키별점
                "ai_summary": ai_summary, # AI요약
                'reviews_count':reviews_count,
                "reviews_content":reviews_data
            }, 
            status=200

        # AI 요약 생성 (아직 없거나 오래된 경우)
        # should_generate_ai_summary = (
        #     not wiki_place.ai_summation or
        #     not wiki_place.ai_summary_updated_at or
        #     (timezone.now() - wiki_place.ai_summary_updated_at).days > 30
        # )
    
        
        )
    
    def get_popular_search_keywords(limit: int = 10) -> List[Dict]:
        """인기 검색 키워드 조회
        
        Args:
            limit: 반환할 키워드 개수
        
        Returns:
            인기 검색어 리스트 [{"keyword": "키워드", "count": 횟수}, ...]
        """
        from django.db.models import Count
        from .models import WikiSearchHistory
        
        # 최근 7일간의 검색 기록에서 인기 키워드 추출
        from datetime import timedelta
        recent_date = timezone.now() - timedelta(days=7)
        
        popular_keywords = (
            WikiSearchHistory.objects
            .filter(created_at__gte=recent_date)
            .values('search_query')
            .annotate(search_count=Count('search_query'))
            .order_by('-search_count')[:limit]
        )
        
        return [
            {
                "keyword": item['search_query'],
                "count": item['search_count']
            }
            for item in popular_keywords
        ]

    @extend_schema(
        tags=["위키 기타"],
        parameters=[
            OpenApiParameter(name="limit", description="반환할 키워드 개수", required=False, type=int),
        ],
        responses={200: PopularKeywordSerializer(many=True)},
        description="인기 검색어 목록 조회"
    )
    @action(detail=False, methods=["GET"])
    def popular_keywords(self, request):
        """인기 검색어 목록 반환"""
        limit = int(request.query_params.get('limit', 10))
        limit = min(max(limit, 1), 50)  # 1~50 범위로 제한
        
        try:
            keywords = get_popular_search_keywords(limit=limit)
            serializer = PopularKeywordSerializer(keywords, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"인기 검색어 조회 중 오류: {e}")
            return Response(
                {'detail': '인기 검색어 조회 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )