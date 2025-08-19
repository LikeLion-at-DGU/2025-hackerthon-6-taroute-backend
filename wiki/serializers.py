"""
Wiki 앱 시리얼라이저
- 위키 검색 요청/응답 데이터 직렬화
- 장소 정보, 리뷰, 신고 관련 시리얼라이저
"""

from rest_framework import serializers
from decimal import Decimal
from places.models import Place
from .models import WikiPlace, WikiSearchHistory, Review, Report


class WikiSearchQuerySerializer(serializers.Serializer):
    """위키 검색 요청 파라미터 시리얼라이저
    - 3.1 위키 검색 기능용
    """
    # 검색 키워드 (필수)
    place_name = serializers.CharField(
        required=False,
        max_length=100,
        help_text="검색할 장소명"
    )
    
    # location_name = serializers.CharField(
    #     required=False,
    #     max_length=100,
    #     help_text="검색할 지역명"
    # )
    
    # 사용자 현재 위치 (선택사항)
    longitude = serializers.FloatField(
        required=False,
        help_text="사용자 현재 위치 경도"
    )
    
    latitude = serializers.FloatField(
        required=False,
        help_text="사용자 현재 위치 위도"
    )
    
    # 검색 옵션
    radius = serializers.IntegerField(
        default=20000,
        min_value=1000,
        max_value=20000,
        help_text="검색 반경(미터), 기본 20km"
    )

    rankPreference = serializers.ChoiceField(
        choices=["RELEVANCE", "DISTANCE"], 
        help_text="'RELEVANCE'=검색 관련성, 'DISTANCE'=거리순",
        default="RELEVANCE", 
        required=False, 
        allow_null=True
    )
    
    # page = serializers.IntegerField(
    #     default=1,
    #     min_value=1,
    #     max_value=45,
    #     help_text="페이지 번호"
    # )
    
    # size = serializers.IntegerField(
    #     default=15,
    #     min_value=1,
    #     max_value=15,
    #     help_text="한 페이지 결과 수"
    # )
    
    # # 세션 키 (검색 기록 저장용)
    # session_key = serializers.CharField(
    #     required=False,
    #     max_length=64,
    #     help_text="사용자 세션 키"
    # )

    def validate(self, data):
        """검색 키워드 유효성 검사
        - place_name 또는 location_name 중 하나는 필수
        """
        place_name = data.get('place_name')
        location_name = data.get('location_name')
        
        if not place_name and not location_name:
            raise serializers.ValidationError(
                "place_name 또는 location_name 중 하나는 필수입니다."
            )
        
        return data


class WikiPlaceSearchResultSerializer(serializers.Serializer):
    """위키 검색 결과 응답 시리얼라이저
    - 3.1 위키 검색 결과용
    """
    # 기본 장소 정보
    place_name = serializers.CharField(help_text="장소명")
    location_name = serializers.CharField(help_text="지역명/주소")
    longitude = serializers.FloatField(help_text="경도")
    latitude = serializers.FloatField(help_text="위도")
    
    # 장소 위치 정보 (상세 주소)
    place_location = serializers.CharField(
        source='address',
        help_text="상세 주소"
    )
    
    # 평점 정보
    review_score = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        help_text="평균 리뷰 점수"
    )
    
    # 추가 정보
    distance = serializers.CharField(
        required=False,
        help_text="사용자 위치로부터의 거리"
    )
    
    category = serializers.CharField(
        required=False,
        help_text="장소 카테고리"
    )
    
    kakao_place_id = serializers.CharField(
        required=False,
        help_text="카카오 장소 ID"
    )


class WikiPlaceDetailSerializer(serializers.Serializer):
    """위키 장소 상세 정보 시리얼라이저
    - 3.2.1 정보 안내용
    """
    # 기본 정보
    place_name = serializers.CharField(help_text="장소명")
    location_name = serializers.CharField(help_text="지역명/주소")
    longitude = serializers.FloatField(help_text="경도")
    latitude = serializers.FloatField(help_text="위도")
    
    # 상점 정보
    shop_name = serializers.CharField(help_text="상점명")
    shop_image = serializers.ImageField(
        required=False,
        help_text="상점 대표 이미지"
    )
    
    # AI 요약
    ai_summation = serializers.CharField(
        help_text="AI가 생성한 장소 요약"
    )
    ai_summation_info = serializers.JSONField(
        help_text="AI 요약 메타데이터"
    )
    
    # 기본 정보
    basic_information = serializers.CharField(
        help_text="장소 기본 정보"
    )
    basic_information_info = serializers.JSONField(
        help_text="기본 정보 메타데이터"
    )
    
    # 리뷰 요약
    reviews = serializers.ListField(
        child=serializers.DictField(),
        help_text="리뷰 목록"
    )
    
    # 통계 정보
    average_review_score = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        help_text="평균 리뷰 점수"
    )
    
    total_review_count = serializers.IntegerField(
        help_text="총 리뷰 개수"
    )


