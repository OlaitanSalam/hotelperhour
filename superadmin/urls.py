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
    # NEW PAYOUT VIEWS
    PayoutDashboardView,
    PayoutDetailView,
    PayoutHistoryView,
    create_payout,
    complete_payout,
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
    # NEW PAYOUT URLS
    path('payouts/', PayoutDashboardView.as_view(), name='superadmin_payout_dashboard'),
    path('payouts/history/', PayoutHistoryView.as_view(), name='superadmin_payout_history'),
    path('payouts/<int:payout_id>/', PayoutDetailView.as_view(), name='superadmin_payout_detail'),
    path('payouts/create/<int:hotel_id>/', create_payout, name='superadmin_create_payout'),
    path('payouts/<int:payout_id>/complete/', complete_payout, name='superadmin_complete_payout'),
]