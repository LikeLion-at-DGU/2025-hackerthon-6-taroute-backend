import requests
from django.conf import settings

BASE = "https://apis.openapi.sk.com/transit/routes"

def _headers():
    return {
            "appKey": settings.TMAP_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
    }

# 6.1 등록된 카드의 동선 안내(대중교통)
def traffic_route(startX, startY, endX, endY, lang=0, format="json", count=5): 
    payload = {
        "startX":startX, 
        "startY":startY, 
        "endX":endX, 
        "endY":endY,
        "lang": lang,
        "format": format,
        "count": count
    }

    r = requests.post(BASE, headers=_headers(), json=payload, timeout=5)
    r.raise_for_status() #200대가 아니면 에러 발생
    return r.json() 