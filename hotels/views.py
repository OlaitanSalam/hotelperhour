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
from django.db.models import Case, When, F, ExpressionWrapper, DecimalField, Sum, Count, Q, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce






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
        # Initialize room formset with parent_form BEFORE validation
        room_formset = RoomFormSet(request.POST, request.FILES, prefix='room', parent_form=form)
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
            lat = request.POST.get('latitude')
            lng = request.POST.get('longitude')
            if 'address' in form.errors and lat and lng:
                form.add_error('address', 'Address is required. We detected coordinates but the address field is empty. Please confirm the address using the map search or "Use My Current Location" before submitting.')
    else:
        form = HotelForm()
        room_formset = RoomFormSet(prefix='room', parent_form=form)
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
        room_formset = RoomFormSet(request.POST, request.FILES, instance=hotel, prefix='room', parent_form=form)
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
        room_formset = RoomFormSet(instance=hotel, prefix='room', parent_form=form)
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
def hotel_edit(request, slug):
    hotel = get_object_or_404(Hotel, slug=slug, owner=request.user)
    
    if request.method == 'POST':
        form = HotelForm(request.POST, request.FILES, instance=hotel)
        room_formset = RoomFormSet(request.POST, request.FILES, instance=hotel, prefix='room')
        extra_formset = ExtraServiceFormSet(request.POST, instance=hotel, prefix='extra')
        image_formset = HotelImageFormSet(request.POST, request.FILES, instance=hotel, prefix='image')
        policy_formset = HotelPolicyFormSet(request.POST, prefix='policy', instance=hotel)
        
        # Set parent form reference BEFORE validation
        room_formset.parent_form = form
        
        if form.is_valid():
            # Re-initialize room formset with the validated parent form
            room_formset = RoomFormSet(request.POST, request.FILES, instance=hotel, prefix='room', parent_form=form)
            
            if room_formset.is_valid() and extra_formset.is_valid() and image_formset.is_valid() and policy_formset.is_valid():
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
        room_formset = RoomFormSet(instance=hotel, prefix='room', parent_form=form)
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

        # ✅ Images (filtered correctly)
        hotel_images = hotel.images.exclude(
            Q(image__isnull=True) | Q(image='')
        ).order_by('order')

        # ✅ Reviews
        reviews = Review.objects.filter(hotel=hotel).order_by('-created_at')

        # ✅ Stats
        stats = reviews.aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )
        hotel.average_rating = stats['avg_rating'] or 0
        hotel.review_count = stats['count'] or 0

        # ✅ Rating breakdown
        rating_breakdown = {}
        total_reviews = stats['count'] or 0

        for rating in range(5, 0, -1):
            c = reviews.filter(rating=rating).count()
            pct = (c / total_reviews * 100) if total_reviews else 0
            rating_breakdown[rating] = {
                'value': c,
                'percent': pct
            }

        # ✅ Add price info to rooms
        for room in hotel.rooms.all():
            room.price_info = room.get_display_price_info()

        # ✅ Build final context (NO overwriting)
        context.update({
            'hotel_images': hotel_images,
            'reviews': reviews[:5],
            'all_reviews': reviews[5:],
            'rating_breakdown': rating_breakdown,
            'review_form': ReviewForm(),
        })

        return context

    def post(self, request, *args, **kwargs):
        hotel = self.get_object()

        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to leave a review.")
            return redirect('hotel_detail', slug=hotel.slug)

        if hasattr(request.user, "is_hotel_owner") and request.user.is_hotel_owner:
            if hotel.owner == request.user:
                messages.error(request, "Hotel owners cannot review their own hotels.")
                return redirect('hotel_detail', slug=hotel.slug)

        form = ReviewForm(request.POST)
        if form.is_valid():
            last_review = Review.objects.filter(
                hotel=hotel,
                email=request.user.email
            ).order_by('-created_at').first()

            if last_review and (now() - last_review.created_at) < timedelta(hours=24):
                messages.error(request, "You can only leave one review per hotel per day.")
                return redirect('hotel_detail', slug=hotel.slug)

            review = form.save(commit=False)
            review.hotel = hotel
            review.email = request.user.email
            review.name = getattr(request.user, "full_name", request.user.email)
            review.save()

            messages.success(request, "Thank you for your review!")
            return redirect('hotel_detail', slug=hotel.slug)

        messages.error(request, "Please correct the errors below.")
        return self.get(request, *args, **kwargs)




