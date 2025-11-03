from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.generic import DetailView
from geopy.distance import geodesic
from django.conf import settings
from .forms import HotelForm, RoomFormSet, ExtraServiceFormSet, ReviewForm, AppFeedbackForm, HotelImageFormSet, HotelPolicyFormSet
from .models import Hotel, Room, ExtraService, Review, AppFeedback, Amenity
from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from bookings.models import Booking
from .forms import DateRangeForm
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from urllib.parse import urlencode
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Review
from django.db.models import Avg, Count, Sum, F
from django.utils.timezone import now
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponseForbidden
from decimal import Decimal
import calendar, json
from datetime import timedelta
from .forms import DateRangeForm
from django.template.defaultfilters import register
from django.db.models import Min




def hotel_owner_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_hotel_owner:
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@hotel_owner_required
def hotel_dashboard(request):
    hotels = Hotel.objects.filter(owner=request.user)
    return render(request, 'hotels/hotel_dashboard.html', {'hotels': hotels})

@login_required
@hotel_owner_required
def hotel_create(request):
    if Hotel.objects.filter(owner=request.user).exists():
        messages.error(request, "You can only register one hotel per account.")
        return redirect('hotel_dashboard')
    if request.method == 'POST':
        form = HotelForm(request.POST, request.FILES)
        room_formset = RoomFormSet(request.POST, request.FILES, prefix='room')
        extra_formset = ExtraServiceFormSet(request.POST, prefix='extra')
        image_formset = HotelImageFormSet(request.POST, request.FILES, prefix='image')
        policy_formset = HotelPolicyFormSet(request.POST, prefix='policy')
        if form.is_valid() and room_formset.is_valid() and extra_formset.is_valid() and image_formset.is_valid() and policy_formset.is_valid():
            # Check if at least one room is provided
            if not any(form.is_valid() and not form.cleaned_data.get('DELETE', False) for form in room_formset.forms):
                messages.error(request, "At least one room is required to create a hotel.")
                return render(request, 'hotels/hotel_form.html', {
                    'form': form,
                    'room_formset': room_formset,
                    'extra_formset': extra_formset,
                    'image_formset': image_formset,
                    'policy_formset': policy_formset,
                    'amenities': Amenity.objects.order_by('name'),
                    'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
                })
            hotel = form.save(commit=False)
            hotel.owner = request.user
            hotel.save()
            form.save_m2m()
            room_formset.instance = hotel
            room_formset.save()
            extra_formset.instance = hotel
            extra_formset.save()
            image_formset.instance = hotel  
            image_formset.save()
            policy_formset.instance = hotel
            policy_formset.save()
            if not request.user.is_hotel_owner:
                request.user.is_hotel_owner = True
                request.user.save()
                messages.success(request, "Your hotel has been created successfully. Please allow up to 24 hours for review and approval.")

            return redirect('hotel_dashboard')
        else:
            # If the POST failed validation, provide a clearer message when
            # address is missing but coordinates were submitted by the map JS.
            if request.method == 'POST':
                lat = request.POST.get('latitude')
                lng = request.POST.get('longitude')
                if 'address' in form.errors and lat and lng:
                    form.add_error('address', 'Address is required. We detected coordinates but the address field is empty. Please confirm the address using the map search or "Use My Current Location" before submitting.')
    else:
        form = HotelForm()
        room_formset = RoomFormSet(prefix='room')
        extra_formset = ExtraServiceFormSet(prefix='extra')
        image_formset = HotelImageFormSet(prefix='image')
        policy_formset = HotelPolicyFormSet(prefix='policy')
    return render(request, 'hotels/hotel_form.html', {
        'form': form,
        'room_formset': room_formset,
        'extra_formset': extra_formset,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'image_formset': image_formset,
        'amenities': Amenity.objects.order_by('name'),
        'policy_formset': policy_formset,
        

    })

