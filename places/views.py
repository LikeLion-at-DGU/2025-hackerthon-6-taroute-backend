import re
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import viewsets, status, mixins
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.contrib.sessions.models import Session
from rest_framework.permissions import AllowAny
from django.utils import timezone
import networkx as nx



from .models import PopularKeyward, Place

from .serializers import *
from .services import kakao, tmap, google, openai, tsp_route

import requests
import json

from django.shortcuts import get_object_or_404
class PlaceViewSet(viewsets.ViewSet):
  
  serializer_class = PlaceMixin #unable to guess serializer 경고 해소용
  # 메인 페이지
  ######################################################################################
  @extend_schema(
    tags = ["🔥메인페이지"], summary="1.1 요즘 뜨는 운명의 장소 / 주변에 가볼만한 곳",
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
    
    # if params.get("many_review") == True:
    #     try:
    #         data = kakao.many_review_sort(data)
    #     except requests.RequestException as e:
    #         # 구글 실패하더라도 카카오 결과는 반환
    #         return Response(
    #             {"detail": f"구글 리뷰 조회 실패: {e}", "data": data},
    #             status=207,  # Multi-Status
    #         )
        
    return Response({"data": data}, status=200) 
  
  @extend_schema(tags= ["🔥메인페이지"], summary="1.2 현재 인기있는 검색어")
  @action(detail=False, methods=["GET"])
  def top10_keyword(self, request):
    popular_keywords = PopularKeyward.objects.all().order_by("-click_num")[:10]
    return Response({"place_name" : keyword.place_name} for keyword in popular_keywords)
  
  @extend_schema(
    tags=["🔥메인페이지"], summary="1.3 검색바 / 구글 장소 검색",
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
        return Response({"detail": "검색 결과 없음", "google_place": []}, status=204)

    return Response({"google_place" : places}, status=200)
  
  @extend_schema(tags = ["🔥메인페이지"], summary="1.4 장소 찜(저장)하기", parameters=[SavePlaceSerializer])
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

        # 현재 세션 ID 출력
        session_key = request.session.session_key
        print(f"Current session key: {session_key}")
                
        request.session['saved_places'][place_id] = data
        request.session.modified = True  # 세션 변경사항 저장
        data["session_key"] = session_key
        # Response 객체 대신 딕셔너리 사용
        response_data = {"data": data, "session_key": session_key, "message": "장소가 성공적으로 저장되었습니다."}

        # JsonResponse 사용
        from django.http import JsonResponse
        response = JsonResponse(response_data, status=200)

        # 쿠키 설정
        response.set_cookie('sessionid', session_key, httponly=False, samesite='Lax')


    except requests.RequestException as e:
        return Response({"detail": f"구글 API 호출 실패: {e}"}, status=502)
    except Exception as e:
        return Response({"detail": f"오류 발생: {str(e)}"}, status=400)

    return response

    

  @extend_schema(
    tags = ["🔥메인페이지"], 
    parameters=[OpenApiParameter(name="session_key", description="세션 키", required=True, type=str)],
    summary="1.4 저장한 장소 정보 가져오기"
  )
  @action(detail=False, methods=["GET"])
  def get_saved_places(self, request):

    session_key = request.query_params.get('session_key')
    
    try:
        session = Session.objects.get(session_key=session_key)
        session_data = session.get_decoded()
        saved_places = session_data.get('saved_places', {})
        return Response({'session_key': session_key, 'places': saved_places})
    except Session.DoesNotExist:
        return Response({'error': '세션을 찾을 수 없습니다.'}, status=404)

  # 위치 페이지
  ######################################################################################################
  @extend_schema(
        tags=["🔥위치페이지"], summary="2.1 현위치 표시", 
        parameters=[OpenApiParameter(name="query", description="검색할 지역명", required=True, type=str)])
  @action(detail=False, methods=["GET"])
  def locate(self, request):
    query = request.query_params.get("query")

    try:
        address_list = kakao.locate_dong(query)
    except requests.RequestException as e:
        return Response({"detail": f"카카오 API 호출 실패: {e}"}, status=502)

    return Response({"address_list": address_list}, status=200)

  # 카테고리 페이지
  ######################################################################################################
  @extend_schema(
        tags=["🔥카테고리페이지"], summary="2.2 카테고리별 장소 검색 및 필터링",
        parameters=[CategorySearchSerializer],
        responses={200: CategoryPlaceSerializer(many=True)}
  )
  @action(detail=False, methods=["GET"])
  def category_search(self, request):
    """카테고리별 장소 검색 및 필터링
    
    - 검색어 기반 또는 카테고리별 장소 검색
    - 거리, 방문시간, 방문요일 필터링 지원
    - 다양한 정렬 옵션 제공
    """
    query = CategorySearchSerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    params = query.validated_data

    # 위치 정보 필수 체크
    if not params.get("x") or not params.get("y"):
        return Response({"detail": "위치 정보(x, y)가 필요합니다."}, status=400)

    try:
        # 구글 API 호출을 위한 파라미터 구성
        search_params = {
            "text_query": params.get("text_query"),
            "category": params.get("category", "all"),
            "x": params["x"],
            "y": params["y"],
            "radius": params.get("radius", 5000),
            "distance_filter": params.get("distance_filter", "all"),
            "visit_time_filter": params.get("visit_time_filter", "all"),
            "visit_days_filter": params.get("visit_days_filter"),
            "sort_by": params.get("sort_by", "relevance"),
            "limit": params.get("limit", 20)
        }

        # 구글 API 호출
        places = google.search_category_places(**search_params)
        
        if not places:
            return Response({
                "detail": "검색 결과가 없습니다.",
                "places": [],
                "total_count": 0,
                "filters_applied": {
                    "category": params.get("category"),
                    "distance_filter": params.get("distance_filter"),
                    "visit_time_filter": params.get("visit_time_filter"),
                    "visit_days_filter": params.get("visit_days_filter"),
                    "sort_by": params.get("sort_by")
                }
            }, status=200)

        return Response({
            "places": places,
            "total_count": len(places),
            "filters_applied": {
                "category": params.get("category"),
                "distance_filter": params.get("distance_filter"),
                "visit_time_filter": params.get("visit_time_filter"),
                "visit_days_filter": params.get("visit_days_filter"),
                "sort_by": params.get("sort_by")
            }
        }, status=200)

    except requests.RequestException as e:
        return Response({"detail": f"외부 API 호출 실패: {e}"}, status=502)
    except Exception as e:
        return Response({"detail": f"검색 중 오류 발생: {str(e)}"}, status=500)

  @extend_schema(
        tags=["🔥카테고리페이지"], summary="2.3 카테고리 페이지에서 장소 찜하기",
        parameters=[SavePlaceSerializer]
  )
  @action(detail=False, methods=["GET"])
  def category_save_place(self, request):
    """카테고리 페이지에서 장소 찜하기 (기존 save_place와 동일한 로직)"""
    place_id = request.query_params.get('place_id')

    if not place_id:
        return Response({"detail": "place_id가 필요합니다."}, status=400)

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
        
        return Response({
            "data": data, 
            "message": "장소가 성공적으로 찜 목록에 추가되었습니다.",
            "is_new": created,
            "total_saves": popularKeyward.click_num
        }, status=200)

    except requests.RequestException as e:
        return Response({"detail": f"구글 API 호출 실패: {e}"}, status=502)
    except Exception as e:
        return Response({"detail": f"오류 발생: {str(e)}"}, status=400)

  @extend_schema(
        tags=["🔧디버깅"], summary="구글 API 연결 테스트",
        parameters=[OpenApiParameter(name="test", description="테스트 파라미터", required=False, type=str)]
  )
  @action(detail=False, methods=["GET"])
  def debug_google_api(self, request):
    """구글 API 연결 상태 디버깅"""
    from django.conf import settings
    import requests
    
    # API 키 확인
    google_api_key = settings.GOOGLE_API_KEY
    if not google_api_key:
        return Response({
            "error": "GOOGLE_API_KEY가 설정되지 않았습니다.",
            "debug_info": {
                "api_key_exists": False,
                "api_key_length": 0
            }
        }, status=500)
    
    # 간단한 구글 Places API 테스트
    test_url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "X-Goog-Api-Key": google_api_key,
        "Content-Type": "application/json",
        "Referer": "http://localhost:8000",
        "X-Goog-FieldMask": "places.displayName,places.id,places.formattedAddress,places.location"
    }
    test_body = {
        "textQuery": "스타벅스 강남역",
        "languageCode": "ko",
        "regionCode": "KR",
        "locationBias": {
            "circle": {
                "center": {"latitude": 37.497942, "longitude": 127.027619},
                "radius": 1000
            }
        }
    }
    
    try:
        response = requests.post(test_url, headers=headers, json=test_body, timeout=10)
        
        return Response({
            "debug_info": {
                "api_key_exists": True,
                "api_key_length": len(google_api_key),
                "api_key_prefix": google_api_key[:10] + "..." if len(google_api_key) > 10 else google_api_key,
                "google_api_status": response.status_code,
                "google_api_response": response.json() if response.status_code == 200 else response.text[:500],
                "test_query": "스타벅스 강남역"
            }
        }, status=200)
        
    except Exception as e:
        return Response({
            "error": f"구글 API 호출 실패: {str(e)}",
            "debug_info": {
                "api_key_exists": True,
                "api_key_length": len(google_api_key),
                "api_key_prefix": google_api_key[:10] + "..." if len(google_api_key) > 10 else google_api_key
            }
        }, status=500)

# 타로 페이지
###########################################################################################################
class ChatViewSet(viewsets.ViewSet):
  #4. 타루 챗봇 대화
  # 호출 시 타로마스터 ai의 질문 목록을 저장합니다.
  serializer_class = ChatSerializer

  @extend_schema(
    tags = ["🔥타로페이지"], summary="4.1 타루 챗봇 질문 리스트 저장",
    description="타로마스터 ai가 4지선다 질문 5개 목록을 생성합니다.",
  )
  @action(detail=False, methods=["POST"])
  def slot_question(self, request):

    try:
        data = openai.create_question()
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
    return Response({"message": "질문 세트가 세션에 저장되었습니다.", "chats":session},status=200)
  
  # 세션 확인용
#   @extend_schema(tags = ["🔥타로페이지"], summary="4.2 저장한 질문/키워드 정보 가져오기")
#   @action(detail=False, methods=["GET"])
#   def get_chats(self, request):
#     chats = request.session.get('taru_chat', {})
#     return Response({'chats': chats})
  
  @extend_schema(
    tags = ["🔥타로페이지"], summary="4.2 타로 카드 20장 추천",
    request= CardSelectSerializer,
    description="입력한 답변에서 추출한 키워드를 기반으로 카드 20장을 추천합니다.",
  )
  @action(detail=False, methods=["POST"])
  def card_select(self, request):

    # 1) 입력한 답변에서 키워드 추출
    input = request.data.get("input_text")
    lang = (request.data.get("lang") or "ko").lower()
    x = request.data.get("x")
    y = request.data.get("y")

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
    
    # 세션에 저장
    taru_chat = request.session.get("taru_chat", {})
    taru_chat.update(parsed_text)
    request.session["taru_chat"] = taru_chat
    request.session.modified = True

    try:
        # 2) 구글 api에 접근해서 리뷰 목록 20개 뽑기
        s = request.session.get('taru_chat', {}) or {}
        chats_radius   = s.get("radius", 0)

        # chats_radius에서 숫자를 추출하여 거리 계산
        if isinstance(chats_radius, str):
            numbers = re.findall(r'\d+', chats_radius)
            if numbers:
                value = int(numbers[0])
                if "시간" in chats_radius:
                    radius = value * 12000 # 1시간=12km=12000m
                elif "분" in chats_radius:
                    radius = value / 60 * 12000
            else:
                radius = 2000  # 숫자를 찾지 못한 경우
        else:
            radius = 2000  # 문자열이 아닌 경우
        print(f"radius {radius}")
        places = google.search_slot(x=x, y=y, radius=radius)

        # ------------3) 장소의 리뷰에 하나씩 접근해서 세션에 저장된 값들이 포함되어있다면 장소 id, 이름 반환-----------
        
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
        p_id = set() # id 중복 체크 위한 set
        matches = google.keyword_match(places, keywords) # 키워드 매칭
        add_count = 0 # 장소 저장 카운트

        for p in matches:
            place_id = p.get('place_id')
            
            if place_id and place_id not in p_id:
                print(f"[MATCH] {p.get('place_name')} ({len(p.get('matches', []))} hits)")
                for hit in p.get('matches', [])[:3]:
                    print(
                        f" - 리뷰#{hit['review_index']} "
                        f"키워드='{hit['keyword']}' (원문='{hit['source_text']}') "
                        f"내용='{hit['context']}'"
                    )
                
                select.append({
                    "select_num" : len(select) + 1,
                    "place_id" : place_id,
                    "place_name" : p.get('place_name'),
                    "place_photos" : p.get('place_photos')
                })
                p_id.add(place_id)
                add_count += 1

        # print(f"{add_count}개 장소 추가됨, 현재 총 {len(select)}개")

        while len(select) < 20 :
            places_two = google.search_slot(x=x, y=y, radius=radius*1.5)
            for t in places_two:
                t_id = t.get('place_id')
                if t_id and t_id not in p_id:
                    select.append({
                        "select_num" : len(select) + 1,
                        "place_id" : t_id,
                        "place_name" : t.get('place_name'),
                        "place_photos" : t.get('place_photos')
                    })
                    p_id.add(t_id)
                    add_count += 1

                    if len(select) >= 20: break
            
            # print(f"이번 시도에서 {add_count}개 장소 추가됨, 현재 총 {len(select)}개")
        
            if add_count == 0:  # 더 이상 새로운 장소를 찾지 못하면 종료
                print("더 이상 새로운 장소를 찾을 수 없습니다.")
                break
    
    except requests.HTTPError as e:
        return Response({"detail": f"Google Places API 호출 실패: {e.response.status_code} {e.response.text}"}, status=502)
    except requests.RequestException as e:
        return Response({"detail": f"Google Places API 호출 실패: {e}"}, status=502)

    if not places:
        return Response({"google_place": []}, status=204)
    return Response({"select" : select}, status=200)

# 동선 페이지
###############################################################################################################################
class PlaceRouteViewSet(viewsets.GenericViewSet):
  queryset = Place.objects.all()
  serializer_class = PlaceRouteSerializer

  # 6.1 등록된 카드의 동선 안내
  @extend_schema(
    tags = ["🔥동선페이지"], summary="6.1 등록된 카드의 동선 안내",
    parameters=[PlaceRouteSerializer],
    description="출발지, 도착지 좌표로 경로 안내(POST=자동차, 대중교통, 도보)",
 )

  @action(detail=False, methods=["POST"])
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
    params = dict( #자동차, 대중교통
                startX=ox, 
                startY=oy,
                endX=dx,
                endY=dy,
                count=1, lang=0, format="json"
            )
    
    try:
        if transport == "car": # 카카오내비(자동차)
            car_routes = tmap.car_route(**params)
            if not car_routes:
                return Response({"detail": "문서 정보를 찾지 못했습니다."}, status=404)
            return Response({"car_routes": car_routes}, status=200)

        elif transport == "transit":  # 티맵 (대중교통)
            traffic_routes = tmap.traffic_route(**params)
            if not traffic_routes:
                return Response({"detail": "대중교통 경로 없음"}, status=404)

            return Response({
                "transit_summary": traffic_routes.get("transit_summary"),
                "segments": traffic_routes.get("segments"),
            }, status=200)
        
        elif transport == "walk": # 티맵(도보)
            params_w = dict( #도보
                startX=ox, 
                startY=oy,
                endX=dx,
                endY=dy,
                startName = data["startName"],
                endName = data["endName"]
            )

            walk_data = tmap.walk_route(**params_w)
            return Response({"data":walk_data}, status=200)
        
        else:
            return Response({"detail": "존재하지 않는 transport 값입니다."}, status=400)
    
    except requests.RequestException as e:
        return Response({"detail": f"외부 API 호출 실패: {e}"}, status=502)


  # 6.2 AI 추천 받기 TSP 알고리즘
  @extend_schema(
    tags = ["🔥동선페이지"], 
    parameters=[
        OpenApiParameter(name="session_key", description="세션 키", required=True, type=str),
        OpenApiParameter(name="day", description="방문요일", required=True, type=str),
        OpenApiParameter(name="x", description="경도", required=True, type=float),
        OpenApiParameter(name="y", description="위도", required=True, type=float)
    ],
    summary="6.2 AI 추천 받기 / TSP 알고리즘"
  )
  @action(detail=False, methods=["GET"])
  def ai_routes(self, request):

    session_key = request.query_params.get('session_key')
    day = request.query_params.get('day')
    x = request.query_params.get('x')
    y = request.query_params.get('y')

    try:
        session = Session.objects.get(session_key=session_key)
        session_data = session.get_decoded()
        data = session_data.get('saved_places', {})

        # 1) 세션에 담긴 장소에서 사용자가 선택한 요일의 영업정보 가져오기
        filter_data = tsp_route.filter(day, data)

        # 2) NetworkX TSP 알고리즘으로 가게간의 직선거리를 엣지 가중치로 최적 경로 구하기
        routes = tsp_route.tsp_route(filter_data, cycle=False, mylat=float(x), mylng=float(y))
        path = tsp_route.route_info(filter_data, routes)

        return Response({'session_key': session_key, 'result': path})
    except Session.DoesNotExist:
        return Response({'error': '세션을 찾을 수 없습니다.'}, status=404)

    
# URL 세션
######################################################################
# class RouteSnapshotViewSet(mixins.CreateModelMixin,
#                            mixins.RetrieveModelMixin,
#                            viewsets.GenericViewSet):
#     queryset = RouteSnapshot.objects.all()
#     serializer_class = RouteSnapshotSerializer
#     permission_classes = [AllowAny]
#     lookup_field = "short"


#     @extend_schema(
#         tags = ["🔥기타페이지"], summary="6.1 등록된 카드의 동선 안내 URL",
#         request=[RouteSnapshotCreateSerializer],
#         description="출발지, 도착지 좌표로 경로 안내(POST=자동차, 대중교통, 도보)",
#     )
#     def create(self, request, *args, **kwargs):
#         s = RouteSnapshotCreateSerializer(data=request.data)
#         s.is_valid(raise_exception=True)

#         # 세션 사용자 식별 정도만 저장(로그인 없음)
#         session_key = request.session.session_key
#         if not session_key:
#             request.session.create()
#             session_key = request.session.session_key

#         # 중복 슬러그 발생 시 재시도
#         for _ in range(3):
#             try:
#                 snap = RouteSnapshot.objects.create(
#                     session_key=session_key,
#                     params=s.validated_data["params"],
#                     result=s.validated_data["result"],
#                 )
#                 break
#             except Exception:
#                 continue

#         return Response(RouteSnapshotSerializer(snap).data, status=status.HTTP_201_CREATED)

#     def retrieve(self, request, short=None):
#         snap = self.get_object()
#         if snap.expires_at and snap.expires_at < timezone.now():
#             return Response({"detail": "링크가 만료되었습니다."}, status=410)
#         return Response(RouteSnapshotSerializer(snap).data)
    
    # {
    #     "params": {
    #         "start": {"name":"중앙대 정문", "x":126.9599, "y":37.5058},
    #         "end":   {"name":"흑석역 3번출구", "x":126.9639, "y":37.5086},
    #         "radius": 2000,
    #         "filters": {"transport":"car", "budget":"~10000", "vibe":"데이트"}
    #     },
    #     "result": {
    #         "time": 6,
    #         "distance": 1100,
    #         "cost": 5000,
    #         "stops": [
    #         {"idx":1,"name":"선우카페","x":126.9618,"y":37.5066,"eta_min":2},
    #         {"idx":2,"name":"필동밤","x":126.9627,"y":37.5074,"eta_min":2},
    #         {"idx":3,"name":"흑석역 3번출구","x":126.9639,"y":37.5086,"eta_min":2}
    #         ],
    #         "cards": [
    #         {"title":"데이트 ☕ → 산책 → 귀가","desc":"따뜻한 라떼 후 캠퍼스 산책"},
    #         {"title":"대안 루트","desc":"비 오면 카페 2곳"}
    #         ],
    #         "polyline": [[126.9599,37.5058],[126.9618,37.5066],[126.9627,37.5074],[126.9639,37.5086]]
    #     }
    # }  