def hotel_list(request):
    query = request.GET.get('q', '')
    
    # Base queryset with annotations
    hotels = Hotel.objects.filter(is_approved=True).annotate(
        average_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )
    
    # Apply search filter
    if query:
        hotels = hotels.filter(
            Q(city__icontains=query) | Q(suburb__icontains=query)
        )

    # Pagination
    paginator = Paginator(hotels.order_by('name'), 9)
    page = request.GET.get('page')
    
    try:
        hotels_page = paginator.page(page)
    except PageNotAnInteger:
        hotels_page = paginator.page(1)
    except EmptyPage:
        hotels_page = paginator.page(paginator.num_pages)

    # Build query string
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = urlencode(query_params)
    
    for hotel in hotels_page:
        hotel.pricing_info = hotel.get_display_pricing_info()

    return render(request, 'hotels/hotel_list.html', {
        'hotels': hotels_page,  # Paginated queryset
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
    hotel = get_object_or_404(Hotel, slug=slug, owner=request.user)

    # ------------------------------------------------------------------
    # 1. All bookings for this hotel (paid or unpaid)
    # ------------------------------------------------------------------
    bookings_qs = Booking.objects.filter(
        room__hotel=hotel
    ).select_related('room').order_by('-check_in')

    # ------------------------------------------------------------------
    # 2. Annotate: full room cost + extras = hotel_revenue
    # ------------------------------------------------------------------
    # ✅ Just fetch bookings - hotel_revenue property handles it
    bookings = bookings_qs.select_related('room').prefetch_related('extras')

    # In your template, use: {{ booking.hotel_revenue }}
    # It will automatically use the frozen snapshot

    # ------------------------------------------------------------------
    # 3. Pagination
    # ------------------------------------------------------------------
    paginator = Paginator(bookings, 10)
    page = request.GET.get('page')
    try:
        bookings_page = paginator.page(page)
    except PageNotAnInteger:
        bookings_page = paginator.page(1)
    except EmptyPage:
        bookings_page = paginator.page(paginator.num_pages)

    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = urlencode(query_params)

    context = {
        'hotel': hotel,
        'bookings': bookings_page,
        'query_string': query_string,
    }
    return render(request, 'hotels/hotel_bookings.html', context)

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

    # ---- Default date range (last 30 days) ----
    default_end = timezone.now().date()
    # Get the earliest check-in date for this hotel
    first_checkin = Booking.objects.filter(
        room__hotel=hotel,
        is_paid=True
    ).aggregate(first=Min('check_in'))['first']

    default_start = first_checkin.date() if first_checkin else default_end

    start_date = default_start
    end_date = default_end

    if form.is_valid():
        start_date = form.cleaned_data.get("start_date") or default_start
        end_date = form.cleaned_data.get("end_date") or default_end

    # ---- Paid bookings in the selected range (check-in date) ----
    bookings_qs = Booking.objects.filter(
        room__hotel=hotel,
        check_in__date__range=(start_date, end_date),
        is_paid=True,
    ).select_related('room')

    # ------------------------------------------------------------------
    # 1. Base room cost (full price – ignore discount_applied)
    # ------------------------------------------------------------------
    def full_room_cost(booking):
        hrs = booking.total_hours
        room = booking.room
        if hrs == 12 and room.twelve_hour_price:
            return room.twelve_hour_price
        if hrs == 24 and room.twenty_four_hour_price:
            return room.twenty_four_hour_price
        # fallback to hourly
        return room.price_per_hour * Decimal(str(hrs))

    # ✅ Don't annotate - just fetch bookings
    bookings = bookings_qs.select_related('room').prefetch_related('extras')

    # Then manually sum using the property:
    total_hotel_rev = sum(booking.hotel_revenue for booking in bookings)

    # For daily aggregation:
    daily_data = {}
    for booking in bookings:
        day = booking.check_in.date()
        if day not in daily_data:
            daily_data[day] = {'count': 0, 'revenue': Decimal('0.00')}
        daily_data[day]['count'] += 1
        daily_data[day]['revenue'] += booking.hotel_revenue

    # Convert to list and sort
    sales_data = [
        {
            'date': day,
            'booking_count': data['count'],
            'total_sales': data['revenue'],
            'commission': data['revenue'] * Decimal('0.10'),
            'payout': data['revenue'] * Decimal('0.90'),
        }
        for day, data in sorted(daily_data.items(), reverse=True)
    ]

    # ------------------------------------------------------------------
    # 2. Daily aggregation (latest first)
    # ------------------------------------------------------------------
    daily_qs = (
        bookings.annotate(day=TruncDate('check_in'))
        .values('day')
        .annotate(
            booking_count=Count('id'),
            hotel_revenue_total=Sum('hotel_revenue_snapshot')
        )
        .order_by('-day')
    )

    sales_data = []
    for row in daily_qs:
        rev = row['hotel_revenue_total'] or Decimal('0.00')
        commission = rev * Decimal('0.10')
        payout = rev - commission
        sales_data.append({
            'date': row['day'],
            'booking_count': row['booking_count'],
            'total_sales': rev,
            'commission': commission,
            'payout': payout,
        })

    # ------------------------------------------------------------------
    # 3. Pagination
    # ------------------------------------------------------------------
    paginator = Paginator(sales_data, 10)
    page = request.GET.get('page')
    try:
        sales_page = paginator.page(page)
    except PageNotAnInteger:
        sales_page = paginator.page(1)
    except EmptyPage:
        sales_page = paginator.page(paginator.num_pages)

    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = urlencode(query_params)

    # ------------------------------------------------------------------
    # 4. Summary totals (full hotel revenue)
    # ------------------------------------------------------------------
    total_bookings = bookings.count()
    total_hotel_rev = bookings.aggregate(t=Sum('hotel_revenue_snapshot'))['t'] or Decimal('0.00')
    total_commission = total_hotel_rev * Decimal('0.10')
    total_payout = total_hotel_rev - total_commission
    avg_booking = total_hotel_rev / total_bookings if total_bookings else Decimal('0.00')

    # ------------------------------------------------------------------
    # 5. KPI blocks (today / this month / previous month)
    # ------------------------------------------------------------------
    now = timezone.now()
    today_rev = bookings.filter(check_in__date=now.date()).aggregate(t=Sum('hotel_revenue_snapshot'))['t'] or Decimal('0.00')
    cur_month_rev = bookings.filter(
        check_in__year=now.year, check_in__month=now.month
    ).aggregate(t=Sum('hotel_revenue_snapshot'))['t'] or Decimal('0.00')
    prev_month = now.month - 1 if now.month > 1 else 12
    prev_year = now.year if now.month > 1 else now.year - 1
    prev_month_rev = bookings.filter(
        check_in__year=prev_year, check_in__month=prev_month
    ).aggregate(t=Sum('hotel_revenue_snapshot'))['t'] or Decimal('0.00')

    # ------------------------------------------------------------------
    # 6. Chart data (monthly / daily / weekly) – all use *hotel_revenue*
    # ------------------------------------------------------------------
    import calendar
    from collections import defaultdict

    # ---- Monthly (current year) ----
    monthly_labels = [calendar.month_abbr[m] for m in range(1, 13)]
    monthly_data = []
    for m in range(1, 13):
        rev = bookings.filter(
            check_in__year=now.year, check_in__month=m
        ).aggregate(t=Sum('hotel_revenue_snapshot'))['t'] or Decimal('0.00')
        monthly_data.append(float(rev))

    # ---- Daily (last 30 days) ----
    last_30 = [default_end - timedelta(days=i) for i in range(29, -1, -1)]
    daily_labels = [d.strftime('%b %d') for d in last_30]
    daily_data = []
    for d in last_30:
        rev = bookings.filter(check_in__date=d).aggregate(t=Sum('hotel_revenue_snapshot'))['t'] or Decimal('0.00')
        daily_data.append(float(rev))

    # ---- Weekly (last 12 weeks) ----
    weekly_labels, weekly_data = [], []
    for i in range(11, -1, -1):
        week_start = default_end - timedelta(weeks=i, days=default_end.weekday())
        week_end = week_start + timedelta(days=6)
        label = f"{week_start:%b %d} - {week_end:%b %d}"
        rev = bookings.filter(
            check_in__date__range=(week_start, week_end)
        ).aggregate(t=Sum('hotel_revenue_snapshot'))['t'] or Decimal('0.00')
        weekly_labels.append(label)
        weekly_data.append(float(rev))

    # ------------------------------------------------------------------
    # 7. Context
    # ------------------------------------------------------------------
    context = {
        'hotel': hotel,
        'form': form,
        'sales_data': sales_page,
        'query_string': query_string,
        'summary': {
            'total_revenue': total_hotel_rev,
            'total_commission': total_commission,
            'total_payout': total_payout,
            'total_bookings': total_bookings,
            'average_booking_value': avg_booking,
            'today_revenue': today_rev,
            'current_month_revenue': cur_month_rev,
            'current_month_commission': cur_month_rev * Decimal('0.10'),
            'current_month_payout': cur_month_rev * Decimal('0.90'),
            'previous_month_revenue': prev_month_rev,
        },
        # chart JSON
        'monthly_chart_data': json.dumps(monthly_labels),
        'monthly_revenue_data': json.dumps(monthly_data),
        'daily_chart_data': json.dumps(daily_labels),
        'daily_revenue_data': json.dumps(daily_data),
        'weekly_chart_data': json.dumps(weekly_labels),
        'weekly_revenue_data': json.dumps(weekly_data),
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'hotels/hotel_sales_report.html', context)



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
    

    
@login_required
@hotel_owner_required
def hotel_payout_history(request, slug):
    """
    Show payout history for hotel owner - audit trail of all payouts
    """
    from superadmin.models import PayoutRecord
    
    hotel = get_object_or_404(Hotel, slug=slug, owner=request.user)
    
    # Get all payouts for this hotel
    payouts = PayoutRecord.objects.filter(
        hotel=hotel
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(payouts, 10)
    page = request.GET.get('page')
    try:
        payouts_page = paginator.page(page)
    except PageNotAnInteger:
        payouts_page = paginator.page(1)
    except EmptyPage:
        payouts_page = paginator.page(paginator.num_pages)
    
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = urlencode(query_params)
    
    # ✅ UPDATED: Calculate revenue states using hotel methods
    pending_revenue = hotel.get_pending_revenue()  # 0-3 days old
    payable_revenue = hotel.get_payable_revenue()  # 4+ days old
    
    # Summary stats for completed/processing payouts
    completed_payouts = payouts.filter(status='completed')
    total_received = sum(p.net_payout for p in completed_payouts)
    
    # Active payouts (pending/approved/processing)
    active_payouts = payouts.filter(status__in=['pending', 'approved', 'processing'])
    total_active = sum(p.net_payout for p in active_payouts)
    
    context = {
        'hotel': hotel,
        'payouts': payouts_page,
        'query_string': query_string,
        'total_received': total_received,
        'total_active': total_active,  # Changed from total_pending
        'pending_revenue': pending_revenue,
        'payable_revenue': payable_revenue,
    }
    return render(request, 'hotels/payout_history.html', context)

@login_required
@hotel_owner_required
def hotel_payout_detail(request, slug, payout_id):
    """
    Show detailed view of a specific payout with all related bookings
    """
    from superadmin.models import PayoutRecord
    
    hotel = get_object_or_404(Hotel, slug=slug, owner=request.user)
    payout = get_object_or_404(PayoutRecord, id=payout_id, hotel=hotel)
    
    # Get related bookings
    bookings = payout.get_related_bookings()
    
    context = {
        'hotel': hotel,
        'payout': payout,
        'bookings': bookings,
    }
    return render(request, 'hotels/payout_detail.html', context)