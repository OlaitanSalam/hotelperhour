from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, LoyaltyRuleViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'loyalty-rules', LoyaltyRuleViewSet, basename='loyaltyrule')

urlpatterns = [
    path('', include(router.urls)),
    re_path(r'^customers/(?P<email>[^/]+)/$', CustomerViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='customer-detail'),
]