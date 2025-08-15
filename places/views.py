from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from rest_framework import viewsets, mixins
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import PopularKeyward, Place

from .serializers import *
from .services import kakao, tmap, google, openai, combined_api

import requests
import json

from django.shortcuts import get_object_or_404
class PlaceViewSet(viewsets.ViewSet):
  @extend_schema(
        tags=["1.1 현위치 표시"], 
        parameters=[OpenApiParameter(name="query", description="검색할 지역명", required=True, type=str)])
  @action(detail=False, methods=["GET"])
  def locate(self, request):
    query = request.query_params.get("query")

    try:
        address_list = kakao.locate_dong(query)
    except requests.RequestException as e:
        return Response({"detail": f"카카오 API 호출 실패: {e}"}, status=502)

    return Response({"address_list": address_list}, status=200)

  # 1.2 구글 장소 검색 → place 정보 반환
  @extend_schema(
    tags=["1.2 검색바 / 구글 장소 검색"],
    parameters=[PlaceSearchSerializer],
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
        return Response({"google_place": []}, status=204)

    return Response({"google_place" : places}, status=200)

  # 1.2 장소 카테고리별 추천, 1.5 지금 이지역에서 뜨고 있는
  # (1) 지금 이지역에서 뜨고 있는 / 리뷰 True, 구글 리뷰가 많은 순으로 위치 기반 카테고리별 3개씩 추천 
  # (2) 주변에 가볼만한 곳 / 카테고리 all 또는 blank 시 카테고리별 3개씩 추천
  @extend_schema(
    tags = ["1.2 주변에 가볼만한 곳, 1.5 지금 이지역에서 뜨고 있는"],
    parameters=[PlaceRecommendSerializer]
  )

  #CT1 문화시설, AT4 관광명소, FD6 음식점, CE7 카페
  @action(detail=False, methods=["GET"])
  def recommend(self, request):
    query = PlaceRecommendSerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    params = query.validated_data

    kakao_params = {
        "x": params["x"],
        "y": params["y"],
        "radius": params["radius"],
        "category_group_code": params.get("category_group_code"),
        "limit": params.get("limit", 10),
    }

    try:
        data = kakao.recommend_place(**kakao_params)
    except requests.RequestException as e:
        return Response({"detail": f"카카오 API 호출 실패: {e}"}, status=502)
    
    if params.get("many_review") == True:
        try:
            data = combined_api.many_review_sort(data)
            print("type(data) ->", type(data))
        except requests.RequestException as e:
            # 구글 실패하더라도 카카오 결과는 반환
            return Response(
                {"detail": f"구글 리뷰 조회 실패: {e}", "data": data},
                status=207,  # Multi-Status
            )
        
    return Response({"data": data}, status=200) 
  
  @extend_schema(tags = ["1.2 장소 저장하기"], parameters=[SavePlaceSerializer])
  @action(detail=False, methods=["GET"])
  def save_place(self, request):
    place_id = request.query_params.get('place_id')

    try:
        data = google.search_detail(place_id)
        place_name = data.get('place_name')

        # set 타입 데이터가 있는지 확인하고 변환
        for key, value in data.items():
            if isinstance(value, set):
                data[key] = list(value)

        popularKeyward, created = PopularKeyward.objects.get_or_create(
            place_id=place_id,
            defaults={'place_name': place_name}
        )

        if not created:
                popularKeyward.click_num += 1
                popularKeyward.save()
            
        # 장소 정보는 세션에 저장
        if 'saved_places' not in request.session:
            request.session['saved_places'] = {}
                
        request.session['saved_places'][place_id] = data
        request.session.modified = True  # 세션 변경사항 저장
        return Response({"data": data, "message": "장소가 성공적으로 저장되었습니다."}, status=200)

    except requests.RequestException as e:
        return Response({"detail": f"구글 API 호출 실패: {e}"}, status=502)
    except Exception as e:
        return Response({"detail": f"오류 발생: {str(e)}"}, status=400)

  @extend_schema(tags = ["1.2 저장한 장소 정보 가져오기"])
  @action(detail=False, methods=["GET"])
  def get_saved_places(self, request):
    # 세션에서 저장된 장소 정보 가져오기
    saved_places = request.session.get('saved_places', {})
    return Response({'places': saved_places})
  
  @extend_schema(tags= ["1.2 실시간 인기검색어"]) #위치기반?
  @action(detail=False, methods=["GET"])
  def top10_keyword(self, request):
    popular_keywords = PopularKeyward.objects.all().order_by("-click_num")[:10]
    return Response({"place_name" : keyword.place_name} for keyword in popular_keywords)


#############################################################################
class ChatViewSet(viewsets.ViewSet):
  #4. 타루 챗봇 대화
  # 호출 시 타로마스터 ai의 질문 목록을 저장합니다.
  @extend_schema(
    tags = ["4.1.1 타루 챗봇 질문 리스트 저장"],
    request=ChatSerializer,
    description="타로마스터 ai가 4지선다 질문 5개 목록을 생성합니다.",
  )
  @action(detail=False, methods=["POST"])
  def slot_question(self, request):
    input = "지금 질문 리스트 5개를 뽑아줘"

    try:
        data = openai.create_question(input_text=input, lang="ko")
    except requests.RequestException as e:
        return Response({"detail": f"openAI API 호출 실패: {e}"}, status=502)
  
    text = ""
    for block in data.get("output", []):
        for c in block.get("content", []):
            text += c.get("text", "")

    parsed_text = json.loads(text).get("questions")

    session = {"questions": parsed_text}
    request.session["taru_chat"] = session
    request.session.modified = True
    return Response({"message": "질문 세트가 세션에 저장되었습니다."},status=200)
  
  @extend_schema(tags = ["4.1.2 저장한 질문/키워드 정보 가져오기"])
  @action(detail=False, methods=["GET"])
  def get_chats(self, request):
    chats = request.session.get('taru_chat', {})
    return Response({'chats': chats})

  @extend_schema(
    tags = ["4.1.3 타루 챗봇 대화 키워드 추출"],
    request=ChatSerializer,
    description="사용자 답변을 받아 ai가 키워드를 추출합니다.",
  )
  @action(detail=False, methods=["POST"])
  def slot_fill(self, request):
    input = request.data.get("input_text")
    lang = (request.data.get("lang") or "ko").lower()
   
    if input is None:
        return Response ({"detail": "input_text가 비어있습니다."}, status=400)
    try:
        data = openai.create_chat(input_text=input, lang=lang)
    except requests.RequestException as e:
        return Response({"detail": f"openAI API 호출 실패: {e}"}, status=502)

    text = ""
    for block in data.get("output", []):
        for c in block.get("content", []):
            text += c.get("text", "")

    parsed_text = json.loads(text)

    taru_chat = request.session.get("taru_chat", {})
    taru_chat.update(parsed_text)
    request.session["taru_chat"] = taru_chat
    request.session.modified = True

    return Response ({"text": parsed_text})
  
  @extend_schema(
    tags = ["4.2 타로 카드 20장 추천"],
    parameters = [PlaceMixin],
    description="추출한 키워드를 기반으로 카드 20장을 추천합니다.",
  )
  @action(detail=False, methods=["GET"])
  def card_select(self, request):
    query = PlaceMixin(data=request.query_params)
    query.is_valid(raise_exception=True)
    x = query.validated_data["x"]
    y = query.validated_data["y"]
    radius = query.validated_data["radius"]

    try:
        # 구글 api에 접근해서 리뷰 목록 20개 뽑기
        places = google.search_slot(x=x, y=y, radius=radius)

        # ------------장소의 리뷰에 하나씩 접근해서 세션에 저장된 값들이 포함되어있다면 장소 id, 이름 반환-----------
        s = request.session.get('taru_chat', {}) or {}
        chats_radius   = s.get("radius")   or ""
        chats_budget   = s.get("budget")   or ""
        chats_vibe     = s.get("vibe")     or ""
        chats_category = s.get("category") or ""
        chats_time     = s.get("time")     or ""

        raw_chats = [chats_radius, chats_budget, chats_vibe, chats_category, chats_time]
        keywords = []
        for src in raw_chats:
            # 공백 기준 분리, 2글자 이상만
            for w in (src or "").split():
                if len(w) >= 2:
                    keywords.append((src, w)) # (원문, 단어)

        select = []  # 조건 만족하는 장소
        matches = google.keyword_match(places, keywords) # 키워드 매칭

        for p in places:
            if matches:
                print(f"[MATCH] {p.get('place_name')} ({len(matches)} hits)")
                for hit in matches[:5]:  # 너무 길면 상위 5개만
                    print(
                        f" - 리뷰#{hit['review_index']} "
                        f"키워드='{hit['keyword']}' (원문='{hit['source_text']}') "
                        f"내용='{hit['context']}'"
                    )
                
                select.append({
                    "select_num" : len(select) + 1,
                    "place_id" : p.get('place_id'),
                    "place_name" : p.get('place_name')
                })
    
    except requests.HTTPError as e:
        return Response({"detail": f"Google Places API 호출 실패: {e.response.status_code} {e.response.text}"}, status=502)
    except requests.RequestException as e:
        return Response({"detail": f"Google Places API 호출 실패: {e}"}, status=502)

    if not places:
        return Response({"google_place": []}, status=204)
    return Response({"select" : select}, status=200)


####################################################################################
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

    # 1) 유효성 검사
    route = PlaceRouteSerializer(data=request.query_params)
    route.is_valid(raise_exception=True)
    data = route.validated_data

    ox, oy = data["origin_x"], data["origin_y"]
    dx, dy = data["destination_x"], data["destination_y"]

    transport = data["transport"]
    print(f"[DEBUG] 실행된 API: {transport}")

    # 2) API 호출
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