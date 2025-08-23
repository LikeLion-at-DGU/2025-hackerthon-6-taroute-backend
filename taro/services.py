"""
Taro 서비스 모듈
- OpenAI API를 활용한 타루 대화 시스템
- 카카오/구글 API를 활용한 장소 추천
- 아키네이터 스타일의 질문 시스템
"""

import requests
import logging
import random
from typing import List, Dict, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

# 로깅 설정
logger = logging.getLogger(__name__)


class TaruAIService:
    """타루 AI 대화 서비스
    
    - OpenAI API를 활용한 대화형 AI
    - 아키네이터 스타일의 질문 생성
    - 사용자 답변 분석 및 장소 추천
    """
    
    def __init__(self):
        """OpenAI 클라이언트 초기화"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai 패키지가 설치되어야 합니다: pip install openai")
        
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def generate_greeting_message(self, user_location: Optional[str] = None) -> str:
        """인사 메시지 생성
        
        Args:
            user_location: 사용자 위치 정보 (선택사항)
        
        Returns:
            타루의 인사 메시지
        """
        location_context = f" {user_location} 근처에서" if user_location else ""
        
        prompt = f"""
당신은 '타루'라는 이름의 친근한 타로 AI입니다. 
사용자와의 대화를 통해 그들에게 완벽한 장소를 추천해주는 역할을 합니다.

아키네이터처럼 질문을 통해 사용자의 취향을 파악하고{location_context} 맞춤형 장소를 추천합니다.

첫 인사말을 작성해주세요:
- 친근하고 신비로운 분위기
- 타로의 컨셉을 살린 표현
- 질문을 시작하겠다는 의지 표현
- 2-3문장 정도로 간결하게
"""
        
        try:
            response = self._client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"인사 메시지 생성 실패: {e}")
            return "안녕하세요! 저는 타루입니다. 🔮 몇 가지 질문을 통해 당신에게 완벽한 장소를 찾아드릴게요!"
    
    def generate_question(
        self, 
        conversation_history: List[Dict], 
        question_count: int,
        user_preferences: Dict
    ) -> str:
        """다음 질문 생성
        
        Args:
            conversation_history: 대화 히스토리
            question_count: 현재까지의 질문 수
            user_preferences: 분석된 사용자 취향
        
        Returns:
            다음 질문
        """
        # 질문 카테고리 정의
        question_categories = [
            "위치 선호도 (실내/실외, 도심/외곽)",
            "활동 유형 (휴식/액티브, 혼자/함께)",
            "분위기 (조용함/활기참, 모던/전통)",
            "시간대 선호 (아침/점심/저녁/밤)",
            "예산 수준 (합리적/중간/프리미엄)",
            "날씨 고려사항",
            "특별한 목적 (데이트/친구모임/혼자시간)",
            "음식/음료 선호도"
        ]
        
        # 대화 히스토리를 문자열로 변환
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in conversation_history[-10:]  # 최근 10개만
        ])
        
        prompt = f"""
당신은 '타루'라는 타로 AI입니다. 아키네이터처럼 질문을 통해 사용자에게 완벽한 장소를 추천합니다.

현재 상황:
- 질문 수: {question_count}/20
- 사용자 취향 분석: {user_preferences}

대화 히스토리:
{history_text}

다음 규칙에 따라 질문을 생성해주세요:
1. 아직 파악되지 않은 사용자 취향을 알아보는 질문
2. 선택지 2-4개를 제공하는 객관식 질문
3. 친근하고 신비로운 타루의 말투
4. 이전 답변을 고려한 연관성 있는 질문
5. 한 번에 하나의 주제만 다루기

질문 형식:
"[질문 내용]
A) [선택지1]
B) [선택지2]
C) [선택지3] (필요시)
D) [선택지4] (필요시)"

