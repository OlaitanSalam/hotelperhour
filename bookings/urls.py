# bookings/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('room/<int:room_id>/book/', views.book_room, name='book_room'),
    path('confirmation/<uuid:booking_reference>/', views.booking_confirmation, name='booking_confirmation'),
    path('payment/<uuid:booking_reference>/', views.initiate_payment, name='initiate_payment'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('webhook/', views.paystack_webhook, name='paystack_webhook'),
    path('verify/', views.verify_booking, name='verify_booking'),
    path('cancel/<uuid:booking_reference>/', views.cancel_booking, name='cancel_booking'),
    path('room/<int:room_id>/check_availability/', views.check_availability, name='check_availability'),
]