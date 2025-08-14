from ..services import google, kakao
import requests

# 카카오 recommend 후 구글 search_place
def many_review_sort(place_list):
  
  sorted_data = {}

  for category, places in place_list.items():
    print(f"category: {category}, type(places): {type(places)}, len: {len(places)}")
    review_sort = []
    for p in places:  # 각 장소 딕셔너리 순회
      print("place_name:", p.get("place_name"))
      try:
          res = google.search_place(
              text_query = p["place_name"],
              x = float(p["x"]),
              y = float(p["y"]),
              radius = 500
          )
          if isinstance(res, list) and len(res) > 0:
            count = res[0].get("review_count", 0)
      except requests.RequestException:
          count = 0
      review_sort.append({**p, "review_count": count}) # 구글 리뷰수를 리스트에 추가

      review_sort.sort(key=lambda v: v.get("review_count", 0), reverse=True) # 오름차순 정렬 후 반환
      sorted_data[category] = review_sort

  return sorted_data