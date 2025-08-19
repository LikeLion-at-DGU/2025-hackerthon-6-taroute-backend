# """
# Wiki 서비스 모듈
# - 카카오 API를 활용한 장소 검색
# - OpenAI API를 활용한 AI 요약 생성
# - 구글 API 연동 준비 (향후 확장용)
# """

# import requests
# import logging
# from typing import List, Dict, Optional, Tuple
# from django.conf import settings
# from django.utils import timezone
# from decimal import Decimal

# # 로깅 설정
# logger = logging.getLogger(__name__)

# # 카카오 API 엔드포인트
# KAKAO_LOCAL_BASE = "https://dapi.kakao.com/v2/local"
# KAKAO_SEARCH_KEYWORD = f"{KAKAO_LOCAL_BASE}/search/keyword.json"
# KAKAO_SEARCH_CATEGORY = f"{KAKAO_LOCAL_BASE}/search/category.json"


# def _kakao_headers():
#     """카카오 API 요청 헤더 생성
#     - 환경변수에서 API 키를 가져와 Authorization 헤더 구성
#     """
#     if not settings.KAKAO_REST_API_KEY:
#         raise ValueError("KAKAO_REST_API_KEY가 설정되지 않았습니다.")
#     return {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}


# def search_places_by_keyword(
#     query: str, 
#     x: Optional[float] = None, 
#     y: Optional[float] = None,
#     radius: int = 20000,
#     page: int = 1,
#     size: int = 15
# ) -> Dict:
#     """카카오 API를 사용한 키워드 기반 장소 검색
    
#     Args:
#         query: 검색할 키워드 (장소명, 지역명 등)
#         x: 중심 좌표 경도 (선택사항)
#         y: 중심 좌표 위도 (선택사항)
#         radius: 검색 반경(미터) - 기본 20km
#         page: 페이지 번호 (1~45)
#         size: 한 페이지 결과 수 (1~15)
    
#     Returns:
#         카카오 API 응답 JSON
#     """
#     params = {
#         "query": query,  # 검색 키워드
#         "page": page,    # 결과 페이지 번호
#         "size": size,    # 한 페이지 결과 수
#     }
    
#     # 좌표가 주어진 경우 중심점 기반 검색
#     if x is not None and y is not None:
#         params.update({
#             "x": x,          # 중심점 경도
#             "y": y,          # 중심점 위도 
#             "radius": radius # 검색 반경
#         })
    
#     try:
#         # 카카오 로컬 검색 API 호출
#         response = requests.get(
#             KAKAO_SEARCH_KEYWORD,
#             headers=_kakao_headers(),
#             params=params,
#             timeout=10  # 10초 타임아웃
#         )
#         response.raise_for_status()  # HTTP 에러 체크
        
#         result = response.json()
#         logger.info(f"카카오 키워드 검색 성공: {query}, 결과 {len(result.get('documents', []))}개")
#         return result
        
#     except requests.RequestException as e:
#         logger.error(f"카카오 API 호출 실패: {e}")
#         raise
#     except Exception as e:
#         logger.error(f"카카오 키워드 검색 중 오류: {e}")
#         raise


# def search_places_by_category(
#     category_group_code: str,
#     x: float,
#     y: float,
#     radius: int = 20000,
#     page: int = 1,
#     size: int = 15
# ) -> Dict:
#     """카카오 API를 사용한 카테고리 기반 장소 검색
    
#     Args:
#         category_group_code: 카테고리 그룹 코드
#             - MT1: 대형마트
#             - CS2: 편의점  
#             - PS3: 어린이집, 유치원
#             - SC4: 학교
#             - AC5: 학원
#             - PK6: 주차장
#             - OL7: 주유소, 충전소
#             - SW8: 지하철역
#             - BK9: 은행
#             - CT1: 문화시설
#             - AG2: 중개업소
#             - PO3: 공공기관
#             - AT4: 관광명소
#             - AD5: 숙박
#             - FD6: 음식점
#             - CE7: 카페
#             - HP8: 병원
#             - PM9: 약국
#         x: 중심 좌표 경도
#         y: 중심 좌표 위도
#         radius: 검색 반경(미터)
#         page: 페이지 번호
#         size: 한 페이지 결과 수
    
