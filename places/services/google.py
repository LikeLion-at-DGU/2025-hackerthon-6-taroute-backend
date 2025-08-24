import re, requests
from django.conf import settings
from ..models import PopularKeyward
from core.distance import calculate_distance
from core.times import format_running
from datetime import datetime, time as dt_time

BASE = "https://places.googleapis.com/v1/places"

culture_types = [
    # --- 문화 관련 (5개) ---
    "art_gallery",               # 미술관
    "museum",                    # 박물관
    "performing_arts_theater",   # 공연장
    "cultural_landmark",         # 문화적 랜드마크
    "historical_landmark",       # 역사적 랜드마크
]
leisure_types = [
    # --- 관광명소 및 여가 (13개) ---
    "amusement_park",            # 놀이공원
    "aquarium",                  # 수족관
    "zoo",                       # 동물원
    "movie_theater",             # 영화관
    "park",                      # 공원
    "tourist_attraction",        # 관광 명소
    "bowling_alley",             # 볼링장
    "botanical_garden",          # 식물원
    "concert_hall",              # 콘서트홀
    "cultural_center",           # 문화센터
    "event_venue",               # 이벤트 장소
    "garden",                    # 정원
    "plaza",                     # 광장 (대형 광장, 공공 공간)
]
cafe_types = [ #카페(6개)
    "cafe",                      # 카페
    "bar",                       # 바
    "bakery",                    # 빵집
    "coffee_shop",               # 커피숍
    "dessert_shop",              # 디저트숍
    "ice_cream_shop",            # 아이스크림숍
]
food_types = [
    # --- 음식점(17개) ---
    # 일반 및 종류별
    "restaurant",                # 레스토랑 (일반)
    "fast_food_restaurant",      # 패스트푸드 레스토랑
    "pizza_restaurant",          # 피자 레스토랑
    "sandwich_shop",             # 샌드위치숍
    "hamburger_restaurant",      # 햄버거 레스토랑
    "pub",                       # 펍
    "wine_bar",                  # 와인 바

    # 국가/요리별 (대표적인 몇몇)
    "korean_restaurant",         # 한식 레스토랑
    "chinese_restaurant",        # 중식 레스토랑
    "japanese_restaurant",       # 일식 레스토랑
    "italian_restaurant",        # 이탈리안 레스토랑
    "american_restaurant",       # 미국식 레스토랑
    "thai_restaurant",           # 태국식 레스토랑
    "indian_restaurant",         # 인도식 레스토랑
    "mexican_restaurant",        # 멕시칸 레스토랑
    "french_restaurant",         # 프랑스식 레스토랑
    "vietnamese_restaurant",     # 베트남식 레스토랑
]

def _headers():
    return {
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": "http://localhost:8000",
        "X-Goog-FieldMask": "places.displayName,places.id,places.userRatingCount,places.nationalPhoneNumber,places.location,places.regularOpeningHours,places.rating,places.photos,places.priceRange,places.formattedAddress,places.types,places.reviews,places.priceLevel",
    }

