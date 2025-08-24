from django.urls import path
from . import views
from .views import HotelDetailView

urlpatterns = [
    path('dashboard/', views.hotel_dashboard, name='hotel_dashboard'),
    path('create/', views.hotel_create, name='hotel_create'),
    path('', views.hotel_list, name='hotel_list'),
    path('nearby/', views.nearby_hotels, name='nearby_hotels'),  # Moved before <slug:slug>/
    path('about/', views.about, name='about'),
    path('contacts/', views.contacts, name='contacts'),
     path('submit-feedback/', views.submit_feedback, name='submit_feedback'),
    
    path('success/', views.contact_success, name='contact_success'),
    path('<slug:slug>/', views.HotelDetailView.as_view(), name='hotel_detail'),  # Moved after specific paths
    path('<slug:slug>/edit/', views.hotel_edit, name='hotel_edit'),
    path('<slug:slug>/delete/', views.hotel_delete, name='hotel_delete'),
    path('<slug:slug>/bookings/', views.hotel_bookings, name='hotel_bookings'),
    path('<slug:slug>/rooms/', views.hotel_rooms, name='hotel_rooms'),
    path('<slug:slug>/sales/', views.hotel_sales_report, name='hotel_sales_report'),
    path('<slug:hotel_slug>/rooms/toggle/<int:room_id>/', views.toggle_room_availability, name='toggle_room_availability'),
    path('hotels/<slug:slug>/bookings/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('hotels/<slug:slug>/bookings/<int:booking_id>/confirm-cancel/', 
     views.confirm_cancel_booking, 
     name='confirm_cancel_booking'),
    
    # Other patterns...
]