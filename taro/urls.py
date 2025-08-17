"""
Taro 앱 URL 설정
- 타루 대화, 카드 뽑기, 장바구니 관련 API 엔드포인트
"""

from django.urls import path, include
from rest_framework import routers
from django.conf import settings
from django.conf.urls.static import static

from .views import TaroViewSet

app_name = "taro"

# 타로 라우터 설정
router = routers.SimpleRouter(trailing_slash=False)
router.register("taro", TaroViewSet, basename="taro")

urlpatterns = [
    path("", include(router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

"""
API 엔드포인트 정리:

### 4.1 '타루'와의 대화
GET /taro/chat
- 파라미터: session_key, limit
- 응답: 최근 대화 히스토리

POST /taro/chat  
- 요청: session_key, input_text, latitude, longitude, meta
- 응답: output_text (타루의 응답)

### 4.2 카드뽑기

#### 4.2.1 카드 셔플 & 드로우 (25장)
GET /taro/shuffle
- 파라미터: session_key
- 응답: 25장의 카드 정보 (card_id, place_name, distance, category, address, road_address, phone)

#### 4.2.2 카드 다시 뽑기 (1회 제한)
GET /taro/redraw
- 파라미터: session_key
- 응답: 새로운 25장의 카드 정보

#### 4.2.3 카드 선택 (장바구니로 이동)
POST /taro/pick
- 요청: session_key, card_id, selection_note, priority
- 응답: 선택된 카드 정보

### 장바구니 조회
GET /taro/cart
- 파라미터: session_key
- 응답: 선택된 카드들 목록

### 기능 특징:
- 아키네이터 스타일의 질문/응답 시스템
- OpenAI API를 활용한 자연스러운 대화
- 카카오 API를 활용한 실제 장소 검색
- 사용자 취향 분석 기반 맞춤 추천
- 세션 기반 익명 사용자 지원
- 카드 다시 뽑기 1회 제한
- 우선순위 기반 장바구니 관리
"""