# 1.2 구글 검색기준을 이용해 장소를 검색하여 리스트를 반환
def search_place(text_query, x, y, radius, rankPreference=None, priceLevel=None):
    
    body = {
        "textQuery": text_query,
        "languageCode": "ko",
        "rankPreference": rankPreference, #RELEVANCE(검색관련성) / DISTANCE(거리순)
        "regionCode": "KR",
        "locationBias": {
            "circle": {
                "center": {"latitude": y, "longitude": x},
                "radius": radius,  # 반경거리
            }
        },
        "priceLevels": priceLevel,  # 가격대 "PRICE_LEVEL_INEXPENSIVE", "PRICE_LEVEL_MODERATE"
    }
    r = requests.post(f"{BASE}:searchText", headers=_headers(), json=body, timeout=15)
    r.raise_for_status()  # 200대가 아니면 에러 발생

    data = r.json()
    places = data.get("places", [])

    google_place = []
    
    for p in places[:10]:
        review_count = p.get("userRatingCount", 0)

        #검색한 장소의 id가 DB에 있을 경우 인기 카운트 횟수를 세서 반환
        p_id = ""
        click_num = 0
        try:
            p_id = PopularKeyward.objects.get(place_id = p.get("id"))
            click_num = p_id.click_num if p_id else 0
        except PopularKeyward.DoesNotExist:
            pass

        # 거리 계산 추가 (m 단위로 통일)
        place_lat = p.get("location", {}).get("latitude", 0)
        place_lng = p.get("location", {}).get("longitude", 0)
        
        if not place_lat or not place_lng or not x or not y:
            distance_m = 999999  # 좌표가 없으면 매우 먼 거리로 설정
        else:
            distance_km = calculate_distance(y, x, place_lat, place_lng)
            distance_m = int(distance_km * 1000)  # km를 m로 변환
        
        # 거리 표시 형식
        if distance_m < 1000:
            distance_display = f"{distance_m}m"
        else:
            distance_display = f"{distance_m / 1000:.1f}km"

        photos = p.get("photos", [])[:1]
        place_photos = {
            build_photo_url(p["name"], max_width_px=800)
            for p in photos
            if p.get("name")
        }
        

        google_place.append({
            # 장소카드에서는 place_name, address, location
            "place_id" : p.get("id"),
            "place_name" : p.get("displayName", {}).get("text"),
            "address" : p.get("formattedAddress"),
            "location" : p.get("location"),
            "distance": distance_display,
            "distance_m": distance_m,  # 정렬을 위한 m 단위 거리
            "review_count" : review_count,
            "click_num": click_num,
            "place_photos" : place_photos
            # "types" : p.get("types"),
            # "phone_number" : p.get("nationalPhoneNumber"),
            # "rating" : p.get("rating"),
            # "price_range_start" : p.get("priceRange", {}).get("startPrice", {}).get("units"),
            # "price_range_end" : p.get("priceRange", {}).get("endPrice", {}).get("units"),
        })

    # rankPreference가 DISTANCE면 거리순 정렬 적용
    if rankPreference == "DISTANCE":
        google_place.sort(key=lambda x: x.get("distance_m", 999999))
    
    return google_place

# 사진 URL 생성
def build_photo_url(photo_name: str, max_width_px: int = 800) -> str:
    return (
        f"https://places.googleapis.com/v1/{photo_name}/media"
        f"?key={settings.GOOGLE_API_KEY}&maxWidthPx={max_width_px}"
    )

# 1.2 장소를 저장하기 위해, 프론트로부터 place_id를 받고 세부 데이터 응답
def search_detail(place_id):
    params = {
        "languageCode": "ko",
        "regionCode": "KR",
        "fields": "id,displayName,formattedAddress,location,regularOpeningHours,photos",
    }
    r = requests.get(f"{BASE}/{place_id}", params=params, headers=_headers(), timeout=15)
    r.raise_for_status()
    p = r.json()

    photos = p.get("photos", [])[:1]
    place_photos = {
        build_photo_url(p["name"], max_width_px=800)
        for p in photos
        if p.get("name")
    }

    running_time = p.get("regularOpeningHours", {})
    if not running_time:
        time = "영업시간 정보 없음"
    else:
        time = format_running(running_time)

    search_details = {
        "place_name" : p.get("displayName", {}).get("text"),
        "address" : p.get("formattedAddress"),
        "location" : p.get("location"),
        "running_time" : time,
        # "running_time_raw" : running_time, 필요 시 프론트 제공
        "place_photos" : place_photos
    }

    return search_details

