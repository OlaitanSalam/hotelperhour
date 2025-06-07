# bookings/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import Booking
from .forms import BookingForm
from hotels.models import Room
import requests
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.core.exceptions import ValidationError

def book_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.room = room
            booking.name = form.cleaned_data['name']
            booking.phone_number = form.cleaned_data['phone_number']
            booking.email = form.cleaned_data['email']
            if request.user.is_authenticated:
                booking.user = request.user
            if not is_room_available(room, booking.check_in, booking.check_out):
                form.add_error(None, "This room is not available for the selected time slot.")
                return render(request, 'bookings/book_room.html', {'form': form, 'room': room})
            booking.save()
            return redirect('booking_confirmation', booking_reference=booking.booking_reference)
    else:
        form = BookingForm()
    return render(request, 'bookings/book_room.html', {'form': form, 'room': room})


def initiate_payment(request, booking_reference):
    booking = get_object_or_404(Booking, booking_reference=booking_reference)
    if booking.is_paid:
        return redirect('booking_confirmation', booking_id=booking.id)
    url = 'https://api.paystack.co/transaction/initialize'
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'email': booking.email,
        'amount': int(booking.total_price * 100),  # Naira to kobo
        'reference': str(booking.booking_reference),
        'callback_url': request.build_absolute_uri(reverse('payment_callback'))
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return redirect(response.json()['data']['authorization_url'])
    return render(request, 'bookings/payment_error.html')

@csrf_exempt
def payment_callback(request):
    if request.method == 'GET':
        reference = request.GET.get('reference')
        booking = get_object_or_404(Booking, booking_reference=reference)
        if verify_payment(reference):
            booking.is_paid = True
            booking.payment_reference = reference
            booking.save()
        return redirect('booking_confirmation', booking_reference=booking.booking_reference)

@csrf_exempt
def paystack_webhook(request):
    if request.method == 'POST':
        payload = json.loads(request.body)
        if payload['event'] == 'charge.success':
            reference = payload['data']['reference']
            booking = Booking.objects.get(booking_reference=reference)
            booking.is_paid = True
            booking.payment_reference = reference
            booking.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

def verify_payment(reference):
    url = f'https://api.paystack.co/transaction/verify/{reference}'
    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    response = requests.get(url, headers=headers)
    return response.status_code == 200 and response.json()['data']['status'] == 'success'


def booking_confirmation(request, booking_reference):
    booking = get_object_or_404(Booking, booking_reference=booking_reference)
    return render(request, 'bookings/confirmation.html', {'booking': booking})


def is_room_available(room, check_in, check_out):
    return not Booking.objects.filter(
        room=room,
        check_in__lt=check_out,
        check_out__gt=check_in
    ).exists()


@login_required
def verify_booking(request):
    # Restrict access to superusers and hotel owners
    if not request.user.is_superuser and not hasattr(request.user, 'hotel_set'):
        return HttpResponseForbidden("Only hotel owners and superusers can verify bookings.")
    
    if request.method == 'POST':
        reference = request.POST.get('reference', '').strip()  # Remove leading/trailing whitespace
        
        # Check for incomplete or empty input
        if not reference:
            return render(request, 'bookings/verify.html', {
                'error': 'Please enter a booking reference.'
            })
        
        try:
            booking = Booking.objects.get(booking_reference=reference)
            # Permission check for non-superusers (hotel owners)
            if not request.user.is_superuser:
                if booking.room.hotel.owner != request.user:
                    return render(request, 'bookings/verify.html', {
                        'error': 'You do not have permission to view this booking.'
                    })
            return render(request, 'bookings/verify.html', {'booking': booking})
        
        except Booking.DoesNotExist:
            return render(request, 'bookings/verify.html', {
                'error': 'No booking found with this reference.'
            })
        except ValidationError:
            return render(request, 'bookings/verify.html', {
                'error': 'The booking reference format is invalid. Please use a valid UUID (e.g., 123e4567-e89b-12d3-a456-426614174000).'
            })
    
    # Render the form for GET requests
    return render(request, 'bookings/verify.html')


def cancel_booking(request, booking_reference):
    booking = get_object_or_404(Booking, booking_reference=booking_reference)
    if request.method == 'POST':  
        if not booking.is_paid:
            booking.delete()
            return redirect('hotel_list')  
        else:
            # Optionally handle paid bookings (e.g., refund logic)
            return render(request, 'bookings/cancellation_error.html', {'error': 'Cannot cancel a paid booking.'})
    return render(request, 'bookings/confirm_cancel.html', {'booking': booking})

def check_availability(request, room_id):
       check_in = request.GET.get('check_in')
       check_out = request.GET.get('check_out')
       room = get_object_or_404(Room, id=room_id)
       if check_in and check_out:
           available = not Booking.objects.filter(
               room=room,
               check_in__lt=check_out,
               check_out__gt=check_in
           ).exists()
           return JsonResponse({'available': available})
       return JsonResponse({'error': 'Invalid dates'}, status=400)