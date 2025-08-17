"""
Taro 앱 모델
- 타루와의 대화, 카드 뽑기, 장바구니 기능
"""

from django.db import models
from django.utils import timezone
from places.models import Place


def default_json():
    """JSONField의 기본값으로 사용할 빈 딕셔너리를 반환하는 함수"""
    return {}


def taro_card_image_upload_path(instance: 'TaroCard', filename: str) -> str:
    """타로 카드 이미지 업로드 경로 설정"""
    return f"taro/cards/{instance.pk}/{filename}"


class TaroConversation(models.Model):
    """사용자-타루 대화 세션 모델
    
    - 아키네이터 스타일의 질문/응답 시스템
    - OpenAI API를 활용한 대화 히스토리 관리
    - 세션 기반으로 익명 사용자도 사용 가능
    """
    
    id = models.BigAutoField(primary_key=True)
    
    # 세션 관리
    session_key = models.CharField(
        max_length=64, 
        db_index=True,
        #"사용자 세션 키 (익명 사용자 지원)"
    )
    
    user_identifier = models.CharField(
        max_length=128, 
        blank=True, 
        null=True,
        #"사용자 식별자 (로그인 사용자용)"
    )
    
    # 대화 상태 관리
    conversation_stage = models.CharField(
        max_length=20,
        choices=[
            ('greeting', '인사 단계'),
            ('questioning', '질문 단계'),
            ('analyzing', '분석 단계'),
            ('recommending', '추천 단계'),
            ('completed', '완료 단계'),
        ],
        default='greeting',
        #"현재 대화 진행 단계"
    )
    
    # 질문 카운터 (아키네이터 스타일)
    question_count = models.IntegerField(
        default=0,
        #"현재까지 진행된 질문 수"
    )
    
    max_questions = models.IntegerField(
        default=20,
        #"최대 질문 수 (기본 20개)"
    )
    
    # 대화 히스토리 (OpenAI 프롬프트 구성용)
    conversation_history = models.JSONField(
        default=default_json,
        #"전체 대화 히스토리 [{role, content, timestamp}, ...]"
    )
    
    # 사용자 답변 분석 데이터
    user_preferences = models.JSONField(
        default=default_json,
        #"사용자 취향 분석 데이터 (장소 유형, 분위기, 활동 등)"
    )
    
    # 위치 정보
    user_latitude = models.FloatField(
        blank=True, 
        null=True,
        #"사용자 현재 위치 위도"
    )
    
    user_longitude = models.FloatField(
        blank=True, 
        null=True,
        #"사용자 현재 위치 경도"
    )
    
    # 카드 추천 제한 (다시 뽑기 1회 제한)
    card_draw_count = models.IntegerField(
        default=0,
        #"카드 뽑기 횟수 (최대 2회: 초기 + 다시뽑기 1회)"
    )
    
    max_card_draws = models.IntegerField(
        default=2,
        #"최대 카드 뽑기 횟수"
    )
    
    # 타임스탬프
    created_at = models.DateTimeField(
        default=timezone.now,
        #"대화 시작 시간"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        #"마지막 업데이트 시간"
    )
    
    # 마지막 AI 응답 캐시
    last_ai_response = models.TextField(
        blank=True,
        null=True,
        #"마지막 AI 응답 (캐시용)"
    )

    class Meta:
        verbose_name = "타로 대화"
        verbose_name_plural = "타로 대화들"
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['conversation_stage']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"TaroConversation<{self.session_key}:{self.conversation_stage}>"
    
    def can_draw_cards(self) -> bool:
        """카드를 뽑을 수 있는지 확인"""
        return self.card_draw_count < self.max_card_draws
    
    def is_conversation_complete(self) -> bool:
        """대화가 완료되었는지 확인"""
        return (
            self.conversation_stage == 'completed' or
            self.question_count >= self.max_questions
        )