def get_google_reviews(place_id, limit=5):
    """구글 Places API에서 특정 장소의 리뷰를 가져오는 함수
    
    Args:
        place_id (str): 구글 place ID
        limit (int): 가져올 리뷰 수 (기본 5개)
    
    Returns:
        dict: {"reviews": [리뷰 텍스트 리스트], "google_rating": 구글평점, "google_rating_count": 총리뷰수, "review_count": 크롤링한리뷰수}
    """
    try:
        # 구글 Places API에서 리뷰 포함하여 장소 정보 조회
        params = {
            "languageCode": "ko",
            "regionCode": "KR", 
            "fields": "id,displayName,reviews,rating,userRatingCount",
        }
        
        r = requests.get(f"{BASE}/{place_id}", params=params, headers=_headers(), timeout=20)
        r.raise_for_status()
        
        data = r.json()
        reviews_data = data.get("reviews", [])
        
        # 구글 장소 평점 정보 (개별 리뷰 별점이 아닌 장소 전체 평점)
        google_rating = data.get("rating", 0)  # 구글 장소 평점
        google_rating_count = data.get("userRatingCount", 0)  # 총 리뷰 수
        
        # 리뷰 텍스트 추출 (빈 리뷰는 제외)
        review_texts = []
        
        for review in reviews_data[:limit]:
            text_data = review.get("text", {})
            review_text = text_data.get("text", "").strip()
            
            if review_text and len(review_text) >= 10:  # 최소 10자 이상인 리뷰만
                review_texts.append(review_text)
        
        print(f"구글 리뷰 {len(review_texts)}개 수집 완료 (구글평점: {google_rating}/5.0, 총 리뷰수: {google_rating_count}) (장소ID: {place_id})")
        
        return {
            "reviews": review_texts,
            "google_rating": google_rating,  # 구글 장소 평점
            "google_rating_count": google_rating_count,  # 총 리뷰 수
            "review_count": len(review_texts)  # 크롤링한 리뷰 수
        }
        
    except requests.RequestException as e:
        print(f"구글 리뷰 수집 실패 (장소ID: {place_id}): {e}")
        return {"reviews": [], "google_rating": 0, "google_rating_count": 0, "review_count": 0}
    except Exception as e:
        print(f"구글 리뷰 처리 중 오류 (장소ID: {place_id}): {e}")
        return {"reviews": [], "google_rating": 0, "google_rating_count": 0, "review_count": 0}

# 4. 타로 페이지
def search_slot(x, y, radius):

    if x is None or y is None:
        raise ValueError(f"위치 좌표가 None입니다. x={x}, y={y}")

    body = {
        "languageCode": "ko",
        "regionCode": "KR",
        "locationRestriction": {
            "circle": {
                "center": {"latitude": float(y), "longitude": float(x)},
                "radius": radius,
            }
        },
        "includedTypes": culture_types + leisure_types + food_types + cafe_types,
    }

    r = requests.post(f"{BASE}:searchNearby", headers=_headers(), json=body, timeout=15)
    r.raise_for_status()  # 200대가 아니면 에러 발생
    data = r.json()
    places = data.get("places") or []

    culture_places = []
    leisure_places = []
    cafe_places = []
    food_places = []

    for p in places:
        place_types = p.get("types", [])

        if any(t in culture_types for t in place_types):
            culture_places.append(p)
        elif any(t in leisure_types for t in place_types):
            leisure_places.append(p)
        elif any(t in cafe_types for t in place_types):
            cafe_places.append(p)
        else:
            food_places.append(p)
    print(f"문화 장소: {len(culture_places)}개")
    print(f"관광/여가 장소: {len(leisure_places)}개")
    print(f"카페 장소: {len(cafe_places)}개")
    print(f"음식점 장소: {len(food_places)}개")
    
    google_place = []
    # 랜덤하게 가져온 20개의 장소를 각 카테고리별로 분류
    for category_name, places_list in [
        ("문화", culture_places), 
        ("관광/여가", leisure_places), 
        ("카페", cafe_places), 
        ("음식점", food_places)
    ]:
        for p in places_list:
            reviews = p.get("reviews") or []
            reviews_text = [
                (re.get("text") or {}).get("text")  
                for re in reviews
                if re.get("text") or {}.get("text")
            ]

            photos = p.get("photos", [])
            place_photos = {
                build_photo_url(p["name"], max_width_px=800)
                for p in photos[:1]
                if p.get("name")
            }

            google_place.append({
                "category" : category_name,
                "place_id" : p.get("id"),
                "place_name" : p.get("displayName", {}).get("text"),
                "place_photos":place_photos,
                "address" : p.get("formattedAddress"),
                "location" : p.get("location"),
                "reviews_text":reviews_text,
            })
    return google_place

