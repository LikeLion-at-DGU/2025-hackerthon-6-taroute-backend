import requests
from django.conf import settings

BASE = "https://dapi.kakao.com/v2/local"

def _headers():
    return {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}

def locate_dong(x, y): 
    params = {"x":x, "y":y}
    r = requests.get(f"{BASE}/geo/coord2regioncode.json", headers=_headers(), params=params, timeout=5)
    r.raise_for_status()
    return r.json() 