@login_required
@hotel_owner_required
def hotel_edit(request, slug):
    hotel = get_object_or_404(Hotel, slug=slug, owner=request.user)
    if request.method == 'POST':
        form = HotelForm(request.POST, request.FILES, instance=hotel)
        room_formset = RoomFormSet(request.POST, request.FILES, instance=hotel, prefix='room')
        extra_formset = ExtraServiceFormSet(request.POST, instance=hotel, prefix='extra')
        image_formset = HotelImageFormSet(request.POST, request.FILES, instance=hotel, prefix='image')
        policy_formset = HotelPolicyFormSet(request.POST, prefix='policy', instance=hotel)
        if form.is_valid() and room_formset.is_valid() and extra_formset.is_valid() and image_formset.is_valid() and policy_formset.is_valid():
            # Check if at least one room remains after edits
            if not any(form.is_valid() and not form.cleaned_data.get('DELETE', False) for form in room_formset.forms):
                messages.error(request, "At least one room is required to update the hotel.")
                return render(request, 'hotels/hotel_form.html', {
                    'form': form,
                    'room_formset': room_formset,
                    'extra_formset': extra_formset,
                    'image_formset': image_formset,
                    'policy_formset': policy_formset,
                    'amenities': Amenity.objects.order_by('name'),
                    'is_edit': True,
                    'hotel': hotel,
                    'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
                })
            form.save()
            room_formset.save()
            extra_formset.save()
            image_formset.save()
            policy_formset.save()
            messages.success(request, "Hotel updated successfully.")
            return redirect('hotel_dashboard')
    else:
        form = HotelForm(instance=hotel)
        room_formset = RoomFormSet(instance=hotel, prefix='room')
        extra_formset = ExtraServiceFormSet(instance=hotel, prefix='extra')
        image_formset = HotelImageFormSet(instance=hotel, prefix='image')
        policy_formset = HotelPolicyFormSet(prefix='policy', instance=hotel)
    return render(request, 'hotels/hotel_form.html', {
        'form': form,
        'room_formset': room_formset,
        'extra_formset': extra_formset,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'image_formset': image_formset,
        'is_edit': True,
        'hotel': hotel,
        'amenities': Amenity.objects.order_by('name'),
        'policy_formset': policy_formset,
    })

@login_required
@hotel_owner_required
def hotel_delete(request, slug):
    # Changed from pk to slug
    hotel = get_object_or_404(Hotel, slug=slug, owner=request.user)
    if request.method == 'POST':
        hotel.delete()
        return redirect('hotel_dashboard')
    return render(request, 'hotels/hotel_confirm_delete.html', {'hotel': hotel})


@register.filter
def rating_label(value):
    labels = {5: 'Excellent', 4: 'Very Good', 3: 'Average', 2: 'Fair', 1: 'Poor'}
    return labels.get(value, 'Unknown')


class HotelDetailView(DetailView):
    model = Hotel
    template_name = 'hotels/hotel_detail.html'
    context_object_name = 'hotel'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hotel = self.object
        # Filter only images with actual files
        context['hotel_images'] = hotel.images.exclude(Q(image__isnull=True) | Q(image='')).order_by('order')
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hotel = self.get_object()
        reviews = Review.objects.filter(hotel=hotel).order_by('-created_at')

        stats = reviews.aggregate(avg_rating=Avg('rating'), count=Count('id'))
        rating_breakdown = {}
        for rating in range(5, 0, -1):  # Start from 5 to 1
            count = reviews.filter(rating=rating).count()
            percent = (count / stats['count'] * 100) if stats['count'] > 0 else 0
            rating_breakdown[rating] = {'value': count, 'percent': percent}
        context['rating_breakdown'] = rating_breakdown
        context['reviews'] = reviews[:5]  # Initial 5 reviews
        context['all_reviews'] = reviews[5:]  # Remaining for "See More"
        context['review_form'] = ReviewForm()
        context['hotel'].average_rating = stats['avg_rating']
        context['hotel'].review_count = stats['count']
        context['rating_breakdown'] = rating_breakdown
        context['hotel_images'] = hotel.images.all().order_by('order')

        return context

    def post(self, request, *args, **kwargs):
        hotel = self.get_object()

        # ✅ Require authentication
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to leave a review.")
            return redirect('hotel_detail', slug=hotel.slug)

        # ✅ Prevent hotel owner from reviewing own hotel
        if hasattr(request.user, "is_hotel_owner") and request.user.is_hotel_owner:
            if hotel.owner == request.user:
                messages.error(request, "Hotel owners cannot review their own hotels.")
                return redirect('hotel_detail', slug=hotel.slug)

        form = ReviewForm(request.POST)
        if form.is_valid():
            # ✅ Limit reviews (1 per hotel per 24h)
            last_review = Review.objects.filter(hotel=hotel, email=request.user.email).order_by("-created_at").first()
            if last_review and (now() - last_review.created_at) < timedelta(hours=24):
                messages.error(request, "You can only leave one review per hotel per day.")
                return redirect('hotel_detail', slug=hotel.slug)

            review = form.save(commit=False)
            review.hotel = hotel
            review.email = request.user.email  # enforce auth email
            review.name = request.user.full_name if hasattr(request.user, "full_name") else request.user.email
            review.save()

            messages.success(request, "Thank you for your review!")
            return redirect('hotel_detail', slug=hotel.slug)

        messages.error(request, "Please correct the errors below.")
        return self.get(request, *args, **kwargs)




