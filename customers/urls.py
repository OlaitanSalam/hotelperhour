from django.urls import path
from . import views
from .views import customer_register, customer_login, customer_dashboard
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView

# urls.py
urlpatterns = [
   
    path('customer/register/', customer_register, name='customer_register'),
    path('customer/login/', customer_login, name='customer_login'),
    path('customer/dashboard/', customer_dashboard, name='customer_dashboard'),
    path('activation-sent/', views.customer_activation_sent, name='customer_activation_sent'),
    path('activate/<uidb64>/<token>/', views.customer_activate, name='customer_activate'),
    path('password_reset/', PasswordResetView.as_view(template_name='customers/password_reset.html'), name='password_reset'),
       path('password_reset/done/', PasswordResetDoneView.as_view(template_name='customers/password_reset_done.html'), name='password_reset_done'),
       path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(template_name='customers/password_reset_confirm.html'), name='password_reset_confirm'),
       path('reset/done/', PasswordResetCompleteView.as_view(template_name='customers/password_reset_complete.html'), name='password_reset_complete'),
       path('profile/', views.customer_profile, name='customer_profile'),
    path('verify-booking/', views.verify_booking, name='verify_booking'),

    # ... (other paths)
]