from django.urls import include, path
from rest_framework import routers
from stripeHooks import views as hook_views



router = routers.DefaultRouter()
router.register(r'hooks', hook_views.HookViewSet, basename='hooks')

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', include(router.urls)),
]
