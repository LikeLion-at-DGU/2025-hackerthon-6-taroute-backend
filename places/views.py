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