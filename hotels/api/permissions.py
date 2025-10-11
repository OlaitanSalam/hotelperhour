from rest_framework.permissions import BasePermission

class IsHotelOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in BasePermission.SAFE_METHODS:  # GET, HEAD, OPTIONS
            return True  # Anyone can read
        return obj.owner == request.user  # Only owner can edit/delete