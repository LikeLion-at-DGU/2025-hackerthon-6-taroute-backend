from rest_framework import serializers
from .models import PopularKeyward

# 1.2 구글 장소 검색
class PlaceMixin(serializers.Serializer):
    x = serializers.FloatField()   # 경도
    y = serializers.FloatField()   # 위도
    radius = serializers.IntegerField(required=False, default=2000)

class PlaceSearchSerializer(PlaceMixin):
    q = serializers.CharField(source="text_query")  # API에 넘길 키 이름 매핑
    priceLevel = serializers.CharField(required=False, allow_null=True)
    rankPreference = serializers.ChoiceField(choices=["RELEVANCE", "DISTANCE"], help_text="'RELEVANCE'=검색 관련성, 'DISTANCE'=거리순",default="RELEVANCE", required=False, allow_null=True)

# 1.2 장소 카테고리별 추천
class PlaceRecommendSerializer(PlaceMixin): 
    radius = serializers.IntegerField(required=True)
    category_group_code = serializers.CharField(required=False)
    limit = serializers.IntegerField(required=False, default=10)
    many_review = serializers.BooleanField(required=False) #지금 인기있는 순=리뷰 많은 순!
    # 인기순 관련 : 검색어가 비슷한 것끼리 모델에 저장되어 카운트?

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


# 6.1 등록된 카드의 동선 안내
class PlaceRouteSerializer(serializers.Serializer):
    transport = serializers.ChoiceField(choices=["car", "transit", "walk"], help_text="'car'=카카오 내비, 'transit'=티맵 대중교통, 'walk'=도보")
    origin_x = serializers.FloatField()
    origin_y = serializers.FloatField()
    destination_x = serializers.FloatField()
    destination_y = serializers.FloatField()
    startName = serializers.CharField(required=False)
    endName = serializers.CharField(required=False)