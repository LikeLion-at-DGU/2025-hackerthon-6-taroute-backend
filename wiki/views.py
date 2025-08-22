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
        summary="3.3 위키 장소 검색"
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
            OpenApiParameter(name="place_id", description="장소ID", required=True, type=str),
            OpenApiParameter(name="lang", description="언어 설정", required=False, type=str, enum=["ko", "en"], default="ko")
        ],
        responses={200: WikiPlaceDetailSerializer},
        summary="3.4 장소 세부정보 - AI 요약 + 기본 정보 + 후기 (다국어 지원)"
    )
    @action(detail=False, methods=["GET"], url_path='detail')
    def place_detail(self, request):
        """장소 상세 정보 제공 - OpenAI API 활용 AI 요약 (다국어 지원)"""
        # 요청 파라미터 검증
        place_id = request.query_params.get('place_id')
        lang = request.query_params.get('lang', 'ko')  # 기본값: 한국어
        
        # 언어 유효성 검사
        if lang not in ['ko', 'en']:
            lang = 'ko'  # 잘못된 언어는 한국어로 기본 설정
            
        logger.info(f"위키 상세정보 요청 - place_id: {place_id}, lang: {lang}")
        
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
        
            # 먼저 구글맵 리뷰 크롤링 (평점 계산에 필요)
            google_review_data = {"reviews": [], "ratings": [], "average_rating": 0, "review_count": 0}
            try:
                google_review_data = google.get_google_reviews(place_id, limit=10)
                logger.info(f"구글맵 리뷰 크롤링 완료: {google_review_data['review_count']}개, 평균별점: {google_review_data['average_rating']}")
            except Exception as e:
                logger.warning(f"구글맵 리뷰 크롤링 실패 (장소: {shop_name}): {e}")

            # 평점 정보 계산 (내부 리뷰 + 크롤링된 구글맵 리뷰 별점 결합)
            reviews = Review.objects.filter(wiki_place=wiki_place)
            
            # 내부 리뷰 평점 계산
            internal_review_score = 0.00
            internal_review_count = 0
            
            if reviews.exists():
                avg_score = reviews.aggregate(avg=Avg('review_score'))['avg']
                internal_review_score = float(avg_score) if avg_score else 0.00
                internal_review_count = reviews.count()
            
            # 🔥 하이브리드 평점 시스템 (자체 우선, 5개 이하면 구글 평점과 합치기)
            print(f"🔍 [DEBUG] 하이브리드 평점 시스템 시작:")
            print(f"🔍 [DEBUG] - 내부 리뷰 개수: {internal_review_count}")
            print(f"🔍 [DEBUG] - 내부 리뷰 평점: {internal_review_score}")
            print(f"🔍 [DEBUG] - 구글맵 전체 평점: {search_details.get('rating')}")
            print(f"🔍 [DEBUG] - 크롤링된 평점: {google_review_data['average_rating']}")
            
            if internal_review_count > 5:
                # 자체 리뷰가 5개 초과면 자체 평점만 사용
                review_score = internal_review_score
                print(f"🔍 [DEBUG] - 자체 리뷰 충분 (5개 초과): 자체 평점만 사용 {review_score}")
            elif internal_review_count > 0:
                # 자체 리뷰가 1~5개면 구글 평점과 가중평균
                google_rating = search_details.get("rating", 0) or google_review_data["average_rating"]
                if google_rating > 0:
                    # 가중평균: 자체 70%, 구글 30%
                    review_score = round((internal_review_score * 0.7) + (google_rating * 0.3), 1)
                    print(f"🔍 [DEBUG] - 하이브리드 평점: 자체({internal_review_score})*0.7 + 구글({google_rating})*0.3 = {review_score}")
                else:
                    review_score = internal_review_score
                    print(f"🔍 [DEBUG] - 구글 평점 없음, 자체 평점만 사용: {review_score}")
            else:
                # 자체 리뷰가 없으면 구글 평점 사용
                review_score = search_details.get("rating", 0) or google_review_data["average_rating"] or 0.00
                print(f"🔍 [DEBUG] - 자체 리뷰 없음, 구글 평점 사용: {review_score}")

            # 게시판 리뷰 조회 (최신순/추천순)
            reviews_content = wiki_place.reviews.order_by('-created_at')
            reviews_count = wiki_place.reviews.count()
            reviews_data = WikiReviewSerializer(
                reviews_content, many=True, context={'request': request}
            ).data #직렬화

            ############################################################################################
            # 🔥 하이브리드 AI 요약 시스템 (자체 우선, 5개 이하면 구글 리뷰와 합치기)
            ai_summary = None
            review_texts = [review.review_content for review in reviews_content if review.review_content]
            
            print(f"🔍 [DEBUG] 하이브리드 AI 요약 시스템 시작:")
            print(f"🔍 [DEBUG] - 자체 리뷰 개수: {len(review_texts)}")
            print(f"🔍 [DEBUG] - 구글 리뷰 개수: {google_review_data['review_count']}")
            
            if len(review_texts) > 5:
                # 🎯 케이스 1: 자체 리뷰가 5개 초과 - 자체 리뷰만 사용
                try:
                    input_text = "\n\n".join(review_texts)
                    ai_summary = openai.openai_summary(input_text=input_text, lang=lang)
                    logger.info(f"자체 리뷰만으로 AI 요약 생성 완료 (장소: {shop_name}, {len(review_texts)}개 리뷰)")
                    print(f"🔍 [DEBUG] - 자체 리뷰만 사용한 AI 요약 생성 성공")
                except Exception as e:
                    logger.error(f"자체 리뷰 AI 요약 실패: {e}")
                    ai_summary = None
                    
            elif len(review_texts) > 0:
                # 🎯 케이스 2: 자체 리뷰 1~5개 - 구글 리뷰와 합치기
                try:
                    combined_reviews = review_texts.copy()  # 자체 리뷰 우선
                    
                    # 구글 리뷰 최대 5개 추가 (자체 리뷰 우선순위 유지)
                    google_reviews_to_add = google_review_data["reviews"][:5]
                    combined_reviews.extend(google_reviews_to_add)
                    
                    ai_summary = openai.create_crawled_reviews_summary(
                        place_name=shop_name,
                        google_reviews=combined_reviews,  # 자체 + 구글 합친 리뷰
                        blog_reviews=[],
                        lang=lang
                    )
                    logger.info(f"하이브리드 AI 요약 생성 완료 (자체: {len(review_texts)}개 + 구글: {len(google_reviews_to_add)}개)")
                    print(f"🔍 [DEBUG] - 하이브리드 요약 생성 성공 (자체:{len(review_texts)} + 구글:{len(google_reviews_to_add)})")
                    
                except Exception as e:
                    logger.error(f"하이브리드 AI 요약 실패: {e}")
                    ai_summary = None
                    
            else:
                # 🎯 케이스 3: 자체 리뷰 없음 - 구글 리뷰만 사용
                if google_review_data["reviews"]:
                    try:
                        ai_summary = openai.create_crawled_reviews_summary(
                            place_name=shop_name,
                            google_reviews=google_review_data["reviews"],
                            blog_reviews=[],
                            lang=lang
                        )
                        logger.info(f"구글맵 리뷰만으로 AI 요약 생성 완료 ({google_review_data['review_count']}개 리뷰)")
                        print(f"🔍 [DEBUG] - 구글 리뷰만 사용한 AI 요약 생성 성공")
                    except Exception as e:
                        logger.error(f"구글맵 리뷰 AI 요약 실패: {e}")
                        ai_summary = None
            
            # 3. 리뷰가 없는 경우 처리 - 다국어 친근한 메시지 표시
            if not ai_summary:
                logger.info(f"실제 리뷰 데이터가 없어 기본 메시지 표시 (장소: {shop_name}, 언어: {lang})")
                if lang == "en":
                    ai_summary = "No reviews yet! Be the first to share your experience! 🌟"
                else:
                    ai_summary = "리뷰가 아직 없습니다! 첫 리뷰의 주인공이 되어주세요! 🌟"

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
    
    # def get_popular_search_keywords(limit: int = 10) -> List[Dict]:
    #     """인기 검색 키워드 조회
        
    #     Args:
    #         limit: 반환할 키워드 개수
        
    #     Returns:
    #         인기 검색어 리스트 [{"keyword": "키워드", "count": 횟수}, ...]
    #     """
    #     from django.db.models import Count
    #     from .models import WikiSearchHistory
        
    #     # 최근 7일간의 검색 기록에서 인기 키워드 추출
    #     from datetime import timedelta
    #     recent_date = timezone.now() - timedelta(days=7)
        
    #     popular_keywords = (
    #         WikiSearchHistory.objects
    #         .filter(created_at__gte=recent_date)
    #         .values('search_query')
    #         .annotate(search_count=Count('search_query'))
    #         .order_by('-search_count')[:limit]
    #     )
        
    #     return [
    #         {
    #             "keyword": item['search_query'],
    #             "count": item['search_count']
    #         }
    #         for item in popular_keywords
    #     ]

    # @extend_schema(
    #     tags=["위키 기타"],
    #     parameters=[
    #         OpenApiParameter(name="limit", description="반환할 키워드 개수", required=False, type=int),
    #     ],
    #     responses={200: PopularKeywordSerializer(many=True)},
    #     description="인기 검색어 목록 조회"
    # )
    # @action(detail=False, methods=["GET"])
    # def popular_keywords(self, request):
    #     """인기 검색어 목록 반환"""
    #     limit = int(request.query_params.get('limit', 10))
    #     limit = min(max(limit, 1), 50)  # 1~50 범위로 제한
        
    #     try:
    #         keywords = get_popular_search_keywords(limit=limit)
    #         serializer = PopularKeywordSerializer(keywords, many=True)
    #         return Response(serializer.data, status=status.HTTP_200_OK)
    #     except Exception as e:
    #         logger.error(f"인기 검색어 조회 중 오류: {e}")
    #         return Response(
    #             {'detail': '인기 검색어 조회 중 오류가 발생했습니다.'},
    #             status=status.HTTP_500_INTERNAL_SERVER_ERROR
    #         )