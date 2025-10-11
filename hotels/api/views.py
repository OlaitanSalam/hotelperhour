from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404
from geopy.distance import geodesic

from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response
from rest_framework.decorators import action

from hotels.models import (
    Hotel, Room, Amenity, ExtraService, Review, AppFeedback, HotelImage, HotelPolicy
)
from .serializers import (
    HotelSerializer, RoomSerializer, AmenitySerializer, ExtraServiceSerializer,
    ReviewSerializer, AppFeedbackSerializer, HotelImageSerializer, HotelPolicySerializer
)
from .permissions import IsHotelOwnerOrReadOnly  # Custom permission


# -------------------- HOTEL --------------------
class HotelViewSet(viewsets.ModelViewSet):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsHotelOwnerOrReadOnly]
    lookup_field = 'slug'

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, "is_hotel_owner", False):
            return Hotel.objects.filter(owner=user)
        return Hotel.objects.filter(is_approved=True)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get'])
    def nearby(self, request, slug=None):
        """Return hotels within 10km radius"""
        hotel = self.get_object()
        nearby_qs = Hotel.objects.filter(is_approved=True).exclude(id=hotel.id)

        nearby = [
            h for h in nearby_qs
            if h.latitude and h.longitude and
            hotel.latitude and hotel.longitude and
            geodesic((hotel.latitude, hotel.longitude), (h.latitude, h.longitude)).km < 10
        ]
        serializer = self.get_serializer(nearby, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# -------------------- ROOM --------------------
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsHotelOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, "is_hotel_owner", False):
            return Room.objects.filter(hotel__owner=user)
        return Room.objects.filter(is_available=True, hotel__is_approved=True)

    def perform_create(self, serializer):
        hotel_slug = self.request.query_params.get('hotel_slug')
        hotel = get_object_or_404(Hotel, slug=hotel_slug, owner=self.request.user)
        serializer.save(hotel=hotel)


# -------------------- AMENITY --------------------
class AmenityViewSet(viewsets.ModelViewSet):
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer
    permission_classes = [permissions.IsAdminUser]


# -------------------- EXTRASERVICE --------------------
class ExtraServiceViewSet(viewsets.ModelViewSet):
    queryset = ExtraService.objects.all()
    serializer_class = ExtraServiceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsHotelOwnerOrReadOnly]


# -------------------- REVIEW --------------------
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        hotel_slug = self.request.data.get('hotel_slug')
        hotel = get_object_or_404(Hotel, slug=hotel_slug)
        user_email = self.request.user.email

        last_review = Review.objects.filter(hotel=hotel, email=user_email).order_by('-created_at').first()
        if last_review and (timezone.now() - last_review.created_at) < timedelta(hours=24):
            raise serializers.ValidationError("You can only post one review per hotel every 24 hours.")

        serializer.save(hotel=hotel)


# -------------------- APP FEEDBACK --------------------
class AppFeedbackViewSet(viewsets.ModelViewSet):
    queryset = AppFeedback.objects.all()
    serializer_class = AppFeedbackSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        serializer.save(created_at=timezone.now())


# -------------------- HOTEL IMAGE --------------------
class HotelImageViewSet(viewsets.ModelViewSet):
    queryset = HotelImage.objects.all()
    serializer_class = HotelImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsHotelOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, "is_hotel_owner", False):
            return HotelImage.objects.filter(hotel__owner=user)
        return HotelImage.objects.filter(hotel__is_approved=True)

    def perform_create(self, serializer):
        hotel_slug = self.request.data.get('hotel_slug')
        hotel = get_object_or_404(Hotel, slug=hotel_slug, owner=self.request.user)
        serializer.save(hotel=hotel)


# -------------------- HOTEL POLICY --------------------
class HotelPolicyViewSet(viewsets.ModelViewSet):
    queryset = HotelPolicy.objects.all()
    serializer_class = HotelPolicySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsHotelOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, "is_hotel_owner", False):
            return HotelPolicy.objects.filter(hotel__owner=user)
        return HotelPolicy.objects.filter(hotel__is_approved=True)

    def perform_create(self, serializer):
        hotel_slug = self.request.data.get('hotel_slug')
        hotel = get_object_or_404(Hotel, slug=hotel_slug, owner=self.request.user)
        serializer.save(hotel=hotel)
