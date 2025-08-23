import re
import requests
from django.conf import settings

BASE = "https://apis.openapi.sk.com/transit/routes"
ROUTE = "https://apis.openapi.sk.com/tmap/routes"

def _headers():
    return {
            "appKey": settings.TMAP_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
    }

# 6.1 등록된 카드의 동선 안내(도보)
# 지도에 마커찍기 위한 위도경도 포인트 추출
def map_points(features):
    result = []
    for f in features:
        geom = f.get("geometry", {})
        props = f.get("properties", {})

        if geom.get("type") == "Point":
            coords = geom.get("coordinates", [])
            if not coords:
                continue

            item = {
                "name": props.get("name") or props.get("nearPoiName") or "",
                "lat": coords[1],   #
                "lng": coords[0]
            }
            result.append(item)
    return result


def walk_route(startX, startY, endX, endY, startName=None, endName=None):
    payload = {
        "startX":startX, 
        "startY":startY, 
        "endX":endX, 
        "endY":endY,
        "startName":startName,
        "endName":endName
    }
    # f"{BASE}:searchNearby"
    r = requests.post(f"{ROUTE}/pedestrian?version=1", headers=_headers(), json=payload, timeout=5)
    r.raise_for_status()
    features = r.json().get("features") or []
    data = features[0].get("properties") or {}

    walk_distance = round((data.get("totalDistance") or 0)/1000, 1)
    walk_time = round((data.get("totalTime") or 0) / 60)
    walk_step = round((data.get("totalDistance") or 0) / 0.7)

    points = map_points(features)

    walk_routes = {
        "walk_distance" : f"{walk_distance}km",
        "walk_time" : f"{walk_time}분",
        "walk_step" : f"{walk_step:,}걸음",
        "points" : points
    }
    return walk_routes


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

    data = (r.json().get("metaData") or {}).get("plan") or {}
    itineraries = (data.get("itineraries") or [])
    if itineraries:
        itin = itineraries[0]
        legs = itin.get("legs") or []
    else:
        legs = []
        legs = itin.get("legs") or []
    
    # 대중교통 요약 (총시간, 총거리, 총요금)
    trans_time = round(itin.get("totalTime", 0) / 60)
    trans_distance = round(itin.get("totalDistance", 0) / 1000, 1)
    trans_fare = itin.get("fare", {}).get("regular", {}).get("totalFare", 0)

    # 구간별 시간, 거리, 노선번호, 승하차정보
    segments = []
    for l in legs:
        mode = l.get("mode")
        section_time = round(l.get("sectionTime")/60)
        start = l.get("start") or {}
        end = l.get("end") or {}

        seg = {
            "mode": mode, # WALK/SUBWAY/BUS
            "section_time" : f"{section_time}분", # 구간시간(분)
        }

        if mode == "SUBWAY":
            seg.update({
                "subway_line" : l.get("route"), # 수도권3호선
                "start_station": start.get("name"), "start_slon": start.get("lon"), "start_slat": start.get("lat"),
                "end_station": end.get("name"), "end_slon": end.get("lon"), "end_slat": end.get("lat")
            })
        elif mode == "BUS":
            bus_line = l.get("route") or ""
            mnum = re.search(r"\d+", bus_line) # 간선:152에서 번호만 추출
            bus_no = mnum.group(0) if mnum else bus_line
            seg.update({
                "bus_number" : bus_no,
                "start_stop": start.get("name"), "start_blon": start.get("lon"), "start_blat": start.get("lat"),
                "end_stop": end.get("name"), "end_blon": end.get("lon"), "end_blat": end.get("lat")
            })
        
        segments.append(seg)

    return {
        # 총시간, 총거리, 총요금, 구간별 상세
        "transit_summary" : {
            "trans_time" : f"{trans_time}분",
            "trans_distance" : f"{trans_distance}km",
            "trans_fare" : f"{trans_fare:,}원"
        },
        "segments" : segments
    }


# 6.1 등록된 카드의 동선 안내(자동차)
def car_route(startX, startY, endX, endY, lang=0, format="json", count=5): 
    payload = {
        "startX":startX, 
        "startY":startY, 
        "endX":endX, 
        "endY":endY,
        "lang": lang,
        "format": format,
        "count": count
    }

    r = requests.post(ROUTE, headers=_headers(), json=payload, timeout=5)
    r.raise_for_status() #200대가 아니면 에러 발생

    data = r.json()

    features = data.get("features") or []
    properties = features[0].get("properties") or {}
    car_distance = round(properties.get("totalDistance", 0)/1000, 1) # 0.0km
    car_time = round(properties.get("totalTime", 0)/60) # 0분
    car_fare = properties.get("taxiFare", 0) + properties.get("totalFare", 0) # 택시요금 + 톨비

    car_routes = []

    car_routes.append({
        "car_duration": f"{car_time}분",
        "distance": f"{car_distance}km",
        "taxi_fare": f"{car_fare:,}원"
    })

    return car_routes