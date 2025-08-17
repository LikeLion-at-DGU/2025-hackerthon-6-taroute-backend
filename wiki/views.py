"""
Wiki 앱 뷰 - 메인 검색 및 정보 안내
"""

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from places.models import Place
from .models import WikiPlace, WikiSearchHistory, Review, Report
from .serializers import (
    WikiSearchQuerySerializer,
    WikiPlaceSearchResultSerializer, 
    WikiPlaceDetailSerializer,
    WikiReviewSerializer,
    WikiReviewCreateSerializer,
    WikiReportSerializer,
    WikiReportCreateSerializer,
    PopularKeywordSerializer
)
from .services import (
    search_places_by_keyword,
    parse_kakao_place_data,
    generate_ai_summary,
    # calculate_distance,
    get_popular_search_keywords
)

from .service import google

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
            
                
            #     # 기존 Place 모델에서 해당 장소 찾기 (좌표 기반)
            #     existing_place = None
            #     try:
            #         # 좌표가 비슷한 기존 장소 찾기 (오차 허용 범위: 0.001도 약 100m)
            #         existing_place = Place.objects.filter(
            #             longitude__range=(place_data['longitude'] - 0.001, place_data['longitude'] + 0.001),
            #             latitude__range=(place_data['latitude'] - 0.001, place_data['latitude'] + 0.001)
            #         ).first()
            #     except Exception as e:
            #         logger.warning(f"기존 장소 검색 중 오류: {e}")
                
            #     # WikiPlace 조회
            #     wiki_place = None
            #     if existing_place:
            #         try:
            #             wiki_place = WikiPlace.objects.get(place=existing_place)
            #         except WikiPlace.DoesNotExist:
            #             pass
                
            #     # 평점 정보 계산
            #     review_score = 0.00
            #     if wiki_place:
            #         review_score = wiki_place.average_review_score
            #     elif existing_place:
            #         # 실시간 평점 계산
            #         reviews = Review.objects.filter(place=existing_place)
            #         if reviews.exists():
            #             from django.db.models import Avg
            #             avg_score = reviews.aggregate(avg=Avg('review_score'))['avg']
            #             review_score = float(avg_score) if avg_score else 0.00
                
            
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
        tags=["위키 정보 안내"],
        parameters=[
            OpenApiParameter(name="place_name", description="장소명", required=True, type=str),
            OpenApiParameter(name="location_name", description="지역명", required=False, type=str),
            OpenApiParameter(name="longitude", description="경도", required=True, type=float),
            OpenApiParameter(name="latitude", description="위도", required=True, type=float),
        ],
        responses={200: WikiPlaceDetailSerializer},
        description="3.2.1 결과 화면 - AI 요약 + 기본 정보 + 후기"
    )
    @action(detail=False, methods=["GET"], url_path='detail')
    def place_detail(self, request):
        """장소 상세 정보 제공 - OpenAI API 활용 AI 요약"""
        # 요청 파라미터 검증
        place_name = request.query_params.get('place_name')
        location_name = request.query_params.get('location_name', '')
        longitude = request.query_params.get('longitude')
        latitude = request.query_params.get('latitude')
        
        if not all([place_name, longitude, latitude]):
            return Response(
                {'detail': 'place_name, longitude, latitude는 필수 파라미터입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            longitude = float(longitude)
            latitude = float(latitude)
        except ValueError:
            return Response(
                {'detail': '경도와 위도는 숫자여야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 기존 Place 또는 WikiPlace 찾기
            place = None
            wiki_place = None
            
            # 좌표 기반으로 기존 장소 찾기
            place = Place.objects.filter(
                longitude__range=(longitude - 0.001, longitude + 0.001),
                latitude__range=(latitude - 0.001, latitude + 0.001)
            ).first()
            
            # WikiPlace 찾기 또는 생성
            if place:
                wiki_place, created = WikiPlace.objects.get_or_create(
                    place=place,
                    defaults={
                        'shop_name': place_name,
                        'kakao_place_id': '',  # 검색에서 온 경우 별도 업데이트 필요
                    }
                )
            else:
                # 새 Place 생성
                with transaction.atomic():
                    place = Place.objects.create(
                        name=place_name,
                        address=location_name,
                        dong='',  # 별도 API 호출로 채울 수 있음
                        longitude=longitude,
                        latitude=latitude,
                        number='',
                        running_time=''
                    )
                    
                    wiki_place = WikiPlace.objects.create(
                        place=place,
                        shop_name=place_name
                    )
            
            # 리뷰 데이터 수집
            reviews = Review.objects.filter(place=place).order_by('-created_at')[:10]
            review_texts = [review.review_content for review in reviews if review.review_content]
            
            # AI 요약 생성 (아직 없거나 오래된 경우)
            should_generate_ai_summary = (
                not wiki_place.ai_summation or
                not wiki_place.ai_summary_updated_at or
                (timezone.now() - wiki_place.ai_summary_updated_at).days > 30
            )
            
            if should_generate_ai_summary:
                try:
                    ai_summary, ai_metadata = generate_ai_summary(
                        place_name=place_name,
                        reviews=review_texts,
                        basic_info=wiki_place.basic_information
                    )
                    
                    # AI 요약 정보 업데이트
                    wiki_place.ai_summation = ai_summary
                    wiki_place.ai_summation_info = ai_metadata
                    wiki_place.ai_summary_updated_at = timezone.now()
                    wiki_place.save(update_fields=[
                        'ai_summation', 
                        'ai_summation_info', 
                        'ai_summary_updated_at'
                    ])
                    
                except Exception as e:
                    logger.warning(f"AI 요약 생성 실패: {e}")
                    # AI 요약 생성 실패해도 다른 정보는 제공
                    if not wiki_place.ai_summation:
                        wiki_place.ai_summation = f"{place_name}에 대한 정보를 제공합니다."
            
            # 기본 정보 구성 (없는 경우)
            if not wiki_place.basic_information:
                basic_info_parts = []
                if place.running_time:
                    basic_info_parts.append(f"운영시간: {place.running_time}")
                if place.number:
                    basic_info_parts.append(f"전화번호: {place.number}")
                if place.address:
                    basic_info_parts.append(f"주소: {place.address}")
                
                wiki_place.basic_information = '\n'.join(basic_info_parts) or "기본 정보가 없습니다."
                wiki_place.basic_information_info = {
                    'generated_at': timezone.now().isoformat(),
                    'source': 'internal_data'
                }
                wiki_place.save(update_fields=['basic_information', 'basic_information_info'])
            
            # 리뷰 통계 업데이트
            wiki_place.update_review_stats()
            
            # 리뷰 데이터 직렬화
            review_data = []
            for review in reviews:
                review_data.append({
                    'id': review.id,
                    'content': review.review_content,
                    'score': float(review.review_score),
                    'created_at': review.created_at.isoformat(),
                    'ai_review': review.ai_review,
                })
            
            # 응답 데이터 구성
            response_data = {
                'place_name': place_name,
                'location_name': location_name or place.address,
                'longitude': longitude,
                'latitude': latitude,
                'shop_name': wiki_place.shop_name or place_name,
                'shop_image': wiki_place.shop_image.url if wiki_place.shop_image else None,
                'ai_summation': wiki_place.ai_summation,
                'ai_summation_info': wiki_place.ai_summation_info,
                'basic_information': wiki_place.basic_information,
                'basic_information_info': wiki_place.basic_information_info,
                'reviews': review_data,
                'average_review_score': float(wiki_place.average_review_score),
                'total_review_count': wiki_place.total_review_count,
            }
            
            serializer = WikiPlaceDetailSerializer(response_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"위키 상세 정보 조회 중 오류: {e}")
            return Response(
                {'detail': f'정보 조회 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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