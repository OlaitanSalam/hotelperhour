from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, BookingDurationViewSet

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'durations', BookingDurationViewSet, basename='duration')

urlpatterns = [
    path('', include(router.urls)),
]