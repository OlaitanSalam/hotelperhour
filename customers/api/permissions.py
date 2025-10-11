from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsCustomerOwnerOrAdmin(BasePermission):
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
            # For customers: only their own data
            if hasattr(request.user, 'is_customer') and request.user.is_customer:
                return obj.email == request.user.email
            # For admin users: all records
            return request.user.is_superuser or request.user.is_staff
        
        # Write permissions are only allowed to the owner or admin
        return (obj.email == request.user.email) or request.user.is_superuser

class IsAdminForLoyaltyRule(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_superuser