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
