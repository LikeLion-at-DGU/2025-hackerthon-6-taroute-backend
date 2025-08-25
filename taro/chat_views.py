"""
Taro 채팅 관련 뷰 메서드들
"""

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import TaroConversation
from .serializers import TaroChatRequestSerializer, TaroChatResponseSerializer
from .services import TaruAIService, PlaceRecommendationService

import logging
logger = logging.getLogger(__name__)


def chat_post_method(viewset_instance, request):
    """타루와의 대화 진행 - POST 메서드"""
    # 요청 데이터 유효성 검사
    body_serializer = TaroChatRequestSerializer(data=request.data)
    body_serializer.is_valid(raise_exception=True)
    
    session_key = body_serializer.validated_data["session_key"]
    input_text = body_serializer.validated_data["input_text"]
    user_latitude = body_serializer.validated_data.get("latitude")
    user_longitude = body_serializer.validated_data.get("longitude")
    meta = body_serializer.validated_data.get("meta", {})
    
    try:
        with transaction.atomic():
            # 대화 세션 가져오기 또는 생성
            conversation, created = TaroConversation.objects.select_for_update().get_or_create(
                session_key=session_key,
                defaults={
                    "conversation_stage": "greeting",
                    "user_latitude": user_latitude,
                    "user_longitude": user_longitude,
                    "conversation_history": [],
                    "user_preferences": {}
                }
            )
            
            # 위치 정보 업데이트 (제공된 경우)
            if user_latitude and user_longitude:
                conversation.user_latitude = user_latitude
                conversation.user_longitude = user_longitude
            
            # AI 서비스 초기화
            ai_service = TaruAIService()
            
            # 대화 히스토리 가져오기
            history = conversation.conversation_history or []
            
            # 첫 번째 대화인 경우 인사말 생성
            if created or conversation.conversation_stage == "greeting":
                if not history:
                    # 시스템 프롬프트 추가
                    history.append({
                        "role": "system",
                        "content": "당신은 '타루'라는 이름의 친근한 타로 AI입니다. 아키네이터처럼 질문을 통해 사용자에게 완벽한 장소를 추천합니다.",
                        "timestamp": timezone.now().isoformat()
                    })
                    
                    # 인사말 생성
                    greeting = ai_service.generate_greeting_message()
                    history.append({
                        "role": "assistant", 
                        "content": greeting,
                        "timestamp": timezone.now().isoformat()
                    })
                    
                    conversation.last_ai_response = greeting
                    conversation.conversation_stage = "questioning"
            
            # 사용자 입력 추가
            history.append({
                "role": "user",
                "content": input_text,
                "timestamp": timezone.now().isoformat(),
                "meta": meta
            })
            
            # 사용자 답변 분석 및 취향 업데이트
            if conversation.conversation_stage == "questioning":
                # 이전 AI 질문 찾기
                last_ai_message = None
                for msg in reversed(history[:-1]):  # 방금 추가한 사용자 메시지 제외
                    if msg["role"] == "assistant":
                        last_ai_message = msg["content"]
                        break
                
                if last_ai_message:
                    # 사용자 답변 분석
                    updated_preferences = ai_service.analyze_user_response(
                        question=last_ai_message,
                        answer=input_text,
                        current_preferences=conversation.user_preferences or {}
                    )
                    conversation.user_preferences = updated_preferences
            
            # 질문 수 증가
            conversation.question_count += 1
            
            # 다음 응답 생성
            output_text = ""
            
            if conversation.question_count >= conversation.max_questions or "충분" in input_text.lower():
                # 질문 단계 완료 - 추천 준비
                conversation.conversation_stage = "analyzing"
                
                # 장소 추천 서비스 초기화
                if user_latitude and user_longitude:
                    recommendation_service = PlaceRecommendationService()
                    recommended_places = recommendation_service.search_places_by_preferences(
                        user_preferences=conversation.user_preferences or {},
                        user_latitude=user_latitude,
                        user_longitude=user_longitude
                    )
                    
                    # 추천 요약 메시지 생성
                    output_text = ai_service.generate_recommendation_summary(
                        user_preferences=conversation.user_preferences or {},
                        recommended_places=recommended_places[:25]
                    )
                    
                    conversation.conversation_stage = "recommending"
                else:
                    output_text = "위치 정보가 필요해요. 현재 위치를 알려주시면 맞춤형 장소를 추천해드릴 수 있어요! 🗺️"
            
            else:
                # 계속 질문 생성
                output_text = ai_service.generate_question(
                    conversation_history=history,
                    question_count=conversation.question_count,
                    user_preferences=conversation.user_preferences or {}
                )
            
            # AI 응답 추가
            history.append({
                "role": "assistant",
                "content": output_text,
                "timestamp": timezone.now().isoformat()
            })
            
            # 대화 히스토리 길이 제한 (최근 100개만 유지)
            conversation.conversation_history = history[-100:]
            conversation.last_ai_response = output_text
            
            # 저장
            conversation.save(update_fields=[
                "conversation_stage",
                "question_count", 
                "user_latitude",
                "user_longitude",
                "conversation_history",
                "user_preferences",
                "last_ai_response",
                "updated_at"
            ])
        
        # 응답 구성
        response_data = {
            "output_text": output_text,
            "conversation_stage": conversation.conversation_stage,
            "question_count": conversation.question_count,
            "max_questions": conversation.max_questions,
            "can_draw_cards": conversation.can_draw_cards(),
            "is_conversation_complete": conversation.is_conversation_complete()
        }
        
        response_serializer = TaroChatResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"타루 대화 처리 중 오류: {e}")
        return Response({
            "error": "대화 처리 중 오류가 발생했습니다.",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

