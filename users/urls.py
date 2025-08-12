# users/urls.py
from django.urls import path
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from . import views
from .views import CustomLoginView
from users.views import unified_logout

urlpatterns = [
       path('', views.home, name='home'),
       path('register/', views.register, name='register'),
       path('activation-sent/', views.activation_sent, name='activation_sent'),
       path('activate/<uidb64>/<token>/', views.activate, name='activate'),
       path('login/', CustomLoginView.as_view(), name='login'),
       #path('login/', LoginView.as_view(template_name='users/login.html'), name='login'),
       path('password_reset/', PasswordResetView.as_view(template_name='users/password_reset.html'), name='password_reset'),
       path('password_reset/done/', PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), name='password_reset_done'),
       path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), name='password_reset_confirm'),
       path('reset/done/', PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), name='password_reset_complete'),
       path('dashboard/', views.dashboard, name='dashboard'),
       path('logout/', views.logout_view, name='logout'),
       path('logout/', unified_logout, name='unified_logout'),
]