from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from rest_framework import viewsets, mixins
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import *
from .serializers import *
from .services import kakao, tmap, google, openai

import requests

from django.shortcuts import get_object_or_404

class PlaceViewSet(viewsets.ViewSet):

  # 1.1 현위치 표시 (프론트에서 처리가능할 수도 있음, 확인 후 삭제 예정)
  @extend_schema(
    tags = ["1.1 현위치 표시"],
    parameters=[PlaceSerializer],
    responses={200: DongResponseSerializer},
    description="클라이언트 위치(경도, 위도) 기준 카카오 동 반환",
  )
  @action(detail=False, methods=["GET"])
  def locate(self, request):
    query = PlaceSerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    x = query.validated_data["latitude"]
    y = query.validated_data["longitude"]

    try:
        data = kakao.locate_dong(x=x, y=y)
    except ValueError:
        return Response({"detail": "경도/위도는 숫자여야 합니다."}, status=400)
    except requests.RequestException as e:
        return Response({"detail": f"카카오 API 호출 실패: {e}"}, status=502)
    
    docs = data.get("documents", [])
    if docs:
        dong = docs[0].get("region_3depth_name")
    if not dong:
        return Response({"detail": "동 정보를 찾지 못했습니다."}, status=404)
    
    return Response({"dong": dong}, status=200)

  # 1.2 구글 장소 검색 → place 정보 반환
  @extend_schema(
    tags=["1.2 구글 장소 검색"],
    parameters=[PlaceSearchSerializer],
    #후기, #인기순 정렬 코드 작성 필요
    description="Google Places API textSearch를 이용해 place 정보 반환",
  )
  @action(detail=False, methods=["GET"])
  def google_place(self, request):
    query = PlaceSearchSerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    params = query.validated_data

    try:
        places = google.search_place(**params)
    except requests.HTTPError as e:
        return Response({"detail": f"Google Places API 호출 실패: {e.response.status_code} {e.response.text}"}, status=502)
    except requests.RequestException as e:
        return Response({"detail": f"Google Places API 호출 실패: {e}"}, status=502)

    if not places:
        return Response({"detail": "장소를 찾지 못했습니다."}, status=404)

    return Response({"google_place" : places}, status=200)

  # 1.2 장소 카테고리별 추천
  # 1) 검색한 구글 장소의 위도경도로 카테고리별 10개씩 추출
  @extend_schema(
    tags = ["1.2 장소 카테고리별 추천"],
    parameters=[PlaceRecommendSerializer],
    description="구글 장소의 위도경도를 이용하여 카테고리별 장소 반환",
  )

  #CT1 문화시설, AT4 관광명소, FD6 음식점, CE7 카페
  @action(detail=False, methods=["GET"])
  def recommend(self, request):
    query = PlaceRecommendSerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    params = query.validated_data

    try:
        data = kakao.recommend_place(**params)
    except requests.RequestException as e:
        return Response({"detail": f"카카오 API 호출 실패: {e}"}, status=502)

    # 2) place_name, x, y 반환 => 구글 장소 세부데이터 요청 필요
    return Response({"data": data}, status=200) 

class PlaceRouteViewSet(viewsets.GenericViewSet):
  queryset = Place.objects.all()
  serializer_class = PlaceRouteSerializer

  # 6.1 등록된 카드의 동선 안내
  @extend_schema(
    tags = ["6.1 등록된 카드의 동선 안내"],
    parameters=[PlaceRouteSerializer],
    description="출발지, 도착지 좌표로 경로 안내(GET=자동차, POST=대중교통, 도보)",
 )

  @action(detail=False, methods=["GET", "POST"])
  def path(self, request):

    # 1) 함수 메소드 분기
    if request.method == "POST":
        request_data = request.query_params
    else:
        request_data = request.data

    # 2) 유효성 검사
    route = PlaceRouteSerializer(data=request_data)
    route.is_valid(raise_exception=True)
    data = route.validated_data

    ox, oy = data["origin_x"], data["origin_y"]
    dx, dy = data["destination_x"], data["destination_y"]

    transport = data["transport"]
    print(f"[DEBUG] 실행된 API: {transport}")

    # 3) API 호출
    try:
        if transport == "car": # 카카오내비(자동차)
            params = {
                "origin": f"{ox},{oy}",
                "destination": f"{dx},{dy}",
            }
            car_routes = kakao.car_route(**params)
            if not car_routes:
                return Response({"detail": "문서 정보를 찾지 못했습니다."}, status=404)
            return Response({"car_routes": car_routes}, status=200)

        elif transport == "transit":  # 티맵 (대중교통)
            params_l = dict(
                startX=data["origin_x"], 
                startY=data["origin_y"],
                endX=data["destination_x"],
                endY=data["destination_y"],
                count=1, lang=0, format="json"
            )

            traffic_routes = tmap.traffic_route(**params_l)
            if not traffic_routes:
                return Response({"detail": "대중교통 경로 없음"}, status=404)

            return Response({
                "transit_summary": traffic_routes.get("transit_summary"),
                "segments": traffic_routes.get("segments"),
            }, status=200)
        
        elif transport == "walk": # 티맵(도보)

            payload_W = dict (
                startX = data["origin_x"],
                startY = data["origin_y"],
                endX = data["destination_x"],
                endY = data["destination_y"],
                startName = data["startName"],
                endName = data["endName"]
            )

            walk_data = tmap.walk_route(**payload_W)
            return Response({"data":walk_data}, status=200)
        
        else:
            return Response({"detail": "존재하지 않는 transport 값입니다."}, status=400)
    
    except requests.RequestException as e:
        return Response({"detail": f"외부 API 호출 실패: {e}"}, status=502)