class TaroCard(models.Model):
    """타로 카드 모델 (추천된 장소)
    
    - 대화 기반으로 추천된 장소들을 카드 형태로 저장
    - Place 모델과 연결하되 독립적인 카드 정보 관리
    """
    
    id = models.BigAutoField(primary_key=True)
    
    # 연관된 대화 세션
    conversation = models.ForeignKey(
        TaroConversation,
        on_delete=models.CASCADE,
        related_name='cards',
        #"이 카드가 속한 대화 세션"
    )
    
    # 기존 장소와의 연결 (있는 경우)
    place = models.ForeignKey(
        Place,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        #"연결된 장소 (기존 Place 모델)"
    )
    
    # 카드 고유 정보 (스냅샷)
    card_id = models.CharField(
        max_length=50,
        #"카드 고유 식별자"
    )
    
    place_name = models.CharField(
        max_length=100,
        #"장소명"
    )
    
    distance = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        #"사용자로부터의 거리 (예: '1.2km')"
    )
    
    category = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        #"장소 카테고리 (카페, 식당, 관광지 등)"
    )
    
    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        #"기본 주소"
    )
    
    road_address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        #"도로명 주소"
    )
    
    phone = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        #"전화번호"
    )
    
    # 추가 카드 정보
    card_image = models.ImageField(
        upload_to=taro_card_image_upload_path,
        blank=True,
        null=True,
        #"카드 이미지"
    )
    
    recommendation_reason = models.TextField(
        blank=True,
        null=True,
        #"AI가 추천한 이유"
    )
    
    # 카드 순서 (덱에서의 위치)
    card_position = models.IntegerField(
        #"카드 덱에서의 위치 (1-25)"
    )
    
    # 카드 뽑기 차수
    draw_round = models.IntegerField(
        default=1,
        #"몇 번째 뽑기에서 나온 카드인지 (1: 초기, 2: 다시뽑기)"
    )
    
    # 외부 API 연동 정보
    kakao_place_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        #"카카오 장소 ID"
    )
    
    google_place_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        #"구글 장소 ID"
    )
    
    # 좌표 정보
    latitude = models.FloatField(
        blank=True,
        null=True,
        #"위도"
    )
    
    longitude = models.FloatField(
        blank=True,
        null=True,
        #"경도"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        #"카드 생성 시간"
    )

    class Meta:
        verbose_name = "타로 카드"
        verbose_name_plural = "타로 카드들"
        indexes = [
            models.Index(fields=['conversation', 'draw_round']),
            models.Index(fields=['card_position']),
            models.Index(fields=['kakao_place_id']),
            models.Index(fields=['google_place_id']),
        ]
        # 같은 대화에서 같은 위치의 카드는 중복되지 않도록
        unique_together = ['conversation', 'card_position', 'draw_round']

    def __str__(self):
        return f"TaroCard<{self.place_name}:{self.card_position}>"


class TaroCartItem(models.Model):
    """타로 장바구니 아이템
    
    - 사용자가 선택한 카드들을 저장
    - 세션 기반으로 관리
    """
    
    id = models.BigAutoField(primary_key=True)
    
    # 세션 정보
    session_key = models.CharField(
        max_length=64,
        db_index=True,
        #"사용자 세션 키"
    )
    
    # 선택된 카드
    card = models.ForeignKey(
        TaroCard,
        on_delete=models.CASCADE,
        related_name='cart_items',
        #"선택된 타로 카드"
    )
    
    # 선택 메모
    selection_note = models.TextField(
        blank=True,
        null=True,
        #"사용자가 작성한 선택 메모"
    )
    
    # 우선순위 (사용자가 설정)
    priority = models.IntegerField(
        default=0,
        #"우선순위 (높을수록 우선)"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        #"장바구니 추가 시간"
    )

    class Meta:
        verbose_name = "타로 장바구니 아이템"
        verbose_name_plural = "타로 장바구니 아이템들"
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['priority']),
        ]
        # 같은 세션에서 같은 카드는 중복 선택 불가
        unique_together = ['session_key', 'card']

    def __str__(self):
        return f"TaroCartItem<{self.session_key}:{self.card.place_name}>"


class TaroQuestionTemplate(models.Model):
    """타로 질문 템플릿
    
    - 아키네이터 스타일의 질문들을 관리
    - AI가 동적으로 질문을 생성할 때 참고용
    """
    
    id = models.BigAutoField(primary_key=True)
    
    question_text = models.TextField(
        #"질문 내용"
    )
    
    question_category = models.CharField(
        max_length=50,
        choices=[
            ('location_preference', '위치 선호도'),
            ('activity_type', '활동 유형'),
            ('atmosphere', '분위기'),
            ('time_preference', '시간 선호도'),
            ('group_size', '그룹 크기'),
            ('budget', '예산'),
            ('weather', '날씨 관련'),
            ('mood', '기분/감정'),
            ('special_occasion', '특별한 날'),
            ('food_preference', '음식 선호도'),
        ],
        #"질문 카테고리"
    )
    
    # 답변 선택지 (JSON 형태로 저장)
    answer_choices = models.JSONField(
        default=default_json,
        #"답변 선택지 리스트"
    )
    
    # 질문 가중치 (자주 사용되는 질문일수록 높음)
    weight = models.IntegerField(
        default=1,
        #"질문 가중치 (AI 선택 시 참고)"
    )
    
    is_active = models.BooleanField(
        default=True,
        #"활성화 여부"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        #"질문 생성 시간"
    )

    class Meta:
        verbose_name = "타로 질문 템플릿"
        verbose_name_plural = "타로 질문 템플릿들"
        indexes = [
            models.Index(fields=['question_category']),
            models.Index(fields=['weight']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"TaroQuestionTemplate<{self.question_category}:{self.question_text[:50]}>"