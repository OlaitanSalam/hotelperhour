# superadmin/views.py
from django.views.generic import ListView, DetailView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Count, Avg
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.http import urlencode
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
from django.db.models import F, ExpressionWrapper, DecimalField, Q
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


# superadmin/views.py
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

        if form.is_valid():
            start_date = form.cleaned_data.get('start_date') or (now - timedelta(days=365))
            end_date = form.cleaned_data.get('end_date') or now
        else:
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now

        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # ====== BASE BOOKINGS ======
        all_bookings = Booking.objects.filter(is_paid=True).annotate(
            hotel_revenue=ExpressionWrapper(F('total_amount') - F('service_charge'), output_field=DecimalField())
        )

        # ====== ALL-TIME KPI ======
        all_service_charge = all_bookings.aggregate(total=Sum('service_charge'))['total'] or Decimal('0.00')
        all_hotel_revenue = all_bookings.aggregate(total=Sum('hotel_revenue'))['total'] or Decimal('0.00')
        all_hotel_commission = all_hotel_revenue * Decimal('0.10')
        all_platform_gain = all_service_charge + all_hotel_commission

        # ====== MONTHLY KPI ======
        monthly_bookings = all_bookings.filter(created_at__gte=current_month_start)
        monthly_service_charge = monthly_bookings.aggregate(total=Sum('service_charge'))['total'] or Decimal('0.00')
        monthly_hotel_revenue = monthly_bookings.aggregate(total=Sum('hotel_revenue'))['total'] or Decimal('0.00')
        monthly_hotel_commission = monthly_hotel_revenue * Decimal('0.10')
        monthly_platform_gain = monthly_service_charge + monthly_hotel_commission

        # ====== COUNTS ======
        total_hotels = Hotel.objects.count()
        total_customers = Customer.objects.count()
        total_owners = CustomUser.objects.filter(is_hotel_owner=True).count()
        total_users = total_customers + total_owners

        # ====== REVENUE GROWTH ======
        prev_month_start = current_month_start - relativedelta(months=1)
        prev_month_end = current_month_start - timedelta(seconds=1)
        prev_bookings = all_bookings.filter(created_at__range=(prev_month_start, prev_month_end))
        prev_service_charge = prev_bookings.aggregate(total=Sum('service_charge'))['total'] or Decimal('0.00')
        revenue_growth = ((monthly_service_charge - prev_service_charge) / prev_service_charge * 100) if prev_service_charge > 0 else (100 if monthly_service_charge > 0 else 0)

        # ====== CHART DATA (Platform Gain per month) ======
        view_type = self.request.GET.get('view', 'monthly')
        labels, data = [], []

        if view_type == 'daily':
            chart_data = all_bookings.filter(created_at__gte=now - timedelta(days=30)).annotate(period=TruncDay('created_at')).values('period').annotate(
                service=Sum('service_charge'),
                revenue=Sum(F('total_amount') - F('service_charge'))
            ).order_by('period')
            for row in chart_data:
                labels.append(row['period'].strftime('%b %d'))
                commission = (row['revenue'] or 0) * Decimal('0.10')
                total_gain = (row['service'] or 0) + commission
                data.append(float(total_gain))
        elif view_type == 'weekly':
            for i in range(11, -1, -1):
                week_end = now - timedelta(days=now.weekday() + 1 + 7*i)
                week_start = week_end - timedelta(days=6)
                agg = all_bookings.filter(created_at__range=(week_start, week_end)).aggregate(
                    service=Sum('service_charge'),
                    revenue=Sum(F('total_amount') - F('service_charge'))
                )
                commission = (agg['revenue'] or 0) * Decimal('0.10')
                total_gain = (agg['service'] or 0) + commission
                labels.append(f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}")
                data.append(float(total_gain))
        else:
            current_month = now.replace(day=1)
            for i in range(11, -1, -1):
                month = current_month - relativedelta(months=i)
                agg = all_bookings.filter(created_at__year=month.year, created_at__month=month.month).aggregate(
                    service=Sum('service_charge'),
                    revenue=Sum(F('total_amount') - F('service_charge'))
                )
                commission = (agg['revenue'] or 0) * Decimal('0.10')
                total_gain = (agg['service'] or 0) + commission
                labels.append(month.strftime('%b %Y'))
                data.append(float(total_gain))

        # ====== CONTEXT ======
        context.update({
            'form': form,
            'total_hotels': total_hotels,
            'total_users': total_users,
            'total_customers': total_customers,
            'revenue_growth': round(revenue_growth, 2),

            # --- ALL-TIME KPI ---
            'all_hotel_revenue': all_hotel_revenue,
            'all_service_charge': all_service_charge,
            'all_hotel_commission': all_hotel_commission,
            'all_platform_gain': all_platform_gain,

            # --- MONTHLY KPI ---
            'monthly_hotel_revenue': monthly_hotel_revenue,
            'monthly_service_charge': monthly_service_charge,
            'monthly_hotel_commission': monthly_hotel_commission,
            'monthly_platform_gain': monthly_platform_gain,

            # --- CHART ---
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
    template_name = 'superadmin/hotel_detail.html'
    model = Hotel
    context_object_name = 'hotel'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hotel = self.object
        now = timezone.now()

        # All paid bookings for this hotel
        bookings = Booking.objects.filter(room__hotel=hotel, is_paid=True).annotate(
            hotel_revenue=ExpressionWrapper(F('total_amount') - F('service_charge'), output_field=DecimalField())
        )

        # ===== KPI CALCULATIONS =====
        total_revenue = bookings.aggregate(total=Sum('hotel_revenue'))['total'] or Decimal('0.00')
        total_commission = total_revenue * Decimal('0.10')
        total_bookings = bookings.count()

        # Current month stats (using check_in date)
        current_year, current_month = now.year, now.month
        monthly_bookings = bookings.filter(check_in__year=current_year, check_in__month=current_month)
        current_month_revenue = monthly_bookings.aggregate(total=Sum('hotel_revenue'))['total'] or Decimal('0.00')
        current_month_commission = current_month_revenue * Decimal('0.10')
        current_month_payout = current_month_revenue * Decimal('0.90')

        # Weekly hotel revenue (last 7 days using check_in date)
        week_start = now.date() - timedelta(days=6)
        week_end = now.date()
        weekly_bookings = bookings.filter(check_in__date__range=(week_start, week_end))
        weekly_revenue = weekly_bookings.aggregate(total=Sum('hotel_revenue'))['total'] or Decimal('0.00')
        weekly_payout = weekly_revenue * Decimal('0.90')
        weekly_commission = weekly_revenue * Decimal('0.10')

        # ===== CHART DATA =====
        # Monthly (using check_in date)
        monthly_labels = [calendar.month_abbr[m] for m in range(1, 13)]
        monthly_revenue_data = []
        for month in range(1, 13):
            rev = bookings.filter(check_in__year=now.year, check_in__month=month).aggregate(total=Sum('hotel_revenue'))['total'] or Decimal('0.00')
            monthly_revenue_data.append(float(rev))

        # Weekly (last 12 weeks using check_in date)
        weekly_labels, weekly_revenue_data = [], []
        for i in range(11, -1, -1):
            week_start = now.date() - timedelta(weeks=i, days=now.date().weekday())
            week_end = week_start + timedelta(days=6)
            label = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"
            revenue = bookings.filter(check_in__date__range=(week_start, week_end)).aggregate(total=Sum('hotel_revenue'))['total'] or Decimal('0.00')
            weekly_labels.append(label)
            weekly_revenue_data.append(float(revenue))

        # Daily (last 30 days using check_in date)
        last_30_days = [now.date() - timedelta(days=i) for i in range(29, -1, -1)]
        daily_labels = [d.strftime("%b %d") for d in last_30_days]
        daily_revenue_data = []
        for d in last_30_days:
            rev = bookings.filter(check_in__date=d).aggregate(total=Sum('hotel_revenue'))['total'] or Decimal('0.00')
            daily_revenue_data.append(float(rev))

        # ===== PAGINATION for Reviews =====
        reviews_qs = Review.objects.filter(hotel=hotel).order_by('-created_at')
        paginator = Paginator(reviews_qs, 5)
        page = self.request.GET.get("page")
        try:
            reviews = paginator.page(page)
        except PageNotAnInteger:
            reviews = paginator.page(1)
        except EmptyPage:
            reviews = paginator.page(paginator.num_pages)

        query_params = self.request.GET.copy()
        if "page" in query_params:
            del query_params["page"]
        query_string = urlencode(query_params)

        avg_rating = reviews_qs.aggregate(avg=Avg('rating'))['avg'] or 0
        rooms = Room.objects.filter(hotel=hotel)

        context.update({
            # KPIs
            'total_revenue': total_revenue,
            'total_commission': total_commission,
            'total_bookings': total_bookings,
            'current_month_revenue': current_month_revenue,
            'current_month_commission': current_month_commission,
            'current_month_payout': current_month_payout,
            'weekly_revenue': weekly_revenue,
            'weekly_commission': weekly_commission,
            'weekly_payout': weekly_payout,

            # Chart data
            'daily_labels': json.dumps(daily_labels),
            'daily_revenue_data': json.dumps(daily_revenue_data),
            'weekly_labels': json.dumps(weekly_labels),
            'weekly_revenue_data': json.dumps(weekly_revenue_data),
            'monthly_labels': json.dumps(monthly_labels),
            'monthly_revenue_data': json.dumps(monthly_revenue_data),

            # Data
            'rooms': rooms,
            'reviews': reviews,
            'avg_rating': round(avg_rating, 2),
            'query_string': query_string,
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
    Lists all hotel owners and superadmins with pagination and search.
    """
    template_name = 'superadmin/owner_list.html'
    model = CustomUser
    context_object_name = 'owners'
    paginate_by = 20

    def get_queryset(self):
        queryset = CustomUser.objects.filter(
            Q(is_hotel_owner=True) | Q(is_superuser=True)
        ).order_by('-date_joined')

        # Search by full name, email, or phone
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone_number__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        if "page" in query_params:
            del query_params["page"]
        query_string = query_params.urlencode()
        context["query_string"] = query_string
        return context



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