def keyword_match(places, keywords):
    
    matched_places = []  # 매칭된 장소를 담을 리스트
    for p in places:
        place_matches = [] # 현재 장소의 매칭 결과물
        reviews = p.get("reviews_text", [])
        if not (reviews and isinstance(reviews, list)): # 리스트 형태인지 확인
            continue
        # 리뷰별로 키워드 검색
        for r_idx, text in enumerate(reviews):
            if not isinstance(text, str) or not text:
                continue
            text_lower = text.lower()
            for src, w in keywords:
                w_lower = w.lower()

                # 리뷰 내 모든 키워드 요소 찾기 (겹침 허용)
                for m in re.finditer(re.escape(w_lower), text_lower):
                    start, end = m.span()
                    # 리뷰 문맥 추출, 프린트용! (앞뒤 10~15자 정도)
                    text_start = max(0, start - 10)
                    text_end   = min(len(text), end + 10)
                    context = text[text_start:text_end]

                    # 결과 레코드 저장
                    place_matches.append({
                        "keyword": w,            # 매칭된 단어
                        "source_text": src,      # 원문
                        "review_index": r_idx,   # 몇 번째 리뷰인지
                        "context": context,      # 리뷰 내용
                    })

        if place_matches:
            place_copy = p.copy()
            place_copy["matches"] = place_matches
            matched_places.append(place_copy)

    return matched_places

# 카테고리별 구글 장소 타입 매핑
CATEGORY_TYPE_MAPPING = {
    "restaurant": [
        "restaurant", "fast_food_restaurant", "pizza_restaurant", 
        "sandwich_shop", "hamburger_restaurant", "korean_restaurant",
        "chinese_restaurant", "japanese_restaurant", "italian_restaurant",
        "american_restaurant", "thai_restaurant", "indian_restaurant",
        "mexican_restaurant", "french_restaurant", "vietnamese_restaurant"
    ],
    "cafe": [
        "cafe", "coffee_shop", "bakery", "dessert_shop", "ice_cream_shop"
    ],
    "culture": [
        "art_gallery", "museum", "performing_arts_theater", 
        "cultural_landmark", "historical_landmark", "library"
    ],
    "tourist_attraction": [
        "amusement_park", "aquarium", "zoo", "park", "tourist_attraction",
        "botanical_garden", "cultural_center", "event_venue", "garden", "plaza"
    ]
}

