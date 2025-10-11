from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HotelViewSet,
    RoomViewSet,
    AmenityViewSet,
    ExtraServiceViewSet,
    ReviewViewSet,
    AppFeedbackViewSet,
    HotelImageViewSet,
    HotelPolicyViewSet,
)

# DRF Router handles CRUD endpoints automatically
router = DefaultRouter()
router.register(r'hotels', HotelViewSet, basename='hotel')
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'amenities', AmenityViewSet, basename='amenity')
router.register(r'extras', ExtraServiceViewSet, basename='extra')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'feedbacks', AppFeedbackViewSet, basename='feedback')
router.register(r'hotel-images', HotelImageViewSet, basename='hotelimage')
router.register(r'policies', HotelPolicyViewSet, basename='hotelpolicy')

urlpatterns = [
    path('', include(router.urls)),
]
