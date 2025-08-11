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
class PlaceSearchSerializer(serializers.Serializer):
    q = serializers.CharField(source="text_query")  # API에 넘길 키 이름 매핑
    x = serializers.FloatField()   # 경도
    y = serializers.FloatField()   # 위도
    radius = serializers.IntegerField(required=False, default=2000) # 미터단위, 기본 2km
    priceLevel = serializers.CharField(required=False, allow_null=True)

# 6.1 등록된 카드의 동선 안내
class PointSerializer(serializers.Serializer):
    x = serializers.FloatField(help_text='경도')
    y = serializers.FloatField(help_text='위도')
class PlaceRouteSerializer(serializers.ModelSerializer):
  class Meta:
    model = Place
    fields = ['transport','origin', 'destination', 'waypoints', 'priority', 'alternatives']

  transport = serializers.ChoiceField(choices=["car", "transit"], help_text="'car'=카카오 내비, 'transit'=티맵 대중교통")
  origin = PointSerializer()
  destination = PointSerializer()
  waypoints = PointSerializer(many=True, required=False, allow_empty=True)
  priority = serializers.ChoiceField(choices=['RECOMMEND','TIME', 'DISTANCE'], required=False)
  alternatives = serializers.BooleanField(default=True)

  def validate_waypoints(self, value):
      if value is None:
          return []
      if len(value) > 25:
          raise serializers.ValidationError("경유지(waypoints)는 최대 25개까지 허용됩니다.")
      return value

class ReviewSerializer(serializers.ModelSerializer):
  class Meta:
    model = Review
    fields = '__all__'
    read_only_fields = ["ai_review"]