def search_category_places(
    text_query=None, 
    category="all", 
    x=None, 
    y=None, 
    radius=5000,
    distance_filter="all",
    visit_time_filter="all", 
    visit_days_filter=None,
    sort_by="relevance",
    limit=20
):
    """카테고리 페이지용 장소 검색 (필터링 포함)
    
    Args:
        text_query: 검색어 (선택사항)
        category: 카테고리 ("restaurant", "cafe", "culture", "tourist_attraction", "all")
        x, y: 검색 중심 좌표
        radius: 기본 검색 반경
        distance_filter: 거리 필터 ("0.5km", "1km", "3km", "5km", "all")
        visit_time_filter: 방문시간 필터 ("morning", "afternoon", "evening", "night", "dawn", "all")
        visit_days_filter: 방문요일 필터 (리스트)
        sort_by: 정렬 기준 ("distance", "relevance", "rating", "popularity")
        limit: 결과 수 제한
    
    Returns:
        필터링된 장소 리스트
    """
    
    # 거리 필터에 따른 반경 조정 (0.5km 추가, 5km 이상 제거)
    if distance_filter == "0.5km":
    # 거리 필터에 따른 반경 조정 (0.5km 추가, 5km 이상 제거)
    if distance_filter == "0.5km":
        search_radius = 500
    elif distance_filter == "1km":
        search_radius = 1000
    elif distance_filter == "3km":
        search_radius = 3000
    elif distance_filter == "5km":
        search_radius = 5000
    else:
        search_radius = radius

    
    
    # 구글 Places API 요청 구성
    body = {
        "languageCode": "ko",
        "regionCode": "KR"
    }

    # 텍스트 쿼리가 있으면 searchText 사용, 없으면 searchNearby 사용
    if text_query:
        body["textQuery"] = text_query
        body["rankPreference"] = "DISTANCE" if sort_by == "distance" else "RELEVANCE"
        api_url = f"{BASE}:searchText"
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": float(y), "longitude": float(x)},
                "radius": float(search_radius),
            }
        }
    else:
        body["locationRestriction"] = {
            "circle": {
                "center": {"latitude": float(y), "longitude": float(x)},
                "radius": float(search_radius),
            }
        }
        # 카테고리별 장소 타입 설정
        if category != "all" and category in CATEGORY_TYPE_MAPPING:
            body["includedTypes"] = CATEGORY_TYPE_MAPPING[category]
        else:
            # 전체 카테고리인 경우 모든 타입 포함
            all_types = []
            for types in CATEGORY_TYPE_MAPPING.values():
                all_types.extend(types)
            body["includedTypes"] = all_types
        
        api_url = f"{BASE}:searchNearby"
    
    try:
        r = requests.post(api_url, headers=_headers(), json=body, timeout=20)
        status = r.status_code
        r.raise_for_status()
        data = r.json()

        places = data.get("places", [])
        
        # 장소 데이터 변환 및 필터링
        filtered_places = []
        
        for p in places:
            # 기본 정보 추출
            place_data = _extract_place_data(p, x, y)
            
            # 거리 필터 적용 (m 단위로 통일)
            if distance_filter != "all":
                # 거리 필터에 따른 추가 필터링 (m 단위)
                if distance_filter == "0.5km" and place_data["distance_m"] > 500:
                    continue
                elif distance_filter == "1km" and place_data["distance_m"] > 1000:
                    continue
                elif distance_filter == "3km" and place_data["distance_m"] > 3000:
                    continue
                elif distance_filter == "5km" and place_data["distance_m"] > 5000:
                    continue
            
            # 영업시간 관련 필터 적용
            if visit_time_filter != "all" or visit_days_filter:
                opening_hours = p.get("regularOpeningHours", {})
                
                # 방문시간 필터
                if visit_time_filter != "all":
                    if not _check_time_filter(opening_hours, visit_time_filter):
                        continue
                
                # 방문요일 필터
                if visit_days_filter:
                    if not _check_days_filter(opening_hours, visit_days_filter):
                        continue
            
            filtered_places.append(place_data)
        
        # 정렬 적용
        sorted_places = _sort_places(filtered_places, sort_by)
        
        # 결과 수 제한
        return sorted_places[:limit]
        
    except requests.HTTPError as e:
        raise RuntimeError(f"Places API error {status}") from e

    except Exception as e:
        print(f"카테고리 장소 검색 실패: {e}")
        return []

