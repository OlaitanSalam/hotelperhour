from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        # Allow registration without authentication
        if view.action == 'register':
            return True
        # Allow activation without authentication
        if view.action == 'activate':
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in SAFE_METHODS:
            return request.user.is_superuser or request.user.is_staff or obj == request.user
        
        # Write permissions are only allowed to the owner or admin
        return obj == request.user or request.user.is_superuser