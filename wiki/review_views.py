"""
Wiki 리뷰 및 신고 뷰
- 3.2.2 후기 작성 기능
- 3.2.3 후기 신고 기능
"""

from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from datetime import datetime, timedelta
from dateutil import parser
from django.utils import timezone

# from places.models import Place
from .models import WikiPlace, Review, Report
from .serializers import (
    WikiReviewSerializer,
    WikiReviewCreateSerializer,
    WikiReportSerializer,
    WikiReportCreateSerializer,
)

import logging

logger = logging.getLogger(__name__)


class WikiReviewViewSet(viewsets.ModelViewSet):
    """위키 리뷰 뷰셋 - 3.2.2 후기 작성 기능"""
    queryset = Review.objects.all()
    serializer_class = WikiReviewSerializer

    def get_serializer_class(self):
        """액션에 따른 시리얼라이저 선택"""
        if self.action == 'create':
            return WikiReviewCreateSerializer
        return WikiReviewSerializer

    # @extend_schema(
    #     tags=["위키 후기"],
    #     parameters=[
    #         OpenApiParameter(name="place_id", description="장소 ID", required=True, type=int),
    #         OpenApiParameter(name="page", description="페이지 번호", required=False, type=int),
    #         OpenApiParameter(name="size", description="페이지 크기", required=False, type=int),
    #     ],
    #     responses={200: WikiReviewSerializer(many=True)},
    #     description="3.2.2 후기 작성 - GET: 특정 장소의 후기 목록 조회"
    # )
    # @action(detail=False, methods=["GET"])
    # def by_place(self, request):
    #     """장소별 리뷰 조회"""
    #     place_id = request.query_params.get('place_id')
    #     if not place_id:
    #         return Response(
    #             {'detail': 'place_id는 필수 파라미터입니다.'},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
        
    #     try:
    #         place_id = int(place_id)
    #         # place = get_object_or_404(Place, id=place_id)
    #     except ValueError:
    #         return Response(
    #             {'detail': 'place_id는 숫자여야 합니다.'},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
        
    #     # 페이지네이션 처리
    #     page = int(request.query_params.get('page', 1))
    #     size = int(request.query_params.get('size', 10))
    #     size = min(max(size, 1), 50)  # 1~50 범위 제한
        
    #     offset = (page - 1) * size
    #     reviews = Review.objects.filter(place=place).order_by('-created_at')[offset:offset+size]
        
    #     serializer = self.get_serializer(reviews, many=True)
    #     return Response({
    #         'results': serializer.data,
    #         'meta': {
    #             'page': page,
    #             'size': size,
    #             'total_count': Review.objects.filter(place=place).count()
    #         }
    #     }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["🔥위키페이지"],
        request={'multipart/form-data': WikiReviewCreateSerializer},
        responses={201: WikiReviewSerializer},
        summary="3.2.2 후기 작성 - POST: 새로운 후기 작성 (약속, 별점, 내용)"
    )
    def create(self, request, *args, **kwargs):
        """리뷰 생성 - 약속(내용), 별점, 이미지 포함"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            with transaction.atomic():
                review = serializer.save()
                if not review.wiki_place_id:
                    raise ValueError("wiki_place가 세팅되지 않았습니다.")

                # 통계 갱신
                review.wiki_place.update_review_stats()

            # 응답용 시리얼라이저로 변환
            return Response(WikiReviewSerializer(review).data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"리뷰 생성 중 오류: {e}")
            return Response(
                {'detail': f'리뷰 작성 중 오류가 발생했습니다. {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        
    @extend_schema(
        tags=["🔥위키페이지"],
        parameters=[OpenApiParameter(name="place_id", description="장소ID", required=True, type=str)],
        summary="게시판 리뷰 좋아요 카운트"
    )
    @action(detail=True, methods=["GET"])
    def click_liked(self, request, pk=None):
        review = self.get_object()
        review.like_num += 1
        review.save(update_fields=["like_num"])
        return Response({
            "review_content": review.review_content,
            "like_count": review.like_num
        })

    @extend_schema(
        tags=["🔥위키페이지"],
        summary="현재 핫한 게시판"
    )
    @action(methods=["GET"], detail=False)
    def top7_liked(self, request):
        top_wiki = self.get_queryset().order_by("-like_num")[:7]
        top_wiki_serializer = WikiReviewSerializer(top_wiki, many=True)
        return Response(top_wiki_serializer.data)
    
    @extend_schema(
        tags=["🔥위키페이지"],
        summary="3.1 최근 업데이트된 위키"
    )
    @action(methods=["GET"], detail=False)
    def recent5_wiki(self, request):
        recent_wiki = self.get_queryset().order_by("-created_at")[:5]
        recent_wiki_serializer = WikiReviewSerializer(recent_wiki, many=True)

        recent_data = []

        for re in recent_wiki_serializer.data:
            
            # 리뷰 몇 분전 작성됐는지
            now = timezone.now()
            created= re.get('created_at')
            created_at = parser.isoparse(created)
            time_diff = now - created_at

            # 시간 차이 계산
            minutes = int(time_diff.total_seconds() // 60)
            hours = int(time_diff.total_seconds() // 3600)
            days = time_diff.days

            if days > 7:
                # 7일 이상이면 'YYYY년 MM월 DD일' 형식으로 표시
                # created_at을 로컬 타임으로 변환하여 포맷팅하는 것이 사용자에게 더 익숙합니다.
                time_text = timezone.localtime(created_at).strftime("%Y년 %m월 %d일")
            elif days > 0:
                time_text = f"{days}일 전"
            elif hours > 0:
                time_text = f"{hours}시간 전"
            elif minutes > 0:
                time_text = f"{minutes}분 전"
            else:
                time_text = "방금 전"

            recent_data.append({
                    'place_name': re.get('place_name'),
                    'review_content': re.get('review_content'),
                    'created_at': re.get('created_at'),
                    'time_text' : time_text
            })

        
        return Response({"recent_data" : recent_data})


class WikiReportViewSet(viewsets.ModelViewSet):
    """위키 신고 뷰셋 - 3.2.3 후기 신고 기능"""
    queryset = Report.objects.all()
    serializer_class = WikiReportSerializer

    def get_serializer_class(self):
        """액션에 따른 시리얼라이저 선택"""
        if self.action == 'create':
            return WikiReportCreateSerializer
        return WikiReportSerializer

    @extend_schema(
        tags=["🔥위키페이지"],
        responses={200: WikiReportSerializer(many=True)},
        summary="3.2.3 후기 신고 - GET: 신고 목록 조회 (관리자용)"
    )
    def list(self, request, *args, **kwargs):
        """신고 목록 조회 (관리자 전용)"""
        # 실제 서비스에서는 관리자 권한 체크 필요
        # if not request.user.is_staff:
        #     return Response({'detail': '관리자만 접근 가능합니다.'}, status=403)
        
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["🔥위키페이지"],
        parameters=[WikiReportCreateSerializer],
        responses={201: WikiReportSerializer},
        summary="3.2.3 후기 신고 - POST: 후기 신고 접수 (신고 사유 포함)"
    )
    def create(self, request, *args, **kwargs):
        """신고 생성 - reason, report_title, report_content 포함"""
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        try:
            # 중복 신고 방지 (같은 세션에서 같은 리뷰에 대한 신고)
            review_id = serializer.validated_data.get('review_id')
            session_key = request.session.session_key
            
            if session_key:
                # 기존 신고가 있는지 확인 (실제 구현 시 세션 기반 중복 체크)
                existing_report = Report.objects.filter(
                    review_id=review_id,
                    # session_key=session_key  # Report 모델에 session_key 필드 추가 시
                ).first()
                
                if existing_report:
                    return Response(
                        {'detail': '이미 신고한 리뷰입니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # 신고 생성
            report = serializer.save()
            response_serializer = WikiReportSerializer(report)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"신고 생성 중 오류: {e}")
            return Response(
                {'detail': '신고 접수 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
