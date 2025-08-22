from django.conf import settings
import requests
import logging

from core import times
from core.distance import calculate_distance
from places.models import PopularKeyward
from wiki.models import WikiPlace

logger = logging.getLogger(__name__)

BASE = "https://places.googleapis.com/v1/places"

def _headers():
    return {
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Goog-FieldMask": "places.displayName,places.id,places.userRatingCount,places.nationalPhoneNumber,places.location,places.regularOpeningHours,places.rating,places.photos,places.priceRange,places.formattedAddress,places.types,places.reviews,places.priceLevel",
    }

# 사진 URL 생성
def build_photo_url(photo_name: str, max_width_px: int = 800) -> str:
    return (
        f"https://places.googleapis.com/v1/{photo_name}/media"
        f"?key={settings.GOOGLE_API_KEY}&maxWidthPx={max_width_px}"
    )

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
    r = requests.post(f"{BASE}:searchText", headers=_headers(), json=body, timeout=15)
    r.raise_for_status()

    data = r.json()
    places = data.get("places", [])

    google_place = []
    
    for p in places[:10]:
        
        p_id = ""
        click_num = 0 #[인기순정렬] 검색한 장소의 id가 DB에 있을 경우 인기 카운트 횟수를 세서 반환
        try:
            p_id = PopularKeyward.objects.get(place_id = p.get("id"))
            click_num = p_id.click_num if p_id else 0
        except PopularKeyward.DoesNotExist:
            pass

        review_count = 0 #[후기순정렬] 검색한 장소의 id, 리뷰 개수 반환
        try:
            r_id = WikiPlace.objects.get(google_place_id = p.get("id"))
            review_count = r_id.total_review_count if p_id else 0
        except WikiPlace.DoesNotExist:
            pass
        
        running_time = p.get("regularOpeningHours", {})
        if not running_time:
            time = "영업시간 정보 없음"
        else:
            time = times.format_running(running_time)

        photos = p.get("photos", [])[:1]
        place_photos = {
            build_photo_url(p["name"], max_width_px=800)
            for p in photos
            if p.get("name")
        }

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
            "review_count": review_count, #[후기순정렬]
            "running_time" : time,
            "distance_text" : distance_text,
            "place_photos":place_photos
        })
        # 후기순정렬은 후기 많은 순으로!
    
    return google_place

# 프론트로부터 place_id를 받고 세부 데이터 응답
def search_detail(place_id):
    params = {
        "languageCode": "ko",
        "regionCode": "KR",
        "fields": "id,displayName,formattedAddress,location,regularOpeningHours,photos",
    }
    r = requests.get(f"{BASE}/{place_id}", params=params, headers=_headers(), timeout=15)
    r.raise_for_status()
    p = r.json()

    photos = p.get("photos", [])[:5] #장소상한
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


def get_google_reviews(place_id, limit=10):
    """구글 Places API에서 특정 장소의 리뷰를 가져오는 함수
    
    Args:
        place_id (str): 구글 place ID
        limit (int): 가져올 리뷰 수 (기본 10개)
    
    Returns:
        dict: {"reviews": [리뷰 텍스트 리스트], "ratings": [별점 리스트], "average_rating": 평균별점}
    """
    try:
        # 구글 Places API에서 리뷰 포함하여 장소 정보 조회
        params = {
            "languageCode": "ko",
            "regionCode": "KR", 
            "fields": "id,displayName,reviews",
        }
        
        r = requests.get(f"{BASE}/{place_id}", params=params, headers=_headers(), timeout=20)
        r.raise_for_status()
        
        data = r.json()
        reviews_data = data.get("reviews", [])
        
        # 리뷰 텍스트와 별점 추출 (빈 리뷰는 제외)
        review_texts = []
        review_ratings = []
        
        for review in reviews_data[:limit]:
            text_data = review.get("text", {})
            review_text = text_data.get("text", "").strip()
            review_rating = review.get("rating", 0)  # 별점 (1-5)
            
            if review_text and len(review_text) >= 10:  # 최소 10자 이상인 리뷰만
                review_texts.append(review_text)
                review_ratings.append(review_rating)
        
        # 평균 별점 계산
        average_rating = round(sum(review_ratings) / len(review_ratings), 1) if review_ratings else 0
        
        logger.info(f"구글 리뷰 {len(review_texts)}개 수집 완료 (평균별점: {average_rating}) (장소ID: {place_id})")
        
        return {
            "reviews": review_texts,
            "ratings": review_ratings, 
            "average_rating": average_rating,
            "review_count": len(review_texts)
        }
        
    except requests.RequestException as e:
        logger.error(f"구글 리뷰 수집 실패 (장소ID: {place_id}): {e}")
        return {"reviews": [], "ratings": [], "average_rating": 0, "review_count": 0}
    except Exception as e:
        logger.error(f"구글 리뷰 처리 중 오류 (장소ID: {place_id}): {e}")
        return {"reviews": [], "ratings": [], "average_rating": 0, "review_count": 0}