def _extract_place_data(place, center_x, center_y):
    """구글 Places API 응답에서 장소 데이터 추출"""
    
    # 인기도 정보 (DB에서 조회)
    place_id = place.get("id")
    click_num = 0
    try:
        popular_place = PopularKeyward.objects.get(place_id=place_id)
        click_num = popular_place.click_num
    except PopularKeyward.DoesNotExist:
        pass
    
    # 거리 계산 (모든 거리를 m 단위로 통일)
    place_lat = place.get("location", {}).get("latitude", 0)
    place_lng = place.get("location", {}).get("longitude", 0)
    
    # 좌표 유효성 검증
    if not place_lat or not place_lng or not center_x or not center_y:
        distance_m = 999999  # 좌표가 없으면 매우 먼 거리로 설정 (999km)
    else:
        distance_km = calculate_distance(center_y, center_x, place_lat, place_lng)
        distance_m = int(distance_km * 1000)  # km를 m로 변환하고 정수로 처리
    
    # 카테고리 분류
    place_types = place.get("types", [])
    category = _classify_category(place_types)
    
    # 사진 URL 생성
    photos = place.get("photos", [])
    place_photos = [
        build_photo_url(photo["name"], max_width_px=400)
        for photo in photos[:5]
        if photo.get("name")
    ]
    
    # 영업시간 정보 처리
    is_open_now = place.get("businessStatus") == "OPERATIONAL"
    running_time = place.get("regularOpeningHours", {})
    if not running_time:
        time = "영업시간 정보 없음"
    else:
        time = format_running(running_time)
    
    # 거리 표시 형식 (m 단위 기준으로 표시)
    if distance_m < 1000:
        distance_display = f"{distance_m}m"
    else:
        distance_display = f"{distance_m / 1000:.1f}km"
    
    return {
        "place_id": place_id,
        "place_name": place.get("displayName", {}).get("text", ""),
        "distance": distance_display,
        "distance_m": distance_m,  # 정렬/필터링을 위한 m 단위 거리
        # "category": category,
        "address": place.get("formattedAddress", ""),
        "location": place.get("location", {}),
        "rating": place.get("rating", 0.0),  # 정렬을 위해 추가
        "review_count": place.get("userRatingCount", 0),  # 정렬을 위해 추가
        "price_level": _get_price_level(place.get("priceLevel")),  # 가격 정렬을 위해 추가
        "running_time": time,
        "is_open_now": is_open_now,
        "place_photos": place_photos,
        "click_num": click_num  # 인기순 정렬을 위해 추가
    }

def _classify_category(place_types):
    """장소 타입을 기반으로 카테고리 분류"""
    for category, types in CATEGORY_TYPE_MAPPING.items():
        if any(ptype in types for ptype in place_types):
            if category == "restaurant":
                return "식당"
            elif category == "cafe":
                return "카페"
            elif category == "culture":
                return "문화시설"
            elif category == "tourist_attraction":
                return "관광명소"
    return "기타"

def _get_price_level(price_level):
    """가격 수준을 한국어로 변환"""
    if not price_level:
        return "정보 없음"
    
    price_mapping = {
        "PRICE_LEVEL_FREE": "무료",
        "PRICE_LEVEL_INEXPENSIVE": "저렴함",
        "PRICE_LEVEL_MODERATE": "보통",
        "PRICE_LEVEL_EXPENSIVE": "비쌈",
        "PRICE_LEVEL_VERY_EXPENSIVE": "매우 비쌈"
    }
    return price_mapping.get(price_level, "정보 없음")

def _check_time_filter(opening_hours, time_filter):
    """방문시간 필터 체크"""
    if not opening_hours or not opening_hours.get("periods"):
        return False
    
    # 시간대별 범위 정의
    time_ranges = {
        "morning": (6, 12),    # 06:00-12:00
        "afternoon": (12, 17), # 12:00-17:00
        "evening": (17, 21),   # 17:00-21:00
        "night": (21, 24),     # 21:00-24:00
        "dawn": (0, 6)         # 00:00-06:00
    }
    
    if time_filter not in time_ranges:
        return True
    
    start_hour, end_hour = time_ranges[time_filter]
    
    # 각 요일별 영업시간 체크
    for period in opening_hours.get("periods", []):
        open_time = period.get("open", {})
        close_time = period.get("close", {})
        
        if not open_time or not close_time:
            continue
        
        open_hour = open_time.get("hour", 0)
        close_hour = close_time.get("hour", 24)
        
        # 24시간 영업인 경우
        if close_hour == 0:
            close_hour = 24
        
        # 영업시간이 필터 시간과 겹치는지 확인
        if _time_overlap(open_hour, close_hour, start_hour, end_hour):
            return True
    
    return False

