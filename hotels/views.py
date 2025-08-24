from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.generic import DetailView
from geopy.distance import geodesic
from django.conf import settings
from .forms import HotelForm, RoomFormSet, ExtraServiceFormSet
from .models import Hotel, Room, ExtraService, Review
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
        if form.is_valid() and room_formset.is_valid() and extra_formset.is_valid():
            hotel = form.save(commit=False)
            hotel.owner = request.user
            hotel.save()
            room_formset.instance = hotel
            room_formset.save()
            extra_formset.instance = hotel
            extra_formset.save()
            if not request.user.is_hotel_owner:
                request.user.is_hotel_owner = True
                request.user.save()
            return redirect('hotel_dashboard')
    else:
        form = HotelForm()
        room_formset = RoomFormSet(prefix='room')
        extra_formset = ExtraServiceFormSet(prefix='extra')
    return render(request, 'hotels/hotel_form.html', {
        'form': form,
        'room_formset': room_formset,
        'extra_formset': extra_formset,
        'mapbox_access_token': settings.MAPBOX_ACCESS_TOKEN
    })

@login_required
@hotel_owner_required
def hotel_edit(request, slug):
    hotel = get_object_or_404(Hotel, slug=slug, owner=request.user)
    if request.method == 'POST':
        form = HotelForm(request.POST, request.FILES, instance=hotel)
        room_formset = RoomFormSet(request.POST, request.FILES, instance=hotel, prefix='room')
        extra_formset = ExtraServiceFormSet(request.POST, instance=hotel, prefix='extra')
        if form.is_valid() and room_formset.is_valid() and extra_formset.is_valid():
            form.save()
            room_formset.save()
            extra_formset.save()
            return redirect('hotel_dashboard')
    else:
        form = HotelForm(instance=hotel)
        room_formset = RoomFormSet(instance=hotel, prefix='room')
        extra_formset = ExtraServiceFormSet(instance=hotel, prefix='extra')
    return render(request, 'hotels/hotel_form.html', {
        'form': form,
        'room_formset': room_formset,
        'extra_formset': extra_formset,
        'mapbox_access_token': settings.MAPBOX_ACCESS_TOKEN,
        'is_edit': True,
        'hotel': hotel
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

class HotelDetailView(DetailView):
    model = Hotel
    template_name = 'hotels/hotel_detail.html'
    context_object_name = 'hotel'
    # Added slug_field and slug_url_kwarg to use slug instead of pk
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

def hotel_list(request):
    query = request.GET.get('q')
    hotels = Hotel.objects.filter(is_approved=True)
    if query:
        hotels = hotels.filter(Q(city__icontains=query))
    paginator = Paginator(hotels, 9)  # 9 hotels per page
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
    return render(request, 'hotels/hotel_list.html', {'hotels': hotels_page, 'query_string': query_string})

def nearby_hotels(request):
    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')
    radius = 10  # km
    if user_lat and user_lng:
        user_location = (float(user_lat), float(user_lng))
        hotels = Hotel.objects.filter(is_approved=True)
        nearby_hotels = []
        for hotel in hotels:
            if hotel.latitude and hotel.longitude:
                hotel_location = (hotel.latitude, hotel.longitude)
                distance = geodesic(user_location, hotel_location).km
                if distance <= radius:
                    nearby_hotels.append({'hotel': hotel, 'distance': distance})
        nearby_hotels.sort(key=lambda x: x['distance'])
        return render(request, 'hotels/nearby_hotels.html', {'nearby_hotels': nearby_hotels})
    return render(request, 'hotels/nearby_hotels.html', {'nearby_hotels': []})

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
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
    else:
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=30)
    
    sales_data = Booking.objects.filter(
        room__hotel=hotel, 
        check_in__date__range=(start_date, end_date),
        is_paid=True  # Only paid bookings contribute to sales
    ).annotate(date=TruncDate('check_in')).values('date').annotate(
        total_sales=Sum('total_amount') - Sum('service_charge'),
        booking_count=Count('id')
    ).order_by('date')
    
    # Calculate commission and payout
    for data in sales_data:
        data['commission'] = data['total_sales'] * Decimal('0.05')  # 5% commission
        data['payout'] = data['total_sales'] - data['commission']
    
    paginator = Paginator(sales_data, 10)  # 10 days per page
    page = request.GET.get('page')
    try:
        sales_data_page = paginator.page(page)
    except PageNotAnInteger:
        sales_data_page = paginator.page(1)
    except EmptyPage:
        sales_data_page = paginator.page(paginator.num_pages)
    
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = urlencode(query_params)
    
    return render(request, 'hotels/hotel_sales_report.html', {
        'hotel': hotel,
        'form': form,
        'sales_data': sales_data_page,
        'query_string': query_string
    })

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
    if request.method == 'POST':
        Review.objects.create(
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            rating=request.POST.get('rating'),
            review_text=request.POST.get('review_text')
        )
        return redirect('contact_success')
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
        
        # Create and save the review
        review = Review(
            name=name,
            email=email,
            review_text=review_text,
            rating=rating
        )
        review.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})