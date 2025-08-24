from django.urls import path
from . import views
from .views import customer_register, customer_login, customer_dashboard
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from .views import (
    CustomerPasswordResetView,
    CustomerPasswordResetConfirmView,
    customer_password_reset_done,
    customer_password_reset_complete,
)

  
# urls.py
urlpatterns = [
   
    path('customer/register/', customer_register, name='customer_register'),
    path('customer/login/', customer_login, name='customer_login'),
    path('customer/dashboard/', customer_dashboard, name='customer_dashboard'),
    path('activation-sent/', views.customer_activation_sent, name='customer_activation_sent'),
    path('activate/<uidb64>/<token>/', views.customer_activate, name='customer_activate'),
    
    path('profile/', views.customer_profile, name='customer_profile'),
    path('verify-booking/', views.verify_booking, name='verify_booking'),
     # 🔹 Password reset URLs for Customers
    path("customer/password_reset/", CustomerPasswordResetView.as_view(), name="customer_password_reset"),
    path("customer/password_reset/done/", customer_password_reset_done, name="customer_password_reset_done"),
    path("customer/reset/<uidb64>/<token>/", CustomerPasswordResetConfirmView.as_view(), name="customer_password_reset_confirm"),
    path("customer/reset/done/", customer_password_reset_complete, name="customer_password_reset_complete"),

    
]