import re, requests
from django.conf import settings
from ..models import PopularKeyward

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
    r = requests.post(f"{BASE}:searchText", headers=_headers(), json=body, timeout=5)
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
        
        google_place.append({
            # 장소카드에서는 place_name, address, location
            "place_id" : p.get("id"),
            "place_name" : p.get("displayName", {}).get("text"),
            "address" : p.get("formattedAddress"),
            "location" : p.get("location"),
            "review_count" : review_count,
            "click_num": click_num
            # "types" : p.get("types"),
            # "phone_number" : p.get("nationalPhoneNumber"),
            # "rating" : p.get("rating"),
            # "price_range_start" : p.get("priceRange", {}).get("startPrice", {}).get("units"),
            # "price_range_end" : p.get("priceRange", {}).get("endPrice", {}).get("units"),
        })

        
    
    return google_place

# 사진 URL 생성
def build_photo_url(photo_name: str, max_width_px: int = 800) -> str:
    return (
        f"https://places.googleapis.com/v1/{photo_name}/media"
        f"?key={settings.GOOGLE_API_KEY}&maxWidthPx={max_width_px}"
    )

# 영업시간 정보 데이터 가공
DAYS = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"]

def format_time(h, m):
    return f"{h:02d}:{m:02d}"

def format_running(running_time):
    result = []
    all_breaks = []  # 모든 요일의 브레이크 타임을 저장할 리스트
    
    for d in range(7):
        day_periods = [ 
            p for p in running_time.get("periods", []) 
            if p.get("open") and p["open"].get("day") == d 
        ]
        # day 값이 없으면 휴무일
        if not day_periods:
            result.append(f"{DAYS[d]} 휴무일")
            continue

        # 시간을 분 단위로 변환하여 전체 시간 계산
        intervals = []
        for p in day_periods:
            start_mins = p["open"]["hour"] * 60 + p["open"]["minute"]
            end_mins = p["close"]["hour"] * 60 + p["close"]["minute"]
            if end_mins == 0:  # 자정은 24*60으로 변환
                end_mins = 24 * 60
            intervals.append((start_mins, end_mins))
        
        # 정렬 후 전체 시간 범위 찾기
        intervals.sort()
        first_start = intervals[0][0]
        last_end = intervals[-1][1]
        
        # 전체 시간 포맷팅
        start_h, start_m = divmod(first_start, 60)
        end_h, end_m = divmod(last_end, 60)
        full_time = f"{format_time(start_h, start_m)}-{format_time(end_h, end_m)}"
        
        # 브레이크타임 계산
        day_breaks = []
        if len(intervals) > 1:
            for i in range(len(intervals) - 1):
                end_time = intervals[i][1]
                next_start = intervals[i + 1][0]
                gap = next_start - end_time
                
                if 0 < gap <= 180:  # 3시간 이하만 브레이크타임으로 간주
                    end_h, end_m = divmod(end_time, 60)
                    next_h, next_m = divmod(next_start, 60)
                    break_time = f"{format_time(end_h, end_m)}-{format_time(next_h, next_m)}"
                    day_breaks.append(break_time)
        
        all_breaks.append(day_breaks)
        result.append(f"{DAYS[d]} {full_time}")
    
    # 브레이크 타임이 모두 동일한 지 체크
    if all_breaks and all(breaks == all_breaks[0] for breaks in all_breaks if breaks):
        if all_breaks[0]:
            result.append(f"쉬는 시간 매일 {', '.join(all_breaks[0])}")
    else:
        # 브레이크 타임이 다르다면 각 요일별로 추가
        result.append("쉬는 시간")
        for d in range(7):
            if all_breaks[d]:
                result.append(f"{DAYS[d]} {', '.join(all_breaks[d])}")
    
    return result

# 1.2 장소를 저장하기 위해, 프론트로부터 place_id를 받고 세부 데이터 응답
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

# 4. 타로 페이지
def search_slot(x, y, radius):
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

    r = requests.post(f"{BASE}:searchNearby", headers=_headers(), json=body, timeout=5)
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
            google_place.append({
                "category" : category_name,
                "place_id" : p.get("id"),
                "place_name" : p.get("displayName", {}).get("text"),
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