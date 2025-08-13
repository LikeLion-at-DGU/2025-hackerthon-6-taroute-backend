import requests
from django.conf import settings

LOCAL = "https://dapi.kakao.com/v2/local"
ROUTE = "https://apis-navi.kakaomobility.com/v1/directions"

def _headers():
    return {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}

# 1.1 현위치 표시 / region_3depth_name => ‘○○동’
def locate_dong(x, y): 
    params = {"x":x, "y":y}
    r = requests.get(f"{LOCAL}/geo/coord2regioncode.json", headers=_headers(), params=params, timeout=5)
    r.raise_for_status() #200대가 아니면 에러 발생
    return r.json()

# 1.2 장소 카테고리별 추천
CATEGORY = ["CT1", "AT4", "FD6", "CE7"] # 문화시설, 관광명소, 음식점, 카페
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
        {"place_name": p.get("place_name"), "x": p.get("x"), "y": p.get("y")}
        for p in places[:size] #장소 리스트 상한 10개
    ]

def recommend_place(x, y, radius, category_group_code=None, limit=10):
    if not category_group_code or category_group_code == "all":
        codes = CATEGORY
        limit = 3 #검색창 하단 카테고리 추천 수 제한
    else:
        codes = [category_group_code] #카테고리 페이지에서는 10개씩 default

    results = {
        code: _search_category(code, x, y, radius, size=limit) 
        for code in codes
    }
    return results[codes[0]] if len(codes) == 1 else results

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
