"""
Taro 앱 뷰 - 타루 대화 및 카드 뽑기 기능
"""

import uuid
import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from places.models import Place
from .models import TaroConversation, TaroCard, TaroCartItem
from .serializers import (
    TaroChatQuerySerializer,
    TaroChatRequestSerializer,
    TaroChatResponseSerializer,
    TaroCardSerializer,
    TaroCardShuffleQuerySerializer,
    TaroCardRedrawQuerySerializer,
    TaroCardSelectSerializer,
    TaroCartItemSerializer,
    TaroCartQuerySerializer,
)
from .services import TaruAIService, PlaceRecommendationService, calculate_distance_km

logger = logging.getLogger(__name__)


class TaroViewSet(viewsets.GenericViewSet):
    """타로 메인 뷰셋 - 타루와의 대화, 카드 뽑기, 장바구니 관리"""
    
    queryset = TaroConversation.objects.all()
    serializer_class = TaroChatResponseSerializer  # 기본 시리얼라이저 설정

    @extend_schema(
        tags=["타루 대화"],
        parameters=[
            OpenApiParameter(name="session_key", description="세션 키", required=True, type=str),
            OpenApiParameter(name="limit", description="최근 N개 대화", required=False, type=int),
        ],
        responses={200: None},
        description="4.1.1 질문 - GET: 최근 대화 히스토리 조회"
    )
    @action(detail=False, methods=["GET"])
    def chat(self, request):
        """타루와의 대화 히스토리 조회"""
        query_serializer = TaroChatQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        
        session_key = query_serializer.validated_data["session_key"]
        limit = query_serializer.validated_data["limit"]
        
        conversation = TaroConversation.objects.filter(
            session_key=session_key
        ).order_by("-updated_at").first()
        
        if not conversation:
            return Response({
                "conversation_history": [],
                "conversation_stage": "greeting",
                "question_count": 0,
                "max_questions": 20
            }, status=status.HTTP_200_OK)
        
        history = conversation.conversation_history or []
        recent_history = history[-limit:] if limit < len(history) else history
        
        return Response({
            "conversation_history": recent_history,
            "conversation_stage": conversation.conversation_stage,
            "question_count": conversation.question_count,
            "max_questions": conversation.max_questions,
            "can_draw_cards": conversation.can_draw_cards(),
            "is_conversation_complete": conversation.is_conversation_complete()
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["타루 대화"],
        request=TaroChatRequestSerializer,
        responses={200: TaroChatResponseSerializer},
        description="4.1.1 질문 - POST: 타루와의 대화 진행 (아키네이터 스타일)"
    )
    @chat.mapping.post
    def chat_post(self, request):
        """타루와의 대화 진행"""
        from .chat_views import chat_post_method
        return chat_post_method(self, request)

    @extend_schema(
        tags=["타로 카드"],
        parameters=[
            OpenApiParameter(name="session_key", description="세션 키", required=True, type=str),
        ],
        responses={200: TaroCardSerializer(many=True)},
        description="4.2.1 카드 셔플 & 드로우 - 대화 기반 장소카드 25장 추천"
    )
    @action(detail=False, methods=["GET"])
    def shuffle(self, request):
        """카드 셔플 & 드로우"""
        query_serializer = TaroCardShuffleQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        
        session_key = query_serializer.validated_data["session_key"]
        
        try:
            conversation = get_object_or_404(TaroConversation, session_key=session_key)
            
            if not conversation.can_draw_cards():
                return Response({
                    "error": "카드 뽑기 횟수를 초과했습니다."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if conversation.conversation_stage not in ["recommending", "completed"]:
                return Response({
                    "error": "아직 대화가 충분히 진행되지 않았습니다."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not (conversation.user_latitude and conversation.user_longitude):
                return Response({
                    "error": "위치 정보가 필요합니다."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                recommendation_service = PlaceRecommendationService()
                recommended_places = recommendation_service.search_places_by_preferences(
                    user_preferences=conversation.user_preferences or {},
                    user_latitude=conversation.user_latitude,
                    user_longitude=conversation.user_longitude
                )
                
                selected_places = recommendation_service.select_diverse_cards(
                    places=recommended_places, count=25
                )
                
                current_draw = conversation.card_draw_count + 1
                TaroCard.objects.filter(
                    conversation=conversation, draw_round=current_draw
                ).delete()
                
                cards = []
                for i, place_data in enumerate(selected_places, 1):
                    distance_km = calculate_distance_km(
                        conversation.user_latitude, conversation.user_longitude,
                        place_data.get('latitude', 0), place_data.get('longitude', 0)
                    )
                    
                    card_id = f"{session_key[:8]}-{current_draw}-{i:02d}"
                    
                    card = TaroCard.objects.create(
                        conversation=conversation,
                        card_id=card_id,
                        place_name=place_data['name'],
                        distance=f"{distance_km}km",
                        category=place_data.get('category', '기타'),
                        address=place_data.get('address', ''),
                        road_address=place_data.get('road_address', ''),
                        phone=place_data.get('phone', ''),
                        recommendation_reason=f"취향 점수: {place_data.get('score', 0):.1f}/10",
                        card_position=i,
                        draw_round=current_draw,
                        kakao_place_id=place_data.get('kakao_id', ''),
                        latitude=place_data.get('latitude'),
                        longitude=place_data.get('longitude')
                    )
                    cards.append(card)
                
                conversation.card_draw_count = current_draw
                conversation.conversation_stage = "completed"
                conversation.save(update_fields=["card_draw_count", "conversation_stage", "updated_at"])
            
            serializer = TaroCardSerializer(cards, many=True)
            return Response({
                "cards": serializer.data,
                "total_cards": len(cards),
                "can_redraw": conversation.can_draw_cards()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"카드 셔플 중 오류: {e}")
            return Response({
                "error": "카드 생성 중 오류가 발생했습니다."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        tags=["타로 카드"],
        parameters=[
            OpenApiParameter(name="session_key", description="세션 키", required=True, type=str),
        ],
        responses={200: TaroCardSerializer(many=True)},
        description="4.2.2 카드 다시 뽑기 - 1회 제한"
    )
    @action(detail=False, methods=["GET"])
    def redraw(self, request):
        """카드 다시 뽑기 (1회 제한)"""
        query_serializer = TaroCardRedrawQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        
        session_key = query_serializer.validated_data["session_key"]
        
        try:
            conversation = get_object_or_404(TaroConversation, session_key=session_key)
            
            if not conversation.can_draw_cards():
                return Response({
                    "error": "다시 뽑기는 1회만 가능합니다."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if conversation.card_draw_count == 0:
                return Response({
                    "error": "먼저 카드를 뽑아주세요."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # shuffle 메서드와 동일한 로직으로 다시 뽑기
            return self.shuffle(request)
            
        except Exception as e:
            logger.error(f"카드 다시 뽑기 중 오류: {e}")
            return Response({
                "error": "카드 다시 뽑기 중 오류가 발생했습니다."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        tags=["타로 카드"],
        request=TaroCardSelectSerializer,
        responses={200: TaroCartItemSerializer},
        description="4.2.3 카드 선택 - 선택된 카드는 장바구니로 이동"
    )
    @action(detail=False, methods=["POST"])
    def pick(self, request):
        """카드 선택 - 장바구니에 추가"""
        body_serializer = TaroCardSelectSerializer(data=request.data)
        body_serializer.is_valid(raise_exception=True)
        
        session_key = body_serializer.validated_data["session_key"]
        card_id = body_serializer.validated_data["card_id"]
        selection_note = body_serializer.validated_data.get("selection_note", "")
        priority = body_serializer.validated_data.get("priority", 5)
        
        try:
            card = get_object_or_404(TaroCard, card_id=card_id)
            
            # 세션 키 확인
            if card.conversation.session_key != session_key:
                return Response({
                    "error": "잘못된 세션입니다."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 중복 선택 방지
            cart_item, created = TaroCartItem.objects.get_or_create(
                session_key=session_key,
                card=card,
                defaults={
                    "selection_note": selection_note,
                    "priority": priority
                }
            )
            
            if not created:
                # 이미 선택된 카드인 경우 메모와 우선순위 업데이트
                cart_item.selection_note = selection_note
                cart_item.priority = priority
                cart_item.save(update_fields=["selection_note", "priority"])
            
            serializer = TaroCartItemSerializer(cart_item)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"카드 선택 중 오류: {e}")
            return Response({
                "error": "카드 선택 중 오류가 발생했습니다."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        tags=["타로 장바구니"],
        parameters=[
            OpenApiParameter(name="session_key", description="세션 키", required=True, type=str),
        ],
        responses={200: TaroCartItemSerializer(many=True)},
        description="장바구니 조회"
    )
    @action(detail=False, methods=["GET"])
    def cart(self, request):
        """장바구니 조회"""
        query_serializer = TaroCartQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        
        session_key = query_serializer.validated_data["session_key"]
        
        cart_items = TaroCartItem.objects.filter(
            session_key=session_key
        ).order_by('-priority', '-created_at')
        
        serializer = TaroCartItemSerializer(cart_items, many=True)
        return Response({
            "cart_items": serializer.data,
            "total_items": len(cart_items)
        }, status=status.HTTP_200_OK)