def hotel_list(request):
    query = request.GET.get('q')
    hotels = Hotel.objects.filter(is_approved=True).annotate(
        average_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )
    if query:
        hotels = hotels.filter(Q(city__icontains=query) | Q(suburb__icontains=query))

    paginator = Paginator(hotels.order_by('name'), 9)
    page = request.GET.get('page')
    try:
        hotels_page = paginator.page(page)
    except PageNotAnInteger:
        hotels_page = paginator.page(1)
    except EmptyPage:
        hotels_page = paginator.page(paginator.num_pages)

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = urlencode(query_params)

    return render(request, 'hotels/hotel_list.html', {
        'hotels': hotels_page,
        'query_string': query_string
    })

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from urllib.parse import urlencode

def nearby_hotels(request):
    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')
    radius = float(request.GET.get('radius', 10))  # default 10 km
    radius_options = [5, 10, 20, 50]

    nearby_hotels = []

    if user_lat and user_lng:
        user_location = (float(user_lat), float(user_lng))
        hotels = Hotel.objects.filter(is_approved=True)

        for hotel in hotels:
            if hotel.latitude and hotel.longitude:
                hotel_location = (hotel.latitude, hotel.longitude)
                distance = geodesic(user_location, hotel_location).km
                if distance <= radius:
                    nearby_hotels.append({'hotel': hotel, 'distance': distance})

        nearby_hotels.sort(key=lambda x: x['distance'])

    # --- Pagination ---
    paginator = Paginator(nearby_hotels, 10)  # 10 hotels per page
    page = request.GET.get('page')
    try:
        hotels_page = paginator.page(page)
    except PageNotAnInteger:
        hotels_page = paginator.page(1)
    except EmptyPage:
        hotels_page = paginator.page(paginator.num_pages)

    # Keep query params except "page" for pagination links
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = urlencode(query_params)

    return render(request, 'hotels/nearby_hotels.html', {
        'nearby_hotels': hotels_page,
        'selected_radius': radius,
        'radius_options': radius_options,
        'query_string': query_string,
    })



@login_required
@hotel_owner_required
def hotel_bookings(request, slug):
    # Changed from hotel_id to slug
    hotel = get_object_or_404(Hotel, slug=slug, owner=request.user)
    bookings = Booking.objects.filter(room__hotel=hotel).order_by('-check_in')
    paginator = Paginator(bookings, 10)  # 10 bookings per page
    page = request.GET.get('page')
    try:
        bookings_page = paginator.page(page)
    except PageNotAnInteger:
        bookings_page = paginator.page(1)
    except EmptyPage:
        bookings_page = paginator.page(paginator.num_pages)
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = urlencode(query_params)
    return render(request, 'hotels/hotel_bookings.html', {'hotel': hotel, 'bookings': bookings_page, 'query_string': query_string})

