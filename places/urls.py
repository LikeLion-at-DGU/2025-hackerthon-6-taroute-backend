from django.urls import path, include
from rest_framework import routers
from .views import *

from django.conf.urls.static import static
from django.conf import settings

app_name = "places"

default_router = routers.SimpleRouter(trailing_slash=False)
default_router.register("places", PlaceViewSet, basename="places")

urlpatterns = [
    path("", include(default_router.urls)),
] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)