#     Returns:
#         카카오 API 응답 JSON
#     """
#     params = {
#         "category_group_code": category_group_code,
#         "x": x,
#         "y": y,
#         "radius": radius,
#         "page": page,
#         "size": size,
#     }
    
#     try:
#         # 카카오 카테고리 검색 API 호출
#         response = requests.get(
#             KAKAO_SEARCH_CATEGORY,
#             headers=_kakao_headers(),
#             params=params,
#             timeout=10
#         )
#         response.raise_for_status()
        
#         result = response.json()
#         logger.info(f"카카오 카테고리 검색 성공: {category_group_code}, 결과 {len(result.get('documents', []))}개")
#         return result
        
#     except requests.RequestException as e:
#         logger.error(f"카카오 카테고리 검색 API 호출 실패: {e}")
#         raise
#     except Exception as e:
#         logger.error(f"카카오 카테고리 검색 중 오류: {e}")
#         raise


# def parse_kakao_place_data(kakao_place: Dict) -> Dict:
#     """카카오 API 응답 데이터를 내부 형식으로 변환
    
#     Args:
#         kakao_place: 카카오 API에서 반환된 장소 정보 딕셔너리
    
#     Returns:
#         내부 Place 모델 형식으로 변환된 딕셔너리
#     """
#     try:
#         # 카카오 응답에서 필요한 정보 추출
#         return {
#             # 기본 장소 정보
#             'name': kakao_place.get('place_name', ''),
#             'address': kakao_place.get('address_name', ''),
#             'road_address': kakao_place.get('road_address_name', ''),
#             'longitude': float(kakao_place.get('x', 0)),
#             'latitude': float(kakao_place.get('y', 0)),
#             'phone': kakao_place.get('phone', ''),
            
#             # 위키 전용 정보
#             'shop_name': kakao_place.get('place_name', ''),
#             'kakao_place_id': kakao_place.get('id', ''),
#             'category_name': kakao_place.get('category_name', ''),
#             'category_group_code': kakao_place.get('category_group_code', ''),
#             'category_group_name': kakao_place.get('category_group_name', ''),
            
#             # 거리 정보 (검색 중심점 기준)
#             'distance': kakao_place.get('distance', ''),
            
#             # URL 정보
#             'place_url': kakao_place.get('place_url', ''),
#         }
#     except (ValueError, TypeError) as e:
#         logger.error(f"카카오 장소 데이터 파싱 실패: {e}, 데이터: {kakao_place}")
#         return {}


# def get_popular_search_keywords(limit: int = 10) -> List[Dict]:
#     """인기 검색 키워드 조회
    
#     Args:
#         limit: 반환할 키워드 개수
    
#     Returns:
#         인기 검색어 리스트 [{"keyword": "키워드", "count": 횟수}, ...]
#     """
#     from django.db.models import Count
#     from .models import WikiSearchHistory
    
#     # 최근 7일간의 검색 기록에서 인기 키워드 추출
#     from datetime import timedelta
#     recent_date = timezone.now() - timedelta(days=7)
    
#     popular_keywords = (
#         WikiSearchHistory.objects
#         .filter(created_at__gte=recent_date)
#         .values('search_query')
#         .annotate(search_count=Count('search_query'))
#         .order_by('-search_count')[:limit]
#     )
    
#     return [
#         {
#             "keyword": item['search_query'],
#             "count": item['search_count']
#         }
#         for item in popular_keywords
#     ]


# # 구글 API 연동 준비 (향후 확장용)
# def search_places_by_google(query: str, location: str = None) -> Dict:
#     """구글 Places API를 사용한 장소 검색 (향후 구현)
    
#     Args:
#         query: 검색 키워드
#         location: 위치 정보
    
#     Returns:
#         구글 API 응답 (현재는 NotImplemented)
#     """
#     # TODO: 구글 Places API 연동 구현
#     raise NotImplementedError("구글 API 연동은 향후 구현 예정입니다.")