@login_required
@hotel_owner_required
def hotel_rooms(request, slug):
    # Changed from hotel_id to slug
    hotel = get_object_or_404(Hotel, slug=slug, owner=request.user)
    rooms = Room.objects.filter(hotel=hotel)
    paginator = Paginator(rooms, 10)  # 10 rooms per page
    page = request.GET.get('page')
    try:
        rooms_page = paginator.page(page)
    except PageNotAnInteger:
        rooms_page = paginator.page(1)
    except EmptyPage:
        rooms_page = paginator.page(paginator.num_pages)
    now = timezone.now()
    active_bookings = Booking.objects.filter(room__in=rooms_page, check_in__lte=now, check_out__gte=now).select_related('room')
    active_bookings_dict = {booking.room.id: booking for booking in active_bookings}
    room_data = [(room, active_bookings_dict.get(room.id)) for room in rooms_page]
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = urlencode(query_params)
    return render(request, 'hotels/hotel_rooms.html', {
        'hotel': hotel,
        'room_data': room_data,
        'rooms_page': rooms_page,
        'query_string': query_string
    })

@login_required
@hotel_owner_required
def toggle_room_availability(request, hotel_slug, room_id):
    # Changed from hotel_id to hotel_slug
    hotel = get_object_or_404(Hotel, slug=hotel_slug)
    room = get_object_or_404(Room, id=room_id, hotel=hotel)
    if room.hotel.owner != request.user:
        return HttpResponseForbidden("You do not have permission to modify this room.")
    if request.method == "POST":
        room.is_available = not room.is_available
        room.save()
        messages.success(request, f"Room {room.room_type} is now {'available' if room.is_available else 'unavailable'}.")
    # Updated redirect to use hotel_slug
    return redirect('hotel_rooms', slug=hotel_slug)



@login_required
@hotel_owner_required
def hotel_sales_report(request, slug):
    hotel = get_object_or_404(Hotel, slug=slug, owner=request.user)

    form = DateRangeForm(request.GET or None)

    # Default to last 30 days
    start_date = Booking.objects.filter(room__hotel=hotel).aggregate(first=Min('check_in'))['first'] or timezone.now().date()
    end_date = timezone.now().date()

    if form.is_valid():
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]

    # Paid bookings in range
    bookings = Booking.objects.filter(
        room__hotel=hotel,
        check_in__date__range=(start_date, end_date),
        is_paid=True,
    )

    # --- Aggregate sales by day ---
    sales_data_qs = (
        bookings.annotate(date=TruncDate("check_in"))
        .values("date")
        .annotate(
            booking_count=Count("id"),
            total_sales=Sum(F("total_amount") - F("service_charge")),
        )
        .order_by("-date")  # ✅ latest first
    )

    sales_data = []
    for row in sales_data_qs:
        total_sales = row["total_sales"] or Decimal("0.00")
        commission = total_sales * Decimal("0.10") # 10% commission
        payout = total_sales - commission
        sales_data.append({
            "date": row["date"],
            "booking_count": row["booking_count"],
            "total_sales": total_sales,
            "commission": commission,
            "payout": payout,
        })

    # --- Pagination ---
    paginator = Paginator(sales_data, 10)
    page = request.GET.get("page")
    try:
        sales_data_page = paginator.page(page)
    except PageNotAnInteger:
        sales_data_page = paginator.page(1)
    except EmptyPage:
        sales_data_page = paginator.page(paginator.num_pages)

    query_params = request.GET.copy()
    if "page" in query_params:
        del query_params["page"]
    query_string = urlencode(query_params)

    # --- Summary totals ---
    total_bookings = bookings.count()
    total_revenue = bookings.aggregate(
        total=Sum(F("total_amount") - F("service_charge"))
    )["total"] or Decimal("0.00")
    total_commission = total_revenue * Decimal("0.10")
    total_payout = total_revenue - total_commission
    avg_booking_value = (
        total_revenue / total_bookings if total_bookings else Decimal("0.00")
    )

    # --- KPIs: Today / This Month / Previous Month ---
    now = timezone.now()
    current_year, current_month = now.year, now.month

    today_revenue = bookings.filter(check_in__date=now.date()).aggregate(
        total=Sum(F("total_amount") - F("service_charge"))
    )["total"] or Decimal("0.00")

    current_month_revenue = bookings.filter(
        check_in__year=current_year, check_in__month=current_month
    ).aggregate(total=Sum(F("total_amount") - F("service_charge")))["total"] or Decimal("0.00")

    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    previous_month_revenue = bookings.filter(
        check_in__year=prev_year, check_in__month=prev_month
    ).aggregate(total=Sum(F("total_amount") - F("service_charge")))["total"] or Decimal("0.00")

    # --- Chart data ---
    # Monthly (Jan–Dec current year)
    monthly_chart_labels = [calendar.month_abbr[m] for m in range(1, 13)]
    monthly_revenue_data = []
    for month in range(1, 13):
        month_revenue = bookings.filter(
            check_in__year=current_year, check_in__month=month
        ).aggregate(total=Sum(F("total_amount") - F("service_charge")))["total"] or Decimal("0.00")
        monthly_revenue_data.append(float(month_revenue))

    # Daily (last 30 days)
    last_30_days = [end_date - timedelta(days=i) for i in range(29, -1, -1)]
    daily_chart_labels = [d.strftime("%b %d") for d in last_30_days]
    daily_revenue_data = []
    for d in last_30_days:
        revenue = bookings.filter(check_in__date=d).aggregate(
            total=Sum(F("total_amount") - F("service_charge"))
        )["total"] or Decimal("0.00")
        daily_revenue_data.append(float(revenue))

    # Weekly (last 12 weeks)
    weekly_chart_labels, weekly_revenue_data = [], []
    for i in range(11, -1, -1):
        week_start = end_date - timedelta(weeks=i, days=end_date.weekday())
        week_end = week_start + timedelta(days=6)
        week_label = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"
        revenue = bookings.filter(check_in__date__range=(week_start, week_end)).aggregate(
            total=Sum(F("total_amount") - F("service_charge"))
        )["total"] or Decimal("0.00")
        weekly_chart_labels.append(week_label)
        weekly_revenue_data.append(float(revenue))

    context = {
        "hotel": hotel,
        "form": form,
        "sales_data": sales_data_page,
        "query_string": query_string,
        "summary": {
            "total_revenue": total_revenue,
            "total_commission": total_commission,
            "total_payout": total_payout,
            "total_bookings": total_bookings,
            "average_booking_value": avg_booking_value,
            "today_revenue": today_revenue,
            "current_month_revenue": current_month_revenue,
            "current_month_commission": current_month_revenue * Decimal("0.10"),
            "current_month_payout": current_month_revenue * Decimal("0.90"),
            "previous_month_revenue": previous_month_revenue,
            "monthly_payout": total_payout,
        },
        # Charts
        "monthly_chart_data": json.dumps(monthly_chart_labels),
        "monthly_revenue_data": json.dumps(monthly_revenue_data),
        "daily_chart_data": json.dumps(daily_chart_labels),
        "daily_revenue_data": json.dumps(daily_revenue_data),
        "weekly_chart_data": json.dumps(weekly_chart_labels),
        "weekly_revenue_data": json.dumps(weekly_revenue_data),
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "hotels/hotel_sales_report.html", context)