질문을 생성해주세요:
"""
        
        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.8
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"질문 생성 실패: {e}")
            # 기본 질문들
            default_questions = [
                "오늘은 어떤 분위기를 원하시나요?\nA) 조용하고 차분한 곳\nB) 활기차고 에너지 넘치는 곳",
                "어떤 활동을 선호하시나요?\nA) 편안한 휴식\nB) 새로운 경험",
                "누구와 함께 하시나요?\nA) 혼자\nB) 친구들과\nC) 연인과\nD) 가족과"
            ]
            return random.choice(default_questions)
    
    def analyze_user_response(
        self, 
        question: str, 
        answer: str, 
        current_preferences: Dict
    ) -> Dict:
        """사용자 답변 분석 및 취향 업데이트
        
        Args:
            question: 제시된 질문
            answer: 사용자 답변
            current_preferences: 현재 분석된 취향
        
        Returns:
            업데이트된 사용자 취향 딕셔너리
        """
        prompt = f"""
다음 정보를 바탕으로 사용자의 장소 취향을 분석하고 업데이트해주세요.

질문: {question}
답변: {answer}
현재 취향 분석: {current_preferences}

다음 카테고리별로 점수를 0-10으로 분석해주세요:
- location_type: 실내(0-3), 중간(4-6), 실외(7-10)
- activity_level: 휴식(0-3), 중간(4-6), 액티브(7-10)
- atmosphere: 조용함(0-3), 중간(4-6), 활기참(7-10)
- social_preference: 혼자(0-2), 소그룹(3-6), 대그룹(7-10)
- time_preference: 아침(morning), 점심(afternoon), 저녁(evening), 밤(night)
- budget_level: 저예산(0-3), 중간(4-6), 고예산(7-10)
- food_preference: 카페(cafe), 식당(restaurant), 술집(bar), 없음(none)

JSON 형태로만 응답해주세요:
{{
  "location_type": 점수,
  "activity_level": 점수,
  "atmosphere": 점수,
  "social_preference": 점수,
  "time_preference": "값",
  "budget_level": 점수,
  "food_preference": "값",
  "confidence": 신뢰도(0-1)
}}
"""
        
        try:
            response = self._client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3  # 분석에서는 일관성이 중요
            )
            
            import json
            analysis = json.loads(response.choices[0].message.content.strip())
            
            # 기존 취향과 새 분석 결과를 가중평균으로 병합
            updated_preferences = current_preferences.copy()
            confidence = analysis.get('confidence', 0.5)
            
            for key, value in analysis.items():
                if key == 'confidence':
                    continue
                    
                if isinstance(value, (int, float)):
                    # 숫자 값은 가중평균 적용
                    current_value = updated_preferences.get(key, 5.0)
                    updated_preferences[key] = (
                        current_value * (1 - confidence) + value * confidence
                    )
                else:
                    # 문자열 값은 신뢰도에 따라 업데이트
                    if confidence > 0.6:
                        updated_preferences[key] = value
            
            return updated_preferences
            
        except Exception as e:
            logger.error(f"답변 분석 실패: {e}")
            return current_preferences
    
    def generate_recommendation_summary(
        self, 
        user_preferences: Dict, 
        recommended_places: List[Dict]
    ) -> str:
        """추천 요약 메시지 생성
        
        Args:
            user_preferences: 분석된 사용자 취향
            recommended_places: 추천된 장소 리스트
        
        Returns:
            추천 요약 메시지
        """
        places_text = "\n".join([
            f"- {place['name']} ({place.get('category', '기타')})"
            for place in recommended_places[:5]  # 상위 5개만
        ])
        
        prompt = f"""
타루로서 사용자에게 장소 추천 결과를 설명해주세요.

분석된 사용자 취향: {user_preferences}
추천된 장소들:
{places_text}