class WikiReviewSerializer(serializers.ModelSerializer):
    """위키 리뷰 시리얼라이저
    - 3.2.2 후기 작성/조회용
    """
    # 리뷰 점수 유효성 검사 강화
    review_score = serializers.DecimalField(
        max_digits=2,
        decimal_places=1,
        min_value=Decimal('0.0'),
        max_value=Decimal('5.0'),
        help_text="리뷰 점수 (0.0~5.0)"
    )
    
    # 읽기 전용 필드들
    ai_review = serializers.CharField(
        read_only=True,
        help_text="AI가 생성한 리뷰 분석"
    )
    
    created_at = serializers.DateTimeField(
        read_only=True,
        help_text="리뷰 작성 시간"
    )
    
    updated_at = serializers.DateTimeField(
        read_only=True,
        help_text="리뷰 수정 시간"
    )

    place_name = serializers.CharField(read_only=True)
    gplace_id   = serializers.CharField(read_only=True)
    like_num = serializers.IntegerField(default=0)


    class Meta:
        model = Review
        fields = [
            'id',
            'review_content',
            'review_score', 
            'ai_review',
            'review_image',
            'created_at',
            'updated_at',
            'place_name',
            'gplace_id',
            'like_num',
        ]
        read_only_fields = ['ai_review']
    
    def to_representation(self, instance):
        representation  = super().to_representation(instance)
        representation ['place_name'] = instance.wiki_place.shop_name
        representation ['gplace_id'] = instance.wiki_place.google_place_id
        return representation

    def validate_review_content(self, value):
        """리뷰 내용 유효성 검사"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "리뷰 내용은 10자 이상 작성해주세요."
            )
        if len(value) > 1000:
            raise serializers.ValidationError(
                "리뷰 내용은 1000자를 초과할 수 없습니다."
            )
        return value.strip()


class WikiReviewCreateSerializer(serializers.ModelSerializer):
    """위키 리뷰 생성 전용 시리얼라이저
    - 장소 ID를 따로 받기 위한 확장
    """
    place_id = serializers.CharField(write_only=True, required=False, allow_blank=True)

    review_image = serializers.ImageField(required=False, allow_null=True, use_url=True)
    class Meta:
        model  = Review
        fields = [
            'id',
            'place_id',
            'review_content',
            'review_score',
            'review_image',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        gplace_id = validated_data.pop('place_id')

        if not gplace_id:
            raise serializers.ValidationError("place_id 는 필수입니다.")

        wp, _ = WikiPlace.objects.get_or_create(
            google_place_id=gplace_id
        )

        # wiki_place를 넣어서 Review 생성
        review = Review.objects.create(wiki_place=wp, **validated_data)
        return review
        

# 신고 사유 선택지 정의
REPORT_REASONS = [
    ('spam', '스팸/광고'),
    ('inappropriate', '부적절한 내용'),
    ('false_info', '허위 정보'),
    ('offensive', '욕설/비방'),
    ('copyright', '저작권 침해'),
    ('other', '기타'),
]
class WikiReportSerializer(serializers.ModelSerializer):
    """위키 신고 시리얼라이저
    - 3.2.3 후기 신고용
    """
 
    reason = serializers.ChoiceField(
        choices=REPORT_REASONS,
        help_text="신고 사유"
    )
    
    # report_title = serializers.CharField(
    #     max_length=50,
    #     help_text="신고 제목"
    # )
    
    report_content = serializers.CharField(
        max_length=500,
        help_text="신고 상세 내용"
    )
    
    # 읽기 전용 필드
    created_at = serializers.DateTimeField(
        read_only=True,
        help_text="신고 시간"
    )

    review_id = serializers.IntegerField(
        source='review.id',
        read_only=True,
        help_text="신고할 리뷰 ID"
    )

    class Meta:
        model = Report
        fields = [
            'id',
            'review_id',
            'reason',
            # 'report_title', 
            'report_content',
            'created_at'
        ]

    def validate_report_content(self, value):
        """신고 내용 유효성 검사"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "신고 내용은 5자 이상 작성해주세요."
            )
        return value.strip()


class WikiReportCreateSerializer(WikiReportSerializer):
    """위키 신고 생성 전용 시리얼라이저"""
    review_id = serializers.IntegerField(
        write_only=True,
        help_text="신고할 리뷰 ID"
    )

    class Meta(WikiReportSerializer.Meta):
        fields = WikiReportSerializer.Meta.fields + ['review_id']
        
    def create(self, validated_data):
        """신고 생성 시 review_id를 review 객체로 변환"""
        review_id = validated_data.pop('review_id')
        try:
            review = Review.objects.get(id=review_id)
            validated_data['review'] = review
        except Review.DoesNotExist:
            raise serializers.ValidationError(
                f"ID {review_id}에 해당하는 리뷰를 찾을 수 없습니다."
            )
        
        return super().create(validated_data)


class WikiSearchHistorySerializer(serializers.ModelSerializer):
    """위키 검색 기록 시리얼라이저
    - 검색 패턴 분석용
    """
    class Meta:
        model = WikiSearchHistory
        fields = [
            'id',
            'search_query',
            'search_type',
            'result_count',
            'session_key',
            'search_longitude',
            'search_latitude',
            'created_at'
        ]
        read_only_fields = ['created_at']


class PopularKeywordSerializer(serializers.Serializer):
    """인기 검색어 시리얼라이저"""
    keyword = serializers.CharField(help_text="검색 키워드")
    count = serializers.IntegerField(help_text="검색 횟수")
