import requests
from django.conf import settings

from ..services import google
from ..models import SubwayLines
from django.db.models import Q #검색어 일부가 포함된 지하철역 검색  


LOCAL = "https://dapi.kakao.com/v2/local"
ROUTE = "https://apis-navi.kakaomobility.com/v1/directions"

def _headers():
    return {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}

# 1.1 현위치 표시
def locate_dong(query): 
    params = {"query":query}
    r = requests.get(f"{LOCAL}/search/address.json", headers=_headers(), params=params, timeout=5)
    r.raise_for_status() #200대가 아니면 에러 발생
    data = r.json()
    address_list = []

    #DB에서 지하철역정보 검색하여 위도경도 반환
    q = query.strip()
    if q.endswith("역"): #00역인 경우 '역' 제거
        q = q[:-1].strip()

    subway = SubwayLines.objects.filter(
        Q(station__icontains=q)
    )
    stations = subway[:10]  # 너무 많이 안 주도록 상한
    for s in stations:
        address_list.append({
            "address_name": f"{s.station} ({s.line})",
            "x": s.longitude,
            "y": s.latitude,
        })

    if data["documents"]: 
        #카카오API의 위도경도 목록
        for document in data["documents"]:
            address_list.append({
                "address_name" : document.get("address_name"),
                "x" : document.get("x"),
                "y" : document.get("y")
            })
    
    return address_list

# 1.2 장소 카테고리별 추천
CATEGORY_LABELS = {
    "CT1": "문화시설",
    "AT4": "관광명소",
    "FD6": "음식점",
    "CE7": "카페",
}
CATEGORY = list(CATEGORY_LABELS.keys())

def _search_category(category, x, y, radius, size=10):
    params = {
        "category_group_code": category,
        "x": x,
        "y": y,
        "radius": radius,
        "size":size,
    }
    r = requests.get(f"{LOCAL}/search/category.json", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    places = (r.json() or {}).get("documents", [])

    # 2) place_name, x, y 반환 => 구글 장소 세부데이터 요청 필요 (places/google_place)
    return [
        {"place_name": p.get("place_name"), "address": p.get("address_name"), "x": p.get("x"), "y": p.get("y")}
        for p in places[:size] #장소 리스트 상한 10개
    ]

def recommend_place(x, y, radius=2000, category_group_code=None, limit=7):
    if not category_group_code or category_group_code == "all":
        codes = CATEGORY
        limit = 2 #검색창 하단 카테고리 추천 수 제한
    else:
        codes = [category_group_code] #카테고리 페이지에서는 3개씩
        limit = 3

    # 카테고리별 결과 검색
    results = {}
    for code in codes:
        places = _search_category(code, x, y, radius, size=limit)

        for p in places:
            try:
                # 카카오 recommend 후 구글 search_place
                res = google.search_place(
                    text_query = p["place_name"],
                    x = float(p["x"]),
                    y = float(p["y"]),
                    radius = 2000
                )

                if res:  # 결과가 있는 경우만
                    place_info = res[0]
                    photos = list(place_info.get("place_photos", []))[:1]  # set을 리스트로 변환 후 첫 번째 항목만 가져오기, # 구글 사진 추가
                    p["place_photos"] = photos

                    print(f"data: {p}")

                    p["review_count"] = res[0].get("review_count", 0) # 구글 리뷰 개수 추가
                    p["place_id"] = res[0].get("place_id", "") # 구글 장소 ID 추가

            except (requests.RequestException, IndexError) as e:
                p["place_id"] = ""
                p["place_photos"] = []
                p["review_count"] = 0

        results[CATEGORY_LABELS[code]] = places
        

    # 단일 카테고리인 경우 해당 결과만 반환
    if len(codes) == 1:
        return results[CATEGORY_LABELS[codes[0]]]
    
    # 전체 카테고리인 경우: 음식점, 카페, 문화시설, 관광명소 순서로 섞어서 반환
    mixed_results = []
    
    # 원하는 순서: 음식점(FD6), 카페(CE7), 문화시설(CT1), 관광명소(AT4)
    category_order = ["FD6", "CE7", "CT1", "AT4"]
    
    # 각 카테고리에서 최대 2개씩 가져와서 순서대로 섞기
    for i in range(2):  # 0, 1 (각 카테고리에서 첫 번째, 두 번째)
        for code in category_order:
            category_name = CATEGORY_LABELS[code]
            category_places = results.get(category_name, [])
            
            if i < len(category_places):  # i번째 장소가 있는 경우
                place = category_places[i].copy()
                # place["category"] = category_name  # 카테고리 정보 추가
                mixed_results.append(place)
    
    return mixed_results

# 6.2 AI 루트 추천 관련 카테고리 검색
def look_category(q, x, y, radius, size=1):
    params = {
        "query": q,
        "x": x,
        "y": y,
        "radius": radius,
        "size":size,
    }
    r = requests.get(f"{LOCAL}/search/keyword.json", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    data = (r.json() or {}).get("documents", [])
    
    if data and len(data) > 0:
        data_type = data[0].get("category_group_code", "")
        return data_type
    else:
        # 데이터가 없는 경우 기본값(음식점) 반환
        return "FD6"

# def many_review_sort(place_list):
#     review_sort = []
#     for p in place_list:  # 각 장소 딕셔너리 순회
#       try:
#           res = google.search_place(
#               text_query=p.get("place_name", ""),
#               x = float(p["x"]),
#               y = float(p["y"]),
#               radius = 500
#           )
#           if isinstance(res, list) and len(res) > 0:
#             count = res[0].get("review_count", 0)
#       except requests.RequestException:
#           count = 0
#       review_sort.append({**p, "review_count": count}) # 구글 리뷰수를 리스트에 추가

#       review_sort.sort(key=lambda v: v.get("review_count", 0), reverse=True) # 오름차순 정렬 후 반환

#     return review_sort
