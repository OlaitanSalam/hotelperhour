# bookings/urls.py
from django.urls import path
from . import views
from .views import get_loyalty_discount
urlpatterns = [
    path('room/<int:room_id>/book/', views.book_room, name='book_room'),
    path('confirmation/<str:booking_reference>/', views.booking_confirmation, name='booking_confirmation'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('payment/<str:booking_reference>/', views.initiate_payment, name='initiate_payment'),
    
    path('webhook/', views.paystack_webhook, name='paystack_webhook'),
    path('verify/', views.verify_booking, name='verify_bookings'),
    path('cancel/<str:booking_reference>/', views.cancel_booking, name='cancel_booking'),
    path('room/<int:room_id>/check_availability/', views.check_availability, name='check_availability'),
    
]