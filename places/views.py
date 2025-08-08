from django.shortcuts import render

# Create your views here.
from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from rest_framework import viewsets, mixins
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import *
from .serializers import *
from .services import kakao

import requests

from django.shortcuts import get_object_or_404

# 1.1 현위치 표시
class PlaceViewSet(viewsets.ModelViewSet):
  queryset = Place.objects.all()
  serializer_class = PlaceSerializer

  @extend_schema(
    tags = ["현위치 표시"],
    parameters=[
      OpenApiParameter(name="x", description="경도", required=True, type=float),
      OpenApiParameter(name="y", description="위도", required=True, type=float),
    ],
    responses={200: DongResponseSerializer},
    summary="현위치 기준 동 반환",
    description="클라이언트 위치(경도, 위도) 기준 카카오 동 반환",
  )

  @action(detail=False, methods=["GET"])
  def locate(self, request):
    lng = request.query_params.get("x")
    lat = request.query_params.get("y")

    if not (lat and lng):
        return Response({"detail": "경도, 위도가 필요합니다."}, status=400)
    try:
        data = kakao.locate_dong(x=float(lng), y=float(lat))
    except ValueError:
        return Response({"detail": "경도/위도는 숫자여야 합니다."}, status=400)
    except requests.RequestException as e:
        return Response({"detail": f"카카오 API 호출 실패: {e}"}, status=502)

    # Kakao 응답에서 동 이름 뽑기 (region_3depth_name가 보통 ‘○○동’)
    dong = None
    code = None
    docs = data.get("documents", [])
    if docs:
        primary = docs[0]
        dong = primary.get("region_3depth_name")
        code = primary.get("code")

    if not dong:
        return Response({"detail": "동 정보를 찾지 못했습니다."}, status=404)

    return Response({"dong": dong, "code": code}, status=200)
