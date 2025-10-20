from django.urls import path
from .views import (
    DashboardView,
    HotelListView,
    HotelDetailView,
    HotelUpdateView,
    HotelDeleteView,
    toggle_hotel_approval,
    CustomerListView,
    CustomerDeleteView,
    OwnerListView,
    OwnerDeleteView,
)

urlpatterns = [
    path('', DashboardView.as_view(), name='superadmin_dashboard'),
    path('hotels/', HotelListView.as_view(), name='superadmin_hotel_list'),
    path('hotels/<slug:slug>/', HotelDetailView.as_view(), name='superadmin_hotel_detail'),
    path('hotels/<slug:slug>/edit/', HotelUpdateView.as_view(), name='superadmin_hotel_edit'),
    path('hotels/<slug:slug>/delete/', HotelDeleteView.as_view(), name='superadmin_hotel_delete'),
    path('hotels/<int:pk>/toggle-approval/', toggle_hotel_approval, name='superadmin_hotel_toggle_approve'),
    path('customers/', CustomerListView.as_view(), name='superadmin_customer_list'),
    path('customers/<int:pk>/delete/', CustomerDeleteView.as_view(), name='superadmin_customer_delete'),
    path('owners/', OwnerListView.as_view(), name='superadmin_owner_list'),
    path('owners/<int:pk>/delete/', OwnerDeleteView.as_view(), name='superadmin_owner_delete'),
]