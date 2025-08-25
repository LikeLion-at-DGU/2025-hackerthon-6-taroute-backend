"""
Taro 앱 시리얼라이저
- 타루 대화, 카드 뽑기, 장바구니 관련 시리얼라이저
"""

from rest_framework import serializers
from .models import TaroConversation, TaroCard, TaroCartItem, TaroQuestionTemplate


class TaroChatQuerySerializer(serializers.Serializer):
    """타루 대화 조회 파라미터 시리얼라이저"""
    
    session_key = serializers.CharField(
        max_length=64,
        #"사용자 세션 키"
    )
    
    limit = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=50,
        default=20,
        #"가져올 대화 수"
    )


class TaroChatRequestSerializer(serializers.Serializer):
    """타루 대화 요청 시리얼라이저"""
    
    session_key = serializers.CharField(
        max_length=64,
        #"사용자 세션 키"
    )
    
    input_text = serializers.CharField(
        #"사용자 입력 텍스트 (질문에 대한 답변)"
    )
    
    # 사용자 위치 정보 (선택사항)
    latitude = serializers.FloatField(
        required=False,
        #"사용자 위도"
    )
    
    longitude = serializers.FloatField(
        required=False,
        #"사용자 경도"
    )
    
    # 메타 정보 (선택사항)
    meta = serializers.DictField(
        required=False,
        allow_empty=True,
        #"추가 메타 정보"
    )

    def validate_input_text(self, value):
        """입력 텍스트 유효성 검사"""
        if len(value.strip()) < 1:
            raise serializers.ValidationError("입력 텍스트는 최소 1자 이상이어야 합니다.")
        if len(value) > 500:
            raise serializers.ValidationError("입력 텍스트는 500자를 초과할 수 없습니다.")
        return value.strip()


class TaroChatResponseSerializer(serializers.Serializer):
    """타루 대화 응답 시리얼라이저"""
    
    output_text = serializers.CharField(
        #"타루의 응답 텍스트"
    )
    
    conversation_stage = serializers.CharField(
        #"현재 대화 단계"
    )
    
    question_count = serializers.IntegerField(
        #"현재까지의 질문 수"
    )
    
    max_questions = serializers.IntegerField(
        #"최대 질문 수"
    )
    
    can_draw_cards = serializers.BooleanField(
        #"카드 뽑기 가능 여부"
    )
    
    is_conversation_complete = serializers.BooleanField(
        #"대화 완료 여부"
    )


class TaroCardSerializer(serializers.ModelSerializer):
    """타로 카드 시리얼라이저"""
    
    # API 응답에서 사용할 카드 ID
    card_id = serializers.CharField(
        source='card_id',
        read_only=True,
        #"카드 고유 식별자"
    )
    
    place_name = serializers.CharField(
        read_only=True,
        #"장소명"
    )
    
    distance = serializers.CharField(
        read_only=True,
        #"사용자로부터의 거리"
    )
    
    category = serializers.CharField(
        read_only=True,
        #"장소 카테고리"
    )
    
    address = serializers.CharField(
        read_only=True,
        #"기본 주소"
    )
    
    road_address = serializers.CharField(
        read_only=True,
        #"도로명 주소"
    )
    
    phone = serializers.CharField(
        read_only=True,
        #"전화번호"
    )
    
    recommendation_reason = serializers.CharField(
        read_only=True,
        #"추천 이유"
    )
    
    card_position = serializers.IntegerField(
        read_only=True,
        #"카드 덱에서의 위치"
    )

    class Meta:
        model = TaroCard
        fields = [
            'card_id',
            'place_name',
            'distance', 
            'category',
            'address',
            'road_address',
            'phone',
            'recommendation_reason',
            'card_position'
        ]


class TaroCardShuffleQuerySerializer(serializers.Serializer):
    """카드 셔플 & 드로우 요청 시리얼라이저"""
    
    session_key = serializers.CharField(
        max_length=64,
        #"사용자 세션 키"
    )


