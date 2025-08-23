from django.urls import path, include
from rest_framework import routers
from .views import *

app_name = "places"

default_router = routers.SimpleRouter(trailing_slash=False)
default_router.register("places", PlaceViewSet, basename="places")

route_router = routers.SimpleRouter(trailing_slash=False)
route_router.register("routes", PlaceRouteViewSet, basename="routes")

chat_router = routers.SimpleRouter(trailing_slash=False)
chat_router.register("chats", ChatViewSet, basename="chats")

snapshot_router = routers.SimpleRouter(trailing_slash=False)
snapshot_router.register("routes/snapshots", RouteSnapshotViewSet, basename="snapshots")

urlpatterns = [
    path("", include(default_router.urls)),
    path("", include(route_router.urls)),   
    path("", include(chat_router.urls)),
    path("", include(snapshot_router.urls)),
]

# Media files는 메인 project/urls.py에서 처리하므로 여기서는 제거
# + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)