# """
# Wiki 앱 Django Admin 설정
# - WikiPlace, WikiSearchHistory 모델 관리
# """

# from django.contrib import admin
# from .models import WikiPlace, WikiSearchHistory


# @admin.register(WikiPlace)
# class WikiPlaceAdmin(admin.ModelAdmin):
#     """WikiPlace 관리자 페이지 설정"""
#     list_display = [
#         'shop_name', 
#         # 'place',
#         'average_review_score', 
#         'total_review_count',
#         'ai_summary_updated_at',
#         'created_at'
#     ]
    
#     list_filter = [
#         'created_at',
#         'ai_summary_updated_at',
#         'average_review_score'
#     ]
    
#     search_fields = [
#         'shop_name',
#         'place__name',
#         'place__address',
#         'kakao_place_id',
#         'google_place_id'
#     ]
    
#     readonly_fields = [
#         # 'place',
#         'average_review_score',
#         'total_review_count', 
#         'created_at',
#         'updated_at',
#         'ai_summary_updated_at'
#     ]
    
#     fieldsets = (
#         ('기본 정보', {
#             'fields': ('place', 'shop_name', 'shop_image')
#         }),
#         ('외부 API 연동', {
#             'fields': ('kakao_place_id', 'google_place_id')
#         }),
#         ('AI 요약', {
#             'fields': ('ai_summation', 'ai_summation_info', 'ai_summary_updated_at'),
#             'classes': ('collapse',)
#         }),
#         ('기본 정보', {
#             'fields': ('basic_information', 'basic_information_info'),
#             'classes': ('collapse',)
#         }),
#         ('통계 (읽기 전용)', {
#             'fields': ('average_review_score', 'total_review_count'),
#             'classes': ('collapse',)
#         }),
#         ('시간 정보 (읽기 전용)', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )

#     def get_queryset(self, request):
#         """관련 객체를 미리 로드하여 성능 최적화"""
#         queryset = super().get_queryset(request)
#         return queryset.select_related('place')


# @admin.register(WikiSearchHistory)
# class WikiSearchHistoryAdmin(admin.ModelAdmin):
#     """WikiSearchHistory 관리자 페이지 설정"""
#     list_display = [
#         'search_query',
#         'search_type', 
#         'result_count',
#         'session_key',
#         'created_at'
#     ]
    
#     list_filter = [
#         'search_type',
#         'created_at',
#         'result_count'
#     ]
    
#     search_fields = [
#         'search_query',
#         'session_key'
#     ]
    
#     readonly_fields = [
#         'created_at'
#     ]
    
#     date_hierarchy = 'created_at'
    
#     # 검색 기록은 읽기 전용으로 설정 (삭제만 허용)
#     def has_add_permission(self, request):
#         return False
    
#     def has_change_permission(self, request, obj=None):
#         return False

# admin.py
from django.contrib import admin
from .models import WikiPlace, Review

@admin.register(WikiPlace)
class WikiPlaceAdmin(admin.ModelAdmin):
    list_display = ("shop_name", "google_place_id", "average_review_score", "total_review_count", "updated_at")
    search_fields = ("shop_name", "google_place_id", "kakao_place_id")

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("wiki_place", "review_score", "session_key", "created_at", "like_num")
    list_filter = ("review_score", "created_at")
    search_fields = ("wiki_place__shop_name", "session_key")
