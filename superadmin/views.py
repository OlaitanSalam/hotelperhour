# superadmin/views.py
from django.views.generic import ListView, DetailView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Count, Avg

from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import user_passes_test
from decimal import Decimal
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
import json
import calendar

from hotels.forms import DateRangeForm
from hotels.models import Hotel, Room, Review
from customers.models import Customer
from users.models import CustomUser
from bookings.models import Booking


class SuperuserRequiredMixin(UserPassesTestMixin):
    """
    This mixin ensures only superusers can access these views.
    If a non-superuser tries to access, they'll be redirected to login.
    """
    def test_func(self):
        return self.request.user.is_superuser
    
    def handle_no_permission(self):
        messages.error(self.request, "You must be a superuser to access this page.")
        return redirect('home')


class DashboardView(SuperuserRequiredMixin, ListView):
    template_name = 'superadmin/dashboard.html'
    model = Hotel
    context_object_name = 'recent_hotels'
    
    def get_queryset(self):
        return Hotel.objects.select_related('owner').order_by('-created_at')[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = DateRangeForm(self.request.GET or None)
        now = timezone.now()
        
        # Default to current month if no form data
        if form.is_valid():
            start_date = form.cleaned_data.get('start_date') or (now - timedelta(days=30))
            end_date = form.cleaned_data.get('end_date') or now
        else:
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        
        # Optimized Queries for Counts (O(1) time)
        total_hotels = Hotel.objects.count()
        total_customers = Customer.objects.count()
        total_owners = CustomUser.objects.filter(is_hotel_owner=True).count()
        total_users = total_customers + total_owners
        total_bookings = Booking.objects.filter(is_paid=True).count()
        
        # Revenue (commission = service_charge)
        total_revenue = Booking.objects.filter(is_paid=True).aggregate(
            total=Sum('service_charge')
        )['total'] or Decimal('0.00')
        
        # Period-specific revenue/commission/service_charge (same as revenue here)
        period_revenue = Booking.objects.filter(
            is_paid=True,
            created_at__range=(start_date, end_date)
        ).aggregate(
            total=Sum('service_charge')
        )['total'] or Decimal('0.00')
        
        # Previous period for growth comparison
        prev_start = start_date - (end_date - start_date)
        prev_end = end_date - (end_date - start_date)
        prev_revenue = Booking.objects.filter(
            is_paid=True,
            created_at__range=(prev_start, prev_end)
        ).aggregate(
            total=Sum('service_charge')
        )['total'] or Decimal('0.00')
        
        revenue_growth = ((period_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else (100 if period_revenue > 0 else 0)
        
        # Chart Data - Dynamic based on filter (optimized with annotations)
        view_type = self.request.GET.get('view', 'monthly')
        
        if view_type == 'daily':
            # Last 30 days
            chart_data = Booking.objects.filter(
                is_paid=True,
                created_at__gte=now - timedelta(days=30)
            ).annotate(
                period=TruncDay('created_at')
            ).values('period').annotate(
                revenue=Sum('service_charge')
            ).order_by('period')
            labels = [item['period'].strftime('%b %d') for item in chart_data]
            data = [float(item['revenue'] or 0) for item in chart_data]
        
        elif view_type == 'weekly':
            # Last 12 weeks
            chart_data = []
            for i in range(11, -1, -1):
                week_start = now - timedelta(days=now.weekday() + 7*i)
                week_end = week_start + timedelta(days=6)
                revenue = Booking.objects.filter(
                    is_paid=True,
                    created_at__range=(week_start, week_end)
                ).aggregate(total=Sum('service_charge'))['total'] or 0
                chart_data.append({
                    'label': f"Week of {week_start.strftime('%b %d')}",
                    'revenue': float(revenue)
                })
            labels = [item['label'] for item in chart_data]
            data = [item['revenue'] for item in chart_data]
        
        else:  # Monthly, last 12 months
            chart_data = Booking.objects.filter(
                is_paid=True,
                created_at__gte=now - relativedelta(months=12)
            ).annotate(
                period=TruncMonth('created_at')
            ).values('period').annotate(
                revenue=Sum('service_charge')
            ).order_by('period')
            labels = [item['period'].strftime('%b %Y') for item in chart_data]
            data = [float(item['revenue'] or 0) for item in chart_data]
        
        context.update({
            'form': form,
            'total_hotels': total_hotels,
            'total_users': total_users,
            'total_bookings': total_bookings,
            'total_customers': total_customers,
            'total_revenue': total_revenue,
            'period_revenue': period_revenue,
            'revenue_growth': round(revenue_growth, 2),
            'chart_labels': json.dumps(labels),
            'chart_data': json.dumps(data),
            'view_type': view_type,
        })
        return context


class HotelListView(SuperuserRequiredMixin, ListView):
    """
    Lists all hotels with pagination.
    Allows filtering and shows approval status.
    """
    template_name = 'superadmin/hotel_list.html'
    model = Hotel
    context_object_name = 'hotels'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Hotel.objects.select_related('owner').order_by('-created_at')
        
        # Filter by approval status if specified
        status = self.request.GET.get('status')
        if status == 'approved':
            queryset = queryset.filter(is_approved=True)
        elif status == 'pending':
            queryset = queryset.filter(is_approved=False)
        
        # Search by name or city
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search) | queryset.filter(city__icontains=search)
        
        return queryset


class HotelDetailView(SuperuserRequiredMixin, DetailView):
    """
    Shows detailed hotel information including:
    - Sales statistics
    - Revenue charts
    - Rooms and bookings
    """
    template_name = 'superadmin/hotel_detail.html'
    model = Hotel
    context_object_name = 'hotel'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hotel = self.object
        now = timezone.now()
        
        # Get all bookings for this hotel
        bookings = Booking.objects.filter(room__hotel=hotel, is_paid=True)
        
        # REVENUE CALCULATIONS
        total_revenue = bookings.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        total_commission = bookings.aggregate(
            total=Sum('service_charge')
        )['total'] or Decimal('0.00')
        
        # Current month revenue
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_revenue = bookings.filter(
            created_at__gte=current_month_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # MONTHLY CHART DATA (last 12 months)
        monthly_labels = []
        monthly_revenue = []
        for i in range(11, -1, -1):
            month_date = now - timedelta(days=30*i)
            month_name = calendar.month_abbr[month_date.month]
            month_rev = bookings.filter(
                created_at__year=month_date.year,
                created_at__month=month_date.month
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            monthly_labels.append(month_name)
            monthly_revenue.append(float(month_rev))
        
        # ROOMS
        rooms = Room.objects.filter(hotel=hotel)
        
        # REVIEWS
        reviews = Review.objects.filter(hotel=hotel).order_by('-created_at')[:5]
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        
        context.update({
            'total_revenue': total_revenue,
            'total_commission': total_commission,
            'current_month_revenue': current_month_revenue,
            'total_bookings': bookings.count(),
            'rooms': rooms,
            'reviews': reviews,
            'avg_rating': round(avg_rating, 2),
            'monthly_labels': json.dumps(monthly_labels),
            'monthly_revenue': json.dumps(monthly_revenue),
        })
        return context


class HotelUpdateView(SuperuserRequiredMixin, DetailView):
    """
    Allows superuser to edit hotel details.
    Reuses the hotel edit form from the hotels app.
    """
    template_name = 'superadmin/hotel_edit.html'
    model = Hotel
    slug_field = 'slug'
    slug_url_kwarg = 'slug'


class HotelDeleteView(SuperuserRequiredMixin, DeleteView):
    """
    Allows superuser to delete a hotel.
    Shows confirmation page first.
    """
    template_name = 'superadmin/confirm_delete.html'
    model = Hotel
    success_url = reverse_lazy('superadmin_hotel_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, f"Hotel '{self.get_object().name}' has been deleted.")
        return super().delete(request, *args, **kwargs)


def toggle_hotel_approval(request, pk):
    """
    Toggles hotel approval status (approved/pending).
    Only accessible to superusers.
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    
    hotel = get_object_or_404(Hotel, pk=pk)
    hotel.is_approved = not hotel.is_approved
    hotel.save()
    
    status = "approved" if hotel.is_approved else "pending"
    messages.success(request, f"Hotel '{hotel.name}' is now {status}.")
    
    return redirect('superadmin_hotel_detail', slug=hotel.slug)


class CustomerListView(SuperuserRequiredMixin, ListView):
    """
    Lists all customers with pagination and search.
    """
    template_name = 'superadmin/customer_list.html'
    model = Customer
    context_object_name = 'customers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Customer.objects.order_by('-date_joined')
        
        # Search by name or email
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(full_name__icontains=search) | queryset.filter(email__icontains=search)
        
        return queryset


class CustomerDeleteView(SuperuserRequiredMixin, DeleteView):
    """
    Allows superuser to delete a customer.
    """
    template_name = 'superadmin/confirm_delete.html'
    model = Customer
    success_url = reverse_lazy('superadmin_customer_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, f"Customer '{self.get_object().full_name}' has been deleted.")
        return super().delete(request, *args, **kwargs)


class OwnerListView(SuperuserRequiredMixin, ListView):
    """
    Lists all hotel owners with pagination and search.
    """
    template_name = 'superadmin/owner_list.html'
    model = CustomUser
    context_object_name = 'owners'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = CustomUser.objects.filter(is_hotel_owner=True).order_by('-date_joined')
        
        # Search by name or email
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(full_name__icontains=search) | queryset.filter(email__icontains=search)
        
        return queryset


class OwnerDeleteView(SuperuserRequiredMixin, DeleteView):
    """
    Allows superuser to delete a hotel owner.
    """
    template_name = 'superadmin/confirm_delete.html'
    model = CustomUser
    success_url = reverse_lazy('superadmin_owner_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, f"Owner '{self.get_object().full_name}' has been deleted.")
        return super().delete(request, *args, **kwargs)