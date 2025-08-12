import requests
from django.conf import settings

LOCAL = "https://dapi.kakao.com/v2/local"
ROUTE = "https://apis-navi.kakaomobility.com/v1/waypoints/directions"

def _headers():
    return {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}

# 1.1 현위치 표시
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
def car_route(origin, destination, waypoints=None, priority="RECOMMEND", alternatives=True):
    params = {
         "origin": {
            "x": origin[0],
            "y": origin[1]
        },
        "destination": {
            "x": destination[0],
            "y": destination[1]
        },
        "priority": priority,
        "alternatives": alternatives,
    }

    # 경유지
    if waypoints:
        params["waypoints"] = [
            {
                "x": wp[0],
                "y": wp[1]
            }
            for wp in waypoints
        ]

    r = requests.post(f"{ROUTE}", headers=_headers(), json=params, timeout=5)
    r.raise_for_status()
    return r.json()
