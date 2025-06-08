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
from django.core.mail import send_mail
from django.template.loader import render_to_string
import logging
from django.utils import timezone

# Setup logging
logger = logging.getLogger(__name__)

def book_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.check_in = form.cleaned_data['check_in']
            booking.check_out = form.cleaned_data['check_out']
            booking.duration = form.cleaned_data['duration']
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
            
            # Send email to hotel owner asynchronously
            try:
                subject = 'New Booking Notification'
                message = render_to_string('bookings/booking_notification.html', {'booking': booking})
                send_mail(subject, '', None, [booking.room.hotel.owner.email], html_message=message)
            except Exception as e:
                logger.error(f"Failed to send booking notification email for booking {booking.booking_reference}: {str(e)}")
                # Continue with booking process even if email fails
            
            return redirect('booking_confirmation', booking_reference=booking.booking_reference)
    else:
        form = BookingForm()
    return render(request, 'bookings/book_room.html', {'form': form, 'room': room})

def initiate_payment(request, booking_reference):
    booking = get_object_or_404(Booking, booking_reference=booking_reference)
    if booking.is_paid:
        return redirect('booking_confirmation', booking_reference=booking.booking_reference)
    url = 'https://api.paystack.co/transaction/initialize'
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'email': booking.email,
        'amount': int(booking.total_amount * 100),  # Include service charge
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
    if not request.user.is_superuser and not hasattr(request.user, 'hotel'):
        return HttpResponseForbidden("Only hotel owners and superusers can verify bookings.")
    
    if request.method == 'POST':
        reference = request.POST.get('reference', '').strip()
        if not reference:
            return render(request, 'bookings/verify.html', {
                'error': 'Please enter a booking reference.'
            })
        
        try:
            booking = Booking.objects.get(booking_reference=reference)
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
                'error': 'The booking reference format is invalid.'
            })
    
    return render(request, 'bookings/verify.html')

def cancel_booking(request, booking_reference):
    booking = get_object_or_404(Booking, booking_reference=booking_reference)
    if request.method == 'POST':
        if not booking.is_paid:
            booking.delete()
            return redirect('hotel_list')
        else:
            return render(request, 'bookings/cancellation_error.html', {'error': 'Cannot cancel a paid booking.'})
    return render(request, 'bookings/confirm_cancel.html', {'booking': booking})

def check_availability(request, room_id):
    check_in_str = request.GET.get('check_in')
    duration = request.GET.get('duration')
    room = get_object_or_404(Room, id=room_id)
    
    if check_in_str and duration:
        try:
            check_in = timezone.datetime.strptime(check_in_str, '%Y-%m-%dT%H:%M')
            duration = int(duration)
            check_out = check_in + timezone.timedelta(hours=duration)
            available = is_room_available(room, check_in, check_out)
            return JsonResponse({'available': available})
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid input'}, status=400)
    return JsonResponse({'error': 'Missing parameters'}, status=400)