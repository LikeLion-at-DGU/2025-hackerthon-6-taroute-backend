from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from rest_framework import viewsets, mixins
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import *
from .serializers import *
from .services import kakao, tmap, google, openai

import requests
import json

from django.shortcuts import get_object_or_404

class PlaceViewSet(viewsets.ViewSet):

  # 1.1 현위치 표시 (프론트에서 처리가능할 수도 있음, 확인 후 삭제 예정)
  @extend_schema(
    tags = ["1.1 현위치 표시"],
    parameters=[
      OpenApiParameter(name="x", description="경도", required=True, type=float),
      OpenApiParameter(name="y", description="위도", required=True, type=float),
    ],
    responses={200: DongResponseSerializer},
    description="클라이언트 위치(경도, 위도) 기준 카카오 동 반환",
  )

  @action(detail=False, methods=["GET"])
  def locate(self, request):
    x = request.query_params.get("x")
    y = request.query_params.get("y")

    try:
        data = kakao.locate_dong(x=float(x), y=float(y))
    except ValueError:
        return Response({"detail": "경도/위도는 숫자여야 합니다."}, status=400)
    except requests.RequestException as e:
        return Response({"detail": f"카카오 API 호출 실패: {e}"}, status=502)

    # Kakao 응답에서 동 이름 뽑기 (region_3depth_name => ‘○○동’)
    docs = data.get("documents", [])
    if docs:
        primary = docs[0]
        dong = primary.get("region_3depth_name")
        code = primary.get("code") #코드는 필요없을 수 있음 확인 후 삭제 예정

    if not dong:
        return Response({"detail": "동 정보를 찾지 못했습니다."}, status=404)
    return Response({"dong": dong, "code": code}, status=200)

  # 1.2 구글 장소 검색 → place 정보 반환
  @extend_schema(
    tags=["1.2 구글 장소 검색"],
    parameters=[
        OpenApiParameter(name="q", description="검색어(textQuery)", required=True, type=str),
        OpenApiParameter(name="x", description="경도", required=True, type=float),
        OpenApiParameter(name="y", description="위도", required=True, type=float),
        OpenApiParameter(name="radius", description="반경거리", required=False, type=float), #거리
        OpenApiParameter(name="priceLevel", description="가격", required=False, type=str), #가격 "PRICE_LEVEL_INEXPENSIVE", "PRICE_LEVEL_MODERATE"
        #후기, #인기순 정렬 코드 작성 필요
    ],
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
  # 1) 구글 장소의 위도경도를 이용하여 카카오맵에 검색하여 카테고리 확인 2) 그 외 카테고리별로 호출!
  @extend_schema(
    tags = ["1.2 장소 카테고리별 추천"],
    parameters=[
      OpenApiParameter(name="x", description="경도", required=True, type=float),
      OpenApiParameter(name="y", description="위도", required=True, type=float),
      OpenApiParameter(name="category_group_code", description="카테고리 코드", required=True, type=str),
      OpenApiParameter(name="radius", description="반경거리", required=True, type=int),
    ],
    description="구글 장소의 위도경도를 이용하여 카테고리별 장소 반환",
  )

  #CT1 문화시설, AT4 관광명소, FD6 음식점, CE7 카페
  @action(detail=False, methods=["GET"])
  def recommend(self, request):
    x = request.query_params.get("x")
    y = request.query_params.get("y")
    category = request.query_params.get("category_group_code")
    radius = request.query_params.get("radius")

    if not (x and y):
        return Response({"detail": "경도, 위도가 필요합니다."}, status=400)
    try:
        data = kakao.recommend_place(x=float(x), y=float(y), category_group_code=category, radius=radius)
    except requests.RequestException as e:
        return Response({"detail": f"카카오 API 호출 실패: {e}"}, status=502)

    return Response({"data": data}, status=200) #=> 가공 필요, 구글과 어떻게 연계할지,,!

class PlaceRouteViewSet(viewsets.GenericViewSet):
  queryset = Place.objects.all()
  serializer_class = PlaceSerializer

  # 6.1 등록된 카드의 동선 안내
  @extend_schema(
    tags = ["등록된 카드의 동선 안내"],
    request=PlaceRouteSerializer,
    description="출발지, 경유지, 도착지 좌표로 경로 안내",
 )

  @action(detail=False, methods=["POST"])
  def path(self, request):
    # 1) 유효성 검사
    route = PlaceRouteSerializer(data=request.data)
    route.is_valid(raise_exception=True)
    data = route.validated_data
    transport = data["transport"]
    print(f"[DEBUG] 실행된 API: {transport}")

    # 2) 스웨거 페이로드, API 호출
    try:
        if transport == "car": # 카카오내비(자동차, 택시)
            payload = {
                "origin": (data["origin"]["x"], data["origin"]["y"]),                 
                "destination": (data["destination"]["x"], data["destination"]["y"]),       
                "waypoints": [
                    (wp["x"], wp["y"])
                    for wp in data.get("waypoints", [])
                ],
                "priority": data["priority"],             
                "alternatives": data.get("alternatives", True),
            }

            data = kakao.car_route(**payload) # **으로 언팩하면 함수와 일치하게 호출됌,,!

            # 3) 정보 가공(택시요금, 통행거리, 소요시간)
            docs = data.get("routes", [])
            routes_info = []

            taxi_fare = None
            distance = None
            car_duration = None

            for route in docs:
                summary = route.get("summary", {})
                fare = summary.get("fare", {}) or {}

                taxi_fare = fare.get("taxi", 0) + fare.get("toll", 0) # 택시요금 + 톨비
                distance = round(summary.get("distance", 0)/1000, 1) # 0.0km
                car_duration = round(summary.get("duration", 0)/60) # 0분

                routes_info.append({
                    "taxi_fare": taxi_fare,
                    "distance": f"{distance}km",
                    "car_duration": f"{car_duration}분"
                })
            
            if not docs:
                return Response({"detail": "문서 정보를 찾지 못했습니다."}, status=404)

            return Response({"routes": routes_info}, status=200)

        elif transport == "transit":  # 티맵 (대중교통)

            trans = tmap.traffic_route(
                startX=data["origin"]["x"], 
                startY=data["origin"]["y"], 
                endX=data["destination"]["x"], 
                endY=data["destination"]["y"],
                count=1, lang=0, format="json"
            )

            plan = (trans.get("metaData") or {}).get("plan") or {}
            itineraries = plan.get("itineraries") or []
            if not itineraries:
                return Response({"detail": "대중교통 경로 없음"}, status=404)

            routes_info = []

            for itin in itineraries:
                legs = itin.get("legs") or []

                routes_info.append({
                    # 요약 (대중교통 거리, 시간, 환승횟수, 요금)
                    "trans_duration": round(itin.get("totalTime", 0) / 60),
                    "trans_distance": round(itin.get("totalDistance", 0) / 1000, 1),
                    "transfers": itin.get("transferCount", 0),
                    "trans_fare": itin.get("fare", {}).get("regular", {}).get("totalFare", 0),

                    # 도보 (시간, 거리, 걸음 수 0.7m)
                    "walk_time": round(itin.get("totalTime", 0) / 60),
                    "walk_distance": round(itin.get("totalDistance", 0) / 1000, 1),
                    "walk_steps": int(round(itin.get("totalWalkDistance", 0) / 0.7)),  # 보폭 0.7m 가정

                    # 지하철/버스 (노선, 번호)
                    "subway_lines": [l.get("route") for l in legs if l.get("mode") == "SUBWAY"],
                    "bus_numbers": [l.get("route") for l in legs if l.get("mode") == "BUS"],
                })

            return Response({"transit_routes":routes_info}, status=200)
        
        else:
            return Response({"detail": "존재하지 않는 transport 값입니다."}, status=400)
    
    except requests.RequestException as e:
        return Response({"detail": f"외부 API 호출 실패: {e}"}, status=502)