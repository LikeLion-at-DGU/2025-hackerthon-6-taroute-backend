from django.db import models
from django.utils import timezone
from places.models import Place  # 기존 Place 모델 재사용


def default_json():
    """JSONField의 기본값으로 사용할 빈 딕셔너리를 반환하는 함수"""
    return {}


def wiki_image_upload_path(instance, filename):
    """위키 이미지 업로드 경로 설정 함수
    - 장소별로 폴더를 나누어 이미지 관리
    """
    return f"wiki/{instance.wiki_place.google_place_id}/{filename}"


class WikiPlace(models.Model):
    """위키 장소 정보 모델
    - 기존 Place 모델을 확장하여 위키 전용 추가 정보 저장
    - AI 요약, 기본 정보 등을 포함
    """

    # 기존 Place 모델과 일대일 관계 설정
    # place = models.OneToOneField(
    #     Place,
    #     on_delete=models.CASCADE,
    #     primary_key=True,
    #     #"기존 장소 모델과 연결"
    # )

    # 위키 전용 추가 필드들
    shop_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        # "🔥상점명 (장소명과 다를 수 있음)"
    )

    # shop_image = models.ImageField(
    #     upload_to=wiki_image_upload_path,
    #     blank=True,
    #     null=True,
    #     #"위키 전용 장소 대표 이미지"
    # )

    # AI 요약 정보
    ai_summation = models.TextField(
        blank=True,
        null=True,
        # "OpenAI가 생성한 장소 요약"
    )

    ai_summation_info = models.JSONField(
        default=default_json,
        blank=True,
        # "AI 요약 생성 시 사용된 메타데이터 (모델, 생성시간 등)"
    )

    # 기본 정보
    basic_information = models.TextField(
        blank=True,
        null=True,
        # "장소의 기본 정보 (영업시간, 가격대 등)"
    )

    basic_information_info = models.JSONField(
        default=default_json,
        blank=True,
        # "기본 정보의 메타데이터 (출처, 업데이트 시간 등)"
    )

    # 카카오 Place ID (검색 결과와 매핑용)
    kakao_place_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        # "카카오 API에서 제공하는 장소 고유 ID"
    )

    # 구글 Place ID (향후 구글 API 연동용)
    google_place_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        # "🔥구글 Places API에서 제공하는 장소 고유 ID"
    )

    # 평점 정보 (캐시용)
    average_review_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        # "🔥전체 리뷰의 평균 점수"
    )

    total_review_count = models.IntegerField(
        default=0,
        # "🔥전체 리뷰 개수"
    )

    # 위키 정보 생성/수정 시간
    created_at = models.DateTimeField(
        default=timezone.now,
        # "🔥위키 정보 최초 생성 시간"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        # "🔥위키 정보 마지막 수정 시간"
    )

    # AI 요약 마지막 업데이트 시간
    ai_summary_updated_at = models.DateTimeField(
        blank=True,
        null=True,
        # "AI 요약이 마지막으로 생성/수정된 시간"
    )

    class Meta:
        verbose_name = "위키 장소"
        verbose_name_plural = "위키 장소들"
        # 카카오 Place ID로 검색 최적화
        indexes = [
            models.Index(fields=["kakao_place_id"]),
            models.Index(fields=["google_place_id"]),
        ]

    def __str__(self):
        return f"WikiPlace: {self.shop_name or self.google_place_id}"

    def update_review_stats(self):
        """리뷰 통계 업데이트 메서드
        - 평균 점수와 리뷰 개수를 재계산하여 캐시
        """
        reviews = self.reviews.all()

        if reviews.exists():
            # 평균 점수 계산
            self.average_review_score = (
                reviews.aggregate(avg_score=models.Avg("review_score"))["avg_score"]
                or 0.00
            )

            # 리뷰 개수 계산
            self.total_review_count = reviews.count()
        else:
            self.average_review_score = 0.00
            self.total_review_count = 0

        self.save(update_fields=["average_review_score", "total_review_count"])


class WikiSearchHistory(models.Model):
    """위키 검색 기록 모델
    - 사용자 검색 패턴 분석용
    - 인기 검색어 추출용
    """

    search_query = models.CharField(
        max_length=200,
        # "사용자가 입력한 검색어"
    )

    search_type = models.CharField(
        max_length=20,
        choices=[
            ("place_name", "장소명 검색"),
            ("location_name", "지역명 검색"),
            ("category", "카테고리 검색"),
            ("mixed", "복합 검색"),
        ],
        default="mixed",
        # "검색 유형"
    )

    # 검색 결과 개수
    result_count = models.IntegerField(default=0, help_text="검색 결과 개수")

    # 검색자 정보 (세션 기반)
    session_key = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        # "검색자 세션 키"
    )

    # 검색 위치 정보
    search_longitude = models.FloatField(
        blank=True,
        null=True,
        # "검색 시점의 사용자 위치 경도"
    )

    search_latitude = models.FloatField(
        blank=True,
        null=True,
        # "검색 시점의 사용자 위치 위도"
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        # "검색 시간"
    )

    class Meta:
        verbose_name = "위키 검색 기록"
        verbose_name_plural = "위키 검색 기록들"
        indexes = [
            models.Index(fields=["search_query"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["session_key"]),
        ]

    def __str__(self):
        return f"검색: {self.search_query} ({self.created_at})"

###############################################################################################
class Review(models.Model):
    """리뷰 모델"""

    wiki_place = models.ForeignKey(
        "WikiPlace", on_delete=models.CASCADE, null=False, related_name="reviews"
    )
    # place_id = models.CharField(max_length=100, null=True, blank=True)

    # place = models.ForeignKey(
    #     Place,
    #     on_delete=models.CASCADE,
    #     related_name='reviews',
    #     #"리뷰가 작성된 장소"
    # )

    review_content = models.TextField(
        # "리뷰 내용"
    )

    review_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        # "리뷰 점수 (1-5)"
    )

    review_image = models.ImageField(
        upload_to=wiki_image_upload_path,
        blank=True,
        null=True,
        # "리뷰 이미지"
    )

    session_key = models.CharField(
        max_length=64,
        # "작성자 세션 키"
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        # "리뷰 작성 시간"
    )

    like_num = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "리뷰"
        verbose_name_plural = "리뷰들"

    def __str__(self):
        return f"리뷰: {self.wiki_place} - {self.review_score}점"

##################################################################################################
class Report(models.Model):
    """신고 모델"""

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        # "신고된 리뷰"
    )

    reason = models.CharField(
        max_length=50,
        # "신고 사유"
    )

    report_title = models.CharField(
        max_length=100,
        # "신고 제목"
    )

    report_content = models.TextField(
        # "신고 내용"
    )

    session_key = models.CharField(
        max_length=64,
        # "신고자 세션 키"
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        # "신고 시간"
    )

    class Meta:
        verbose_name = "신고"
        verbose_name_plural = "신고들"

    def __str__(self):
        return f"신고: {self.report_title}"
