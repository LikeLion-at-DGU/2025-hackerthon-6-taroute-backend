# 2025-hackerthon-6-taroute-backend
2025 멋쟁이사자처럼 중앙해커톤 동국대 6팀 'taroute' 백엔드 레포지토리입니다.

Taroute Backend API
한 줄 소개: 타로 테마 기반 사용자 취향 분석을 통한 최적 장소 추천 및 경로 안내 서비스
# 아키텍처
<img width="2210" height="1272" alt="architecture_diagram" src="https://github.com/user-attachments/assets/5a7a1019-6520-401d-ab20-61a2f8703f99" />

# 요구사항
Python 3.12+
Git
가상환경 (venv 추천)

# 리포지토리 클론
git clone https://github.com/your-org/taroute-backend.git
cd taroute-backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 📚 API 문서
전체 API는 Swagger/ReDoc에서 확인 가능. 주요 엔드포인트 요약:

places 앱 (장소/경로)

GET /api/places/recommend/: 주변 추천 장소

GET /api/places/google_place/: 구글 장소 검색

GET /api/places/save_place/: 장소 찜하기

GET /api/places/category_search/: 카테고리별 검색

POST /api/routes/path/: 경로 안내 (자동차/대중교통/도보)

GET /api/routes/ai_routes/: AI 최적 경로 추천

POST /api/routes/snapshots/: 공유 링크 생성

wiki 앱 (위키/리뷰)

GET /api/wiki/search/: 위키 검색

GET /api/wiki/detail/: 장소 세부 정보 (AI 요약)

GET /api/reviews/by_place/: 후기 조회

POST /api/reviews/: 후기 작성

POST /api/reports/: 후기 신고

taro 앱 (타로 AI)

POST /api/taro/chat/: 타루 AI 대화

POST /api/taro/card_select/: 카드 추천

POST /api/taro/pick/: 카드 선택 (장바구니)

GET /api/taro/cart/: 장바구니 조회

상세 스펙은 Swagger 문서 참조.

# 🛡️ 인증 & 보안
세션 기반: Django Session 사용 (24시간 만료)
CORS: 허용 도메인 제한 (localhost, taroute.com 등)
CSRF: SameSite=None 설정 (크로스 사이트 지원)

# 📊 데이터 모델
places: PopularKeyward (인기 키워드), RouteSnapshot (경로 공유)
wiki: WikiPlace (장소 정보), Review (리뷰), Report (신고)
taro: TaroConversation (대화), TaroCard (카드), TaroCartItem (장바구니)

# 📞 연락처
개발팀: 2025 멋쟁이사자처럼 중앙해커톤 동국대 6팀
이메일: ohsein37@gmail.com
이슈 트래커: GitHub Issues
