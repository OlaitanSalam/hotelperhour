from django.urls import path
from . import views
from .views import customer_register, customer_login, customer_dashboard, customer_logout
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView

# urls.py
urlpatterns = [
   
    path('customer/register/', customer_register, name='customer_register'),
    path('customer/login/', customer_login, name='customer_login'),
    path('customer/dashboard/', customer_dashboard, name='customer_dashboard'),
    path('logout/', customer_logout, name='logout'),  # Shared logout
    path('password_reset/', PasswordResetView.as_view(template_name='users/password_reset.html'), name='password_reset'),
       path('password_reset/done/', PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), name='password_reset_done'),
       path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), name='password_reset_confirm'),
       path('reset/done/', PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), name='password_reset_complete'),
       path('profile/', views.customer_profile, name='customer_profile'),
    path('verify-booking/', views.verify_booking, name='verify_booking'),

    # ... (other paths)
]