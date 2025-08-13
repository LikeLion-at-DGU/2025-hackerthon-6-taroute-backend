from rest_framework import serializers
from .models import *

# 1.1 현위치 표시
class PlaceSerializer(serializers.ModelSerializer):
  class Meta:
    model = Place
    fields = ['longitude', 'latitude']
class DongResponseSerializer(serializers.Serializer):
    dong = serializers.CharField(help_text="행정동(법정동) 명칭")
    code = serializers.CharField(help_text="행정코드", required=False)

# 1.2 구글 장소 검색
class PlaceMixin(serializers.Serializer):
    x = serializers.FloatField()   # 경도
    y = serializers.FloatField()   # 위도
    radius = serializers.IntegerField(required=False, default=2000)

class PlaceSearchSerializer(PlaceMixin):
    q = serializers.CharField(source="text_query")  # API에 넘길 키 이름 매핑
    priceLevel = serializers.CharField(required=False, allow_null=True)

# 1.2 장소 카테고리별 추천
class PlaceRecommendSerializer(PlaceMixin): 
    radius = serializers.IntegerField(required=True)
    category_group_code = serializers.CharField(required=False)
    limit = serializers.IntegerField(required=False, default=10)
    # 인기순 관련 : 검색어가 비슷한 것끼리 모델에 저장되어 카운트?

# 6.1 등록된 카드의 동선 안내
class PlaceRouteSerializer(serializers.Serializer):
    transport = serializers.ChoiceField(choices=["car", "transit", "walk"], help_text="'car'=카카오 내비, 'transit'=티맵 대중교통, 'walk'=도보")
    origin_x = serializers.FloatField()
    origin_y = serializers.FloatField()
    destination_x = serializers.FloatField()
    destination_y = serializers.FloatField()
    startName = serializers.CharField(required=False)
    endName = serializers.CharField(required=False)

class ReviewSerializer(serializers.ModelSerializer):
  class Meta:
    model = Review
    fields = '__all__'
    read_only_fields = ["ai_review"]