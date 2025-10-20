"""
URL configuration for hotelperhour project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from bookings.views import book_room, get_loyalty_discount
from hotels import views as hotel_views
from rest_framework_simplejwt.views import  TokenRefreshView, TokenObtainPairView
from .auth import CustomTokenObtainPairView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.views.generic import TemplateView



urlpatterns = [
    
    path("admin/", admin.site.urls),

    path('', include('users.urls')),
    #path("users/", include("users.urls")),
    path("hotels/", include("hotels.urls")),
    path("bookings/", include("bookings.urls")),
    path("customers/", include("customers.urls")),
    path("superadmin/", include("superadmin.urls")),
    path('get_loyalty_discount/', get_loyalty_discount, name='get_loyalty_discount'),
    path('about/', hotel_views.about, name='about'),
    path('contacts/', hotel_views.contacts, name='contacts'),
    # API URLs
    path('api/v1/hotels/', include('hotels.api.urls')),  # Include hotels API
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # JWT refresh
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Default JWT login for CustomUsers
    path('api/token/customer/', CustomTokenObtainPairView.as_view(), name='customer_token_obtain_pair'),  # Custom JWT login for Customers
    path('api/v1/bookings/', include('bookings.api.urls')),
    path('api/v1/customers/', include('customers.api.urls')),
    path('api/v1/users/', include('users.api.urls')),
    # privacy policy, refund policy and terms of service
     path('privacy/', TemplateView.as_view(template_name='privacy_policy.html'), name='privacy'),
     path('terms/', TemplateView.as_view(template_name='terms_&_condition.html'), name='terms'),
        path('refund-policy/', TemplateView.as_view(template_name='refund_policy.html'), name='refund_policy'),

    # OpenAPI schema + Swagger UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
