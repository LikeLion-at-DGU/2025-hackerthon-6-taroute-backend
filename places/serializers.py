from rest_framework import serializers
from django.conf import settings
from .models import PopularKeyward, RouteSnapshot, gen_short
from django.db import IntegrityError, models as dj_models
from django.db import transaction
from django.db.models import Max



# 1.2 구글 장소 검색
class PlaceMixin(serializers.Serializer):
    x = serializers.FloatField()   # 경도
    y = serializers.FloatField()   # 위도
    radius = serializers.IntegerField(required=False)

class PlaceSearchSerializer(PlaceMixin):
    q = serializers.CharField(source="text_query")  # API에 넘길 키 이름 매핑
    priceLevel = serializers.CharField(required=False, allow_null=True)
    rankPreference = serializers.ChoiceField(choices=["RELEVANCE", "DISTANCE"], help_text="'RELEVANCE'=검색 관련성, 'DISTANCE'=거리순",default="RELEVANCE", required=False, allow_null=True)

# 1.2 장소 카테고리별 추천
class PlaceRecommendSerializer(PlaceMixin): 
    category_group_code = serializers.CharField(required=False)
    limit = serializers.IntegerField(required=False, default=7)

# 1.2 장소 저장하기
class SavePlaceSerializer(serializers.Serializer):
   place_id = serializers.CharField(max_length=50)
   class Meta:
    model = PopularKeyward
    fields = ("place_id", "place_name", "click_num")
    read_only_fields = ("place_name", "click_num")

# 4. 타로 페이지
class ChatSerializer(serializers.Serializer):
    input_text = serializers.CharField()
    lang = serializers.ChoiceField(choices=["ko","en"], required=False)

class CardSelectSerializer(PlaceMixin):
    input_text = serializers.CharField()
    lang = serializers.ChoiceField(choices=["ko","en"], required=False)

# 카테고리 페이지 - 검색 및 필터링
class CategorySearchSerializer(PlaceMixin):
    text_query = serializers.CharField(required=False, help_text="검색어 (선택사항)")
    category = serializers.ChoiceField(
        choices=[
            ("restaurant", "식당"),
            ("cafe", "카페"), 
            ("culture", "문화시설"),
            ("tourist_attraction", "관광명소"),
            ("all", "전체")
        ],
        default="all",
        help_text="카테고리 필터"
    )
    
    # 거리 필터
    distance_filter = serializers.ChoiceField(
        choices=[
            ("0.5km", "0.5km 이내"),
            ("1km", "1km 이내"),
            ("3km", "3km 이내"),
            ("5km", "5km 이내"),
            ("all", "전체")
        ],
        default="all",
        help_text="거리 필터"
    )
    
    # 방문시간 필터
    visit_time_filter = serializers.ChoiceField(
        choices=[
            ("morning", "아침 (06:00-12:00)"),
            ("afternoon", "낮 (12:00-17:00)"),
            ("evening", "저녁 (17:00-21:00)"),
            ("night", "밤 (21:00-24:00)"),
            ("dawn", "새벽 (00:00-06:00)"),
            ("all", "전체")
        ],
        default="all",
        help_text="방문시간 필터"
    )
    
    # 방문요일 필터 (다중 선택 가능)
    visit_days_filter = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            ("monday", "월요일"),
            ("tuesday", "화요일"),
            ("wednesday", "수요일"),
            ("thursday", "목요일"),
            ("friday", "금요일"),
            ("saturday", "토요일"),
            ("sunday", "일요일")
        ]),
        required=False,
        help_text="방문요일 필터 (복수 선택 가능)"
    )
    
    # 정렬 옵션
    sort_by = serializers.ChoiceField(
        choices=[
            ("distance", "거리순"),
            ("relevance", "관련성순"),
            ("rating", "평점순"),
            ("popularity", "인기순")
        ],
        default="relevance",
        help_text="정렬 기준"
    )
    
    limit = serializers.IntegerField(default=20, min_value=1, max_value=50, help_text="결과 수 제한")

# 카테고리 장소 응답 시리얼라이저
class CategoryPlaceSerializer(serializers.Serializer):
    place_id = serializers.CharField(help_text="구글 장소 ID")
    place_name = serializers.CharField(help_text="장소명")
    category = serializers.CharField(help_text="카테고리")
    address = serializers.CharField(help_text="주소")
    location = serializers.DictField(help_text="위치 좌표")
    distance = serializers.CharField(help_text="거리 (예: 1.2km)")
    rating = serializers.FloatField(help_text="평점")
    review_count = serializers.IntegerField(help_text="리뷰 수")
    price_level = serializers.CharField(required=False, help_text="가격대")
    opening_hours = serializers.DictField(required=False, help_text="영업시간 정보")
    is_open_now = serializers.BooleanField(required=False, help_text="현재 영업 중 여부")
    place_photos = serializers.ListField(required=False, help_text="장소 사진 URL 목록")
    click_num = serializers.IntegerField(default=0, help_text="인기도 (클릭 수)")

# 6.1 등록된 카드의 동선 안내
class PlaceRouteSerializer(serializers.Serializer):
    transport = serializers.ChoiceField(choices=["car", "transit", "walk"], help_text="'car'=카카오 내비, 'transit'=티맵 대중교통, 'walk'=도보")
    origin_x = serializers.FloatField()
    origin_y = serializers.FloatField()
    destination_x = serializers.FloatField()
    destination_y = serializers.FloatField()
    startName = serializers.CharField(required=False)
    endName = serializers.CharField(required=False)

# 6.3 링크 공유
FRONT_ORIGIN = getattr(settings, "FRONT_ORIGIN", "https://www.taroute.com").rstrip("/")
class RouteSnapshotCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteSnapshot
        fields = ["params"] 

    def create(self, validated_data):

        last_err = None
        for _ in range(10):
            try:
                return RouteSnapshot.objects.create(
                    short=gen_short(),
                    view_count=0, 
                    **validated_data
                )
            except IntegrityError as e:
                last_err = e
                if "unique" in str(e).lower() and "short" in str(e).lower():
                    continue
                raise serializers.ValidationError(f"DB 오류: {e}")
        raise serializers.ValidationError(f"공유 코드를 발급하지 못했습니다. (마지막 오류: {last_err})")

class RouteSnapshotSerializer(serializers.ModelSerializer):
    share_url = serializers.SerializerMethodField()

    class Meta:
        model = RouteSnapshot
        fields = ["short", "params", "created_at", "expires_at", "share_url", "view_count"]

    def get_share_url(self, obj):
        return f"{FRONT_ORIGIN}/r/{obj.short}"