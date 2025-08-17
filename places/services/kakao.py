import requests
from django.conf import settings

from ..services import google
from ..models import SubwayLines
from django.db.models import Q #검색어 일부가 포함된 지하철역 검색  


LOCAL = "https://dapi.kakao.com/v2/local"
ROUTE = "https://apis-navi.kakaomobility.com/v1/directions"

def _headers():
    return {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}

# 1.1 현위치 표시
def locate_dong(query): 
    params = {"query":query}
    r = requests.get(f"{LOCAL}/search/address.json", headers=_headers(), params=params, timeout=5)
    r.raise_for_status() #200대가 아니면 에러 발생
    data = r.json()
    address_list = []

    #DB에서 지하철역정보 검색하여 위도경도 반환
    q = query.strip()
    if q.endswith("역"): #00역인 경우 '역' 제거
        q = q[:-1].strip()

    subway = SubwayLines.objects.filter(
        Q(station__icontains=q)
    )
    stations = subway[:10]  # 너무 많이 안 주도록 상한
    for s in stations:
        address_list.append({
            "address_name": f"{s.station} ({s.line})",
            "x": s.longitude,
            "y": s.latitude,
        })

    if data["documents"]: 
        #카카오API의 위도경도 목록
        for document in data["documents"]:
            address_list.append({
                "address_name" : document.get("address_name"),
                "x" : document.get("x"),
                "y" : document.get("y")
            })
    
    return address_list

# 1.2 장소 카테고리별 추천
CATEGORY_LABELS = {
    "CT1": "문화시설",
    "AT4": "관광명소",
    "FD6": "음식점",
    "CE7": "카페",
}
CATEGORY = list(CATEGORY_LABELS.keys())

def _search_category(category, x, y, radius, size=10):
    params = {
        "category_group_code": category,
        "x": x,
        "y": y,
        "radius": radius,
        "size":size,
    }
    r = requests.get(f"{LOCAL}/search/category.json", headers=_headers(), params=params, timeout=5)
    r.raise_for_status()
    places = (r.json() or {}).get("documents", [])

    # 2) place_name, x, y 반환 => 구글 장소 세부데이터 요청 필요 (places/google_place)
    return [
        {"place_name": p.get("place_name"), "address": p.get("address_name"), "x": p.get("x"), "y": p.get("y")}
        for p in places[:size] #장소 리스트 상한 10개
    ]

def recommend_place(x, y, radius=2000, category_group_code=None, limit=7):
    if not category_group_code or category_group_code == "all":
        codes = CATEGORY
        limit = 3 #검색창 하단 카테고리 추천 수 제한
    else:
        codes = [category_group_code] #카테고리 페이지에서는 10개씩 default

    results = {
        CATEGORY_LABELS[code]: _search_category(code, x, y, radius, size=limit) 
        for code in codes
    }
    return results[CATEGORY_LABELS[codes[0]]] if len(codes) == 1 else results

# 카카오 recommend 후 구글 search_place(리뷰순정렬)
def many_review_sort(place_list):
    review_sort = []
    for p in place_list:  # 각 장소 딕셔너리 순회
      print("place_name:", p.get("place_name"))
      try:
          res = google.search_place(
              text_query = p["place_name"],
              x = float(p["x"]),
              y = float(p["y"]),
              radius = 500
          )
          if isinstance(res, list) and len(res) > 0:
            count = res[0].get("review_count", 0)
      except requests.RequestException:
          count = 0
      review_sort.append({**p, "review_count": count}) # 구글 리뷰수를 리스트에 추가

      review_sort.sort(key=lambda v: v.get("review_count", 0), reverse=True) # 오름차순 정렬 후 반환

    return review_sort

# 6.1 등록된 카드의 동선 안내(택시, 자동차)
def car_route(origin:str, destination:str):
    params = {
        "origin": origin,
        "destination": destination,
    }
    r = requests.get(f"{ROUTE}", headers=_headers(), params=params, timeout=5)
    r.raise_for_status()

    # 3) 자동차 정보 가공(소요시간(분), 통행거리(km), 택시요금(원))
    data = r.json().get("routes", [])
    car_routes = []
    summary = data[0].get("summary", {})
    fare = summary.get("fare", {}) or {}

    taxi_fare = fare.get("taxi", 0) + fare.get("toll", 0) # 택시요금 + 톨비
    distance = round(summary.get("distance", 0)/1000, 1) # 0.0km
    car_duration = round(summary.get("duration", 0)/60) # 0분

    car_routes.append({
        "car_duration": f"{car_duration}분",
        "distance": f"{distance}km",
        "taxi_fare": f"{taxi_fare:,}원",
    })

    return car_routes