@login_required
@hotel_owner_required
def cancel_booking(request, slug, booking_id):
    hotel = get_object_or_404(Hotel, slug=slug, owner=request.user)
    booking = get_object_or_404(Booking, id=booking_id, room__hotel=hotel)
    if booking.is_paid:
        messages.error(request, "Cannot cancel a paid booking.")
    else:
        booking.delete()
        messages.success(request, "Booking cancelled successfully.")
    return redirect('hotel_bookings', slug=slug)

@login_required
@hotel_owner_required
def confirm_cancel_booking(request, slug, booking_id):
    """Show cancellation confirmation page"""
    hotel = get_object_or_404(Hotel, slug=slug, owner=request.user)
    booking = get_object_or_404(Booking, id=booking_id, room__hotel=hotel)
    
    return render(request, 'hotels/cancel_booking2.html', {
        'hotel': hotel,
        'booking': booking
    })

def about(request):
    return render(request, 'about.html')



def contacts(request):
    return render(request, 'contacts.html')

def contact_success(request):
    return render(request, 'hotels/contact_success.html')

@require_POST
@csrf_exempt
def submit_feedback(request):
    try:
        name = request.POST.get('name')
        email = request.POST.get('email')
        review_text = request.POST.get('review_text')
        rating = request.POST.get('rating')

        AppFeedback.objects.create(
            name=name,
            email=email,
            review_text=review_text,
            rating=rating
        )

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