class TaroCardRedrawQuerySerializer(serializers.Serializer):
    """카드 다시 뽑기 요청 시리얼라이저"""
    
    session_key = serializers.CharField(
        max_length=64,
        #"사용자 세션 키"
    )


class TaroCardSelectSerializer(serializers.Serializer):
    """카드 선택 요청 시리얼라이저"""
    
    session_key = serializers.CharField(
        max_length=64,
        #"사용자 세션 키"
    )
    
    card_id = serializers.CharField(
        #"선택할 카드 ID"
    )
    
    selection_note = serializers.CharField(
        required=False,
        max_length=500,
        #"선택 메모 (선택사항)"
    )
    
    priority = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=10,
        default=5,
        #"우선순위 (0-10)"
    )


class TaroCartItemSerializer(serializers.ModelSerializer):
    """타로 장바구니 아이템 시리얼라이저"""
    
    card = TaroCardSerializer(read_only=True)
    
    class Meta:
        model = TaroCartItem
        fields = [
            'id',
            'session_key',
            'card',
            'selection_note',
            'priority',
            'created_at'
        ]
        read_only_fields = ['created_at']


class TaroCartQuerySerializer(serializers.Serializer):
    """장바구니 조회 요청 시리얼라이저"""
    
    session_key = serializers.CharField(
        max_length=64,
        #"사용자 세션 키"
    )


class TaroConversationStatusSerializer(serializers.ModelSerializer):
    """대화 상태 시리얼라이저"""
    
    can_draw_cards = serializers.SerializerMethodField()
    is_conversation_complete = serializers.SerializerMethodField()
    
    class Meta:
        model = TaroConversation
        fields = [
            'session_key',
            'conversation_stage',
            'question_count',
            'max_questions',
            'card_draw_count',
            'max_card_draws',
            'can_draw_cards',
            'is_conversation_complete',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_can_draw_cards(self, obj):
        """카드 뽑기 가능 여부"""
        return obj.can_draw_cards()
    
    def get_is_conversation_complete(self, obj):
        """대화 완료 여부"""
        return obj.is_conversation_complete()


class TaroQuestionTemplateSerializer(serializers.ModelSerializer):
    """타로 질문 템플릿 시리얼라이저 (관리자용)"""
    
    class Meta:
        model = TaroQuestionTemplate
        fields = [
            'id',
            'question_text',
            'question_category',
            'answer_choices',
            'weight',
            'is_active',
            'created_at'
        ]
        read_only_fields = ['created_at']


# 통계 및 분석용 시리얼라이저들

class TaroRecommendationStatsSerializer(serializers.Serializer):
    """추천 통계 시리얼라이저"""
    
    total_conversations = serializers.IntegerField(
        #"총 대화 수"
    )
    
    completed_conversations = serializers.IntegerField(
        #"완료된 대화 수"
    )
    
    total_cards_generated = serializers.IntegerField(
        #"생성된 총 카드 수"
    )
    
    total_cards_selected = serializers.IntegerField(
        #"선택된 총 카드 수"
    )
    
    popular_categories = serializers.ListField(
        child=serializers.DictField(),
        #"인기 카테고리"
    )
    
    avg_questions_per_session = serializers.FloatField(
        #"세션당 평균 질문 수"
    )


class TaroUserJourneySerializer(serializers.Serializer):
    """사용자 여정 시리얼라이저"""
    
    session_key = serializers.CharField(
        #"세션 키"
    )
    
    conversation_status = TaroConversationStatusSerializer()
    
    current_cards = TaroCardSerializer(many=True)
    
    cart_items = TaroCartItemSerializer(many=True)
    
    next_action = serializers.CharField(
        #"다음 권장 액션"
    )


# 에러 응답용 시리얼라이저

class TaroErrorResponseSerializer(serializers.Serializer):
    """타로 에러 응답 시리얼라이저"""
    
    error_code = serializers.CharField(
        #"에러 코드"
    )
    
    error_message = serializers.CharField(
        #"에러 메시지"
    )
    
    details = serializers.DictField(
        required=False,
        #"추가 에러 상세 정보"
    )

