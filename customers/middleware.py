from django.shortcuts import redirect
from django.contrib import messages
from customers.models import Customer

class RestrictAdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Existing admin restriction
        if request.path.startswith('/admin/') and request.user.is_authenticated:
            if isinstance(request.user, Customer) or not request.user.is_staff:
                messages.error(request, "You do not have permission to access the admin page.")
                return redirect('home')  # Replace 'home' with your desired redirect URL
        
        # New: Handle login attempts while already authenticated
        if request.user.is_authenticated:
            # Check if trying to access customer login while hotel owner, or vice versa
            if request.path == '/customer/login/' and request.user.is_hotel_owner:  # Adjust to your customer login URL
                messages.error(request, "Logout first to switch roles.")
                return redirect('hotel_dashboard')  # Redirect to hotel dashboard
            elif request.path == '/hotel/login/' and request.user.is_customer:  # Adjust to your hotel login URL
                messages.error(request, "Logout first to switch roles.")
                return redirect('customer_dashboard')  # Redirect to customer dashboard
        
        response = self.get_response(request)
        return response

# customers/middleware.py
class RoleBasedRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Redirect authenticated users trying to access login pages
        if request.user.is_authenticated:
            if request.path in ['/customer/login/', '/hotel/login/']:
                if request.user.is_customer:
                    return redirect('customer_dashboard')
                elif request.user.is_hotel_owner:
                    return redirect('hotel_dashboard')
        
        return response