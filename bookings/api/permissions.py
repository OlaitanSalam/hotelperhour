from rest_framework.permissions import BasePermission
from hotels.models import Hotel
from django.contrib.contenttypes.models import ContentType

class IsBookingOwnerOrHotelOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            user_content_type = ContentType.objects.get_for_model(request.user)
            is_booking_owner = (obj.content_type == user_content_type and obj.object_id == request.user.id)
            return is_booking_owner or (request.user.is_hotel_owner and obj.room.hotel.owner == request.user)
        return (obj.content_type == ContentType.objects.get_for_model(request.user) and obj.object_id == request.user.id) or request.user.is_superuser