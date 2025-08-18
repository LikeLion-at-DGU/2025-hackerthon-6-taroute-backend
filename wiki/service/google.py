from django.conf import settings
import requests

from core import times
from core.distance import calculate_distance
from places.models import PopularKeyward

BASE = "https://places.googleapis.com/v1/places"

def _headers():
    return {
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Goog-FieldMask": "places.displayName,places.id,places.userRatingCount,places.nationalPhoneNumber,places.location,places.regularOpeningHours,places.rating,places.photos,places.priceRange,places.formattedAddress,places.types,places.reviews,places.priceLevel",
    }

def search_place(place_name, latitude, longitude, radius, rankPreference=None, priceLevel=None):
    
    body = {
        "textQuery": place_name,
        "languageCode": "ko",
        "rankPreference": rankPreference, #[거리순정렬] RELEVANCE(검색관련성) / DISTANCE(거리순)
        "regionCode": "KR",
        "locationBias": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius,  # 반경거리
            }
        },
    }
    r = requests.post(f"{BASE}:searchText", headers=_headers(), json=body, timeout=5)
    r.raise_for_status()

    data = r.json()
    places = data.get("places", [])

    google_place = []
    
    for p in places[:10]:
        #[인기순정렬] 검색한 장소의 id가 DB에 있을 경우 인기 카운트 횟수를 세서 반환
        p_id = ""
        click_num = 0
        try:
            p_id = PopularKeyward.objects.get(place_id = p.get("id"))
            click_num = p_id.click_num if p_id else 0
        except PopularKeyward.DoesNotExist:
            pass
        
        running_time = p.get("regularOpeningHours", {})
        if not running_time:
            time = "영업시간 정보 없음"
        else:
            time = times.format_running(running_time)

        # 거리 계산 (사용자 위치가 있는 경우)
        user_latitude = latitude
        user_longitude = longitude
        place_latitude = p.get("location", {}).get("latitude")
        place_longitude = p.get("location", {}).get("longitude")

        distance_text = ""
        if user_latitude and user_longitude:
            distance_km = calculate_distance(
                user_latitude, user_longitude,
                place_latitude, place_longitude
            )
            distance_text = f"{distance_km}km"
        
        google_place.append({
            "place_id" : p.get("id"),
            "place_name" : p.get("displayName", {}).get("text"),
            "address" : p.get("formattedAddress"),
            "location" : p.get("location"),
            "rating" : p.get("rating"), #구글 별점 혹시하고 가져옴
            "click_num": click_num, #[인기순정렬]
            "running_time" : time,
            "distance_text" : distance_text
        })
        # 후기순정렬은 후기 많은 순으로!
    
    return google_place

# 사진 URL 생성
def build_photo_url(photo_name: str, max_width_px: int = 800) -> str:
    return (
        f"https://places.googleapis.com/v1/{photo_name}/media"
        f"?key={settings.GOOGLE_API_KEY}&maxWidthPx={max_width_px}"
    )

# 프론트로부터 place_id를 받고 세부 데이터 응답
def search_detail(place_id):
    params = {
        "languageCode": "ko",
        "regionCode": "KR",
        "fields": "id,displayName,formattedAddress,location,regularOpeningHours,photos",
    }
    r = requests.get(f"{BASE}/{place_id}", params=params, headers=_headers(), timeout=5)
    r.raise_for_status()
    p = r.json()

    photos = p.get("photos", [])
    place_photos = {
        build_photo_url(p["name"], max_width_px=800)
        for p in photos
        if p.get("name")
    }

    running_time = p.get("regularOpeningHours", {})
    if not running_time:
        time = "영업시간 정보 없음"
    else:
        time = times.format_running(running_time)

    search_details = {
        "place_name" : p.get("displayName", {}).get("text"),
        "location" : p.get("location"),
        "place_photos" : place_photos,

        # 영업정보
        "address" : p.get("formattedAddress"),
        "running_time" : time,
        "phone_number" : p.get("nationalPhoneNumber"),   

        "rating" : p.get("rating") #구글 별점 혹시하고 가져옴
    }

    return search_details