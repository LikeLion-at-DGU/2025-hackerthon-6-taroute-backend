import requests
from django.conf import settings

BASE = "https://places.googleapis.com/v1/places"


def _headers():
    return {
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Goog-FieldMask": "places.displayName,places.id,places.nationalPhoneNumber,places.location,places.regularOpeningHours,places.rating,places.photos,places.priceRange,places.formattedAddress,places.types,places.reviews,places.priceLevel",
    }

# 1.2 구글 검색기준을 이용해 장소를 검색하여 리스트를 반환
def search_place(text_query, x, y, radius, priceLevel=None):
    body = {
        "textQuery": text_query,
        "languageCode": "ko",
        "regionCode": "KR",
        "locationBias": {
            "circle": {
                "center": {"latitude": y, "longitude": x},
                "radius": radius,  # 반경거리
            }
        },
        "priceLevels": priceLevel,  # 가격대 "PRICE_LEVEL_INEXPENSIVE", "PRICE_LEVEL_MODERATE"
    }
    r = requests.post(f"{BASE}:searchText", headers=_headers(), json=body, timeout=5)
    r.raise_for_status()  # 200대가 아니면 에러 발생

    data = r.json()
    places = data.get("places", [])

    google_place = []
    for p in places: #장소 리스트 상한 필요시 [:5]

        photos = p.get("photos", [])
        place_photos = {
            build_photo_url(p["name"], max_width_px=800)
            for p in photos
            if p.get("name")
        }

        reviews = p.get("reviews", [])
        reviews_text = [
            r.get("text", {}).get("text")  
            for r in reviews #리뷰 상한 필요시 [:5]
            if r.get("text", {}).get("text")
        ]

        google_place.append({
            "place_id" : p.get("id"),
            "place_name" : p.get("displayName", {}).get("text"),
            "address" : p.get("formattedAddress"),
            "location" : p.get("location"),
            "types" : p.get("types"),
            "phone_number" : p.get("nationalPhoneNumber"),
            "rating" : p.get("rating"),
            "open_now" : p.get("regularOpeningHours", {}).get("openNow"),
            "running_time" : p.get("regularOpeningHours", {}).get("weekdayDescriptions"),
            "price_range_start" : p.get("priceRange", {}).get("startPrice", {}).get("units"),
            "price_range_end" : p.get("priceRange", {}).get("endPrice", {}).get("units"),
            "place_photos" : place_photos,
            "reviews_text" : reviews_text
        })
    
    return google_place


# 사진 URL 생성
def build_photo_url(photo_name: str, max_width_px: int = 800) -> str:
    return (
        f"https://places.googleapis.com/v1/{photo_name}/media"
        f"?key={settings.GOOGLE_API_KEY}&maxWidthPx={max_width_px}"
    )