def _check_days_filter(opening_hours, days_filter):
    """방문요일 필터 체크"""
    if not opening_hours or not opening_hours.get("periods"):
        return False
    
    # 요일 매핑 (구글 API는 0=일요일부터 시작)
    day_mapping = {
        "sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3,
        "thursday": 4, "friday": 5, "saturday": 6
    }
    
    # 필터에서 요청한 요일들의 숫자 변환
    filter_day_numbers = [day_mapping.get(day) for day in days_filter if day in day_mapping]
    
    # 영업하는 요일들 추출
    operating_days = set()
    for period in opening_hours.get("periods", []):
        open_day = period.get("open", {}).get("day")
        if open_day is not None:
            operating_days.add(open_day)
    
    # 필터 요일 중 하나라도 영업하면 통과
    return any(day_num in operating_days for day_num in filter_day_numbers)

def _time_overlap(start1, end1, start2, end2):
    """두 시간 범위가 겹치는지 확인"""
    return max(start1, start2) < min(end1, end2)

def _sort_places(places, sort_by):
    """장소 리스트 정렬"""
    if sort_by == "distance":
        # 거리순 정렬 (distance_m 기준, None이나 누락값은 999999로 처리)
        sorted_places = sorted(places, key=lambda x: int(x.get("distance_m", 999999)))
        return sorted_places
    elif sort_by == "rating":
        return sorted(places, key=lambda x: x.get("rating", 0), reverse=True)
    elif sort_by == "popularity":
        return sorted(places, key=lambda x: x.get("click_num", 0), reverse=True)
    elif sort_by == "price_low":
        # 가격 낮은 순 정렬 시도
        sorted_by_price = _sort_by_price(places, reverse=False)
        if sorted_by_price:
            return sorted_by_price
        else:
            # 가격 정보가 없으면 정확도 순으로 대체
            return _sort_by_relevance(places)
    elif sort_by == "price_high":
        # 가격 높은 순 정렬 시도
        sorted_by_price = _sort_by_price(places, reverse=True)
        if sorted_by_price:
            return sorted_by_price
        else:
            # 가격 정보가 없으면 정확도 순으로 대체
            return _sort_by_relevance(places)
    else:  # relevance (기본값)
        return _sort_by_relevance(places)

def _sort_by_price(places, reverse=False):
    """가격 기준 정렬 (가격 정보가 있는 장소만)"""
    # 가격 정보가 있는 장소들만 필터링
    places_with_price = [p for p in places if p.get("price_level") and p.get("price_level") != "정보 없음"]
    
    if not places_with_price:
        return None  # 가격 정보가 있는 장소가 없음
    
    # 가격 수준을 숫자로 변환하여 정렬
    def price_to_number(place):
        price_level = place.get("price_level", "")
        return _price_level_to_number(price_level)
    
    return sorted(places_with_price, key=price_to_number, reverse=reverse)

def _price_level_to_number(price_level):
    """가격 수준을 숫자로 변환"""
    price_mapping = {
        "무료": 0,
        "저렴함": 1,
        "보통": 2,
        "비쌈": 3,
        "매우 비쌈": 4
    }
    return price_mapping.get(price_level, 2)  # 기본값은 보통

def _sort_by_relevance(places):
    """정확도 순 정렬 (거리도 고려)"""
    def relevance_score(place):
        rating = place.get("rating", 0)
        review_count = min(place.get("review_count", 0), 1000)  # 최대 1000으로 제한
        distance_m = place.get("distance_m", 999999)
        
        # 기본 점수 (평점 * 리뷰수 가중치)
        base_score = rating * (1 + review_count / 1000)
        
        # 거리 보너스 (1km 이내면 보너스, 멀수록 패널티)
        if distance_m <= 1000:  # 1km 이내
            distance_bonus = 1 + (1000 - distance_m) / 1000 * 0.3  # 최대 30% 보너스
        else:
            distance_bonus = max(0.7, 1 - (distance_m - 1000) / 10000 * 0.3)  # 거리 패널티
            
        return base_score * distance_bonus
    
    return sorted(places, key=relevance_score, reverse=True)