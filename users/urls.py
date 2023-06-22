from django.urls import include, path
from rest_framework import routers
from users import views as user_views

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = routers.DefaultRouter()
router.register(r'users', user_views.UserViewSet)
router.register(r'user', user_views.ResetPasswordEmailViewSet,
                basename='resetPassword')
router.register(r'emailvalidation', user_views.ConfirmEmailViewSet,
                basename='resetPassword')
router.register(r'groups', user_views.GroupViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', include(router.urls)),
    path('token/', user_views.EmailTokenObtainPairView.as_view(),
         name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
