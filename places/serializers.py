from rest_framework import serializers
from .models import *

class PlaceSerializer(serializers.ModelSerializer):
  class Meta:
    model = Place
    fields = ['longitude', 'latitude']

class DongResponseSerializer(serializers.Serializer):
    dong = serializers.CharField(help_text="행정동(법정동) 명칭")
    code = serializers.CharField(help_text="행정코드", required=False)

class ReviewSerializer(serializers.ModelSerializer):
  class Meta:
    model = Review
    fields = '__all__'
    read_only_fields = ["ai_review"]