from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.views import CustomTokenRefreshView, CustomTokenObtainPairView, UserModelViewSet

router = DefaultRouter()

router.register(r'users', UserModelViewSet)
urlpatterns = [
    path('login', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls))
]
