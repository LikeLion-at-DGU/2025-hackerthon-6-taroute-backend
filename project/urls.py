"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularJSONAPIView, SpectacularRedocView, SpectacularSwaggerView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('wiki/', include('wiki.urls')),
    path('api/schema/', SpectacularJSONAPIView.as_view(), name='schema-json'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema-json'), name='redoc'),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema-json"), name="swagger-ui"),
    path('api/', include('places.urls')),  # places URLs에 api/ prefix 추가
]

# Media files 처리 (개발환경에서만) - 구체적인 패턴만 매치하도록 수정
if settings.DEBUG:
    from django.views.static import serve
    import re
    urlpatterns += [
        path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
        path('static/<path:path>', serve, {'document_root': settings.STATIC_ROOT}),
    ]