다음 요소를 포함해서 2-3문장으로 작성해주세요:
- 사용자 취향에 대한 간단한 요약
- 왜 이러한 장소들을 추천했는지 설명
- 카드를 뽑아보라는 안내
- 타루의 친근하고 신비로운 말투
"""
        
        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"추천 요약 생성 실패: {e}")
            return f"당신의 취향을 바탕으로 {len(recommended_places)}개의 특별한 장소를 준비했어요! 🔮 이제 카드를 뽑아보세요!"


class PlaceRecommendationService:
    """장소 추천 서비스
    
    - 사용자 취향 기반 장소 추천
    - 카카오/구글 API 연동
    - 거리 및 카테고리 필터링
    """
    
    def __init__(self):
        """서비스 초기화"""
        self.kakao_base_url = "https://dapi.kakao.com/v2/local"
        
    def _get_kakao_headers(self) -> Dict[str, str]:
        """카카오 API 헤더 생성"""
        if not settings.KAKAO_REST_API_KEY:
            raise ValueError("KAKAO_REST_API_KEY가 설정되지 않았습니다.")
        return {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}
    
    def search_places_by_preferences(
        self,
        user_preferences: Dict,
        user_latitude: float,
        user_longitude: float,
        radius: int = 5000
    ) -> List[Dict]:
        """사용자 취향 기반 장소 검색
        
        Args:
            user_preferences: 분석된 사용자 취향
            user_latitude: 사용자 위도
            user_longitude: 사용자 경도
            radius: 검색 반경 (미터)
        
        Returns:
            추천 장소 리스트
        """
        # 취향 기반 검색 키워드 생성
        search_keywords = self._generate_search_keywords(user_preferences)
        all_places = []
        
        for keyword in search_keywords:
            try:
                places = self._search_kakao_places(
                    keyword=keyword,
                    x=user_longitude,
                    y=user_latitude,
                    radius=radius
                )
                all_places.extend(places)
            except Exception as e:
                logger.error(f"장소 검색 실패 - 키워드: {keyword}, 에러: {e}")
                continue
        
        # 중복 제거 및 점수 계산
        unique_places = self._deduplicate_and_score_places(
            all_places, user_preferences, user_latitude, user_longitude
        )
        
        # 상위 50개 선택 (카드 25장의 2배로 여유분 확보)
        return sorted(unique_places, key=lambda x: x['score'], reverse=True)[:50]
    
    def _generate_search_keywords(self, user_preferences: Dict) -> List[str]:
        """사용자 취향 기반 검색 키워드 생성"""
        keywords = []
        
        # 음식 선호도 기반
        food_pref = user_preferences.get('food_preference', 'cafe')
        if food_pref == 'cafe':
            keywords.extend(['카페', '커피', '디저트', '베이커리'])
        elif food_pref == 'restaurant':
            keywords.extend(['맛집', '식당', '레스토랑'])
        elif food_pref == 'bar':
            keywords.extend(['술집', '바', '펍', '와인바'])
        
        # 활동 수준 기반
        activity_level = user_preferences.get('activity_level', 5)
        if activity_level <= 3:  # 휴식 선호
            keywords.extend(['공원', '도서관', '카페', '스파'])
        elif activity_level >= 7:  # 액티브 선호
            keywords.extend(['체험', '액티비티', '놀이', '스포츠'])
        
        # 분위기 기반
        atmosphere = user_preferences.get('atmosphere', 5)
        if atmosphere <= 3:  # 조용한 곳 선호
            keywords.extend(['조용한', '한적한', '갤러리', '박물관'])
        elif atmosphere >= 7:  # 활기찬 곳 선호
            keywords.extend(['번화가', '쇼핑', '시장', '축제'])
        
        # 위치 타입 기반
        location_type = user_preferences.get('location_type', 5)
        if location_type <= 3:  # 실내 선호
            keywords.extend(['실내', '백화점', '복합문화공간'])
        elif location_type >= 7:  # 실외 선호
            keywords.extend(['공원', '해변', '산', '야외'])
        
        # 기본 키워드 (결과가 부족할 때)
        if not keywords:
            keywords = ['카페', '맛집', '관광지', '공원', '문화시설']
        
        return list(set(keywords))  # 중복 제거
    
    def _search_kakao_places(
        self, 
        keyword: str, 
        x: float, 
        y: float, 
        radius: int = 5000
    ) -> List[Dict]:
        """카카오 API로 장소 검색"""
        url = f"{self.kakao_base_url}/search/keyword.json"
        params = {
            'query': keyword,
            'x': x,
            'y': y,
            'radius': radius,
            'size': 15,  # 키워드당 최대 15개
            'sort': 'distance'  # 거리순 정렬
        }
        
        response = requests.get(
            url, 
            headers=self._get_kakao_headers(), 
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        places = []
        
        for place in data.get('documents', []):
            places.append({
                'kakao_id': place.get('id'),
                'name': place.get('place_name'),
                'category': place.get('category_name', '').split(' > ')[-1],  # 마지막 카테고리만
                'address': place.get('address_name'),
                'road_address': place.get('road_address_name'),
                'phone': place.get('phone'),
                'latitude': float(place.get('y', 0)),
                'longitude': float(place.get('x', 0)),
                'distance': place.get('distance', '0'),
                'place_url': place.get('place_url'),
                'search_keyword': keyword
            })
        
        return places
    
    def _deduplicate_and_score_places(
        self, 
        places: List[Dict], 
        user_preferences: Dict,
        user_lat: float,
        user_lng: float
    ) -> List[Dict]:
        """장소 중복 제거 및 점수 계산"""
        # 카카오 ID 기준으로 중복 제거
        unique_places = {}
        for place in places:
            kakao_id = place['kakao_id']
            if kakao_id not in unique_places:
                unique_places[kakao_id] = place
        
        # 각 장소에 점수 부여
        scored_places = []
        for place in unique_places.values():
            score = self._calculate_place_score(place, user_preferences, user_lat, user_lng)
            place['score'] = score
            scored_places.append(place)
        
        return scored_places
    
    def _calculate_place_score(
        self, 
        place: Dict, 
        user_preferences: Dict,
        user_lat: float,
        user_lng: float
    ) -> float:
        """장소 점수 계산"""
        score = 0.0
        
        # 거리 점수 (가까울수록 높은 점수)
        distance = float(place.get('distance', 0))
        if distance > 0:
            distance_score = max(0, 10 - (distance / 500))  # 500m마다 1점 감소
            score += distance_score * 0.3
        
        # 카테고리 점수
        category = place.get('category', '').lower()
        food_pref = user_preferences.get('food_preference', 'cafe')
        
        category_score = 0
        if food_pref == 'cafe' and any(word in category for word in ['카페', '커피', '디저트']):
            category_score = 10
        elif food_pref == 'restaurant' and any(word in category for word in ['음식점', '식당', '한식', '양식', '중식']):
            category_score = 10
        elif food_pref == 'bar' and any(word in category for word in ['주점', '바', '펍']):
            category_score = 10
        else:
            category_score = 5  # 기본 점수
        
        score += category_score * 0.4
        
        # 키워드 매칭 점수
        search_keyword = place.get('search_keyword', '')
        if search_keyword and search_keyword in place.get('name', ''):
            score += 5 * 0.2
        
        # 정보 완성도 점수
        completeness = 0
        if place.get('phone'):
            completeness += 1
        if place.get('road_address'):
            completeness += 1
        if place.get('place_url'):
            completeness += 1
        
        score += completeness * 0.1
        
        return round(score, 2)
    
    def select_diverse_cards(
        self, 
        places: List[Dict], 
        count: int = 25
    ) -> List[Dict]:
        """다양성을 고려하여 카드 선택
        
        Args:
            places: 후보 장소 리스트
            count: 선택할 카드 수
        
        Returns:
            선택된 카드 리스트
        """
        if len(places) <= count:
            return places
        
        selected = []
        categories_used = []
        
        # 높은 점수 순으로 정렬
        sorted_places = sorted(places, key=lambda x: x['score'], reverse=True)
        
        # 다양한 카테고리에서 선택
        for place in sorted_places:
            if len(selected) >= count:
                break
                
            category = place.get('category', '기타')
            
            # 같은 카테고리가 너무 많지 않도록 제한 (최대 5개)
            category_count = sum(1 for p in selected if p.get('category') == category)
            if category_count < 5:
                selected.append(place)
                if category not in categories_used:
                    categories_used.append(category)
        
        # 아직 부족하면 나머지 고득점 장소로 채움
        while len(selected) < count and len(selected) < len(sorted_places):
            for place in sorted_places:
                if place not in selected:
                    selected.append(place)
                    if len(selected) >= count:
                        break
        
        return selected[:count]


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간의 거리 계산 (하버사인 공식)"""
    import math
    
    R = 6371.0  # 지구 반지름 (km)
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = (math.sin(dlat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return round(R * c, 2)
