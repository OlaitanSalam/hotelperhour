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
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType
from customers.models import Customer, LoyaltyRule

# Setup logging
logger = logging.getLogger(__name__)

def send_sms_notification(phone_number, message):
    """Send SMS via Yournotify API."""
    if not phone_number.startswith('+'):
        phone_number = f'+234{phone_number.lstrip("0")}'  # Normalize Nigerian numbers
    url = 'https://api.yournotify.com/sms'
    headers = {
        'Authorization': f'Bearer {settings.YOURNOTIFY_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'sender': settings.YOURNOTIFY_SENDER_ID,
        'recipient': phone_number,
        'message': message[:160],  # SMS limit
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        logger.info(f"SMS sent to {phone_number}: {message}")
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")

def book_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    is_customer = request.user.is_authenticated and isinstance(request.user, Customer)
    
    if request.method == 'POST':
        form = BookingForm(request.POST, room=room, user=request.user)
        if form.is_valid():
            check_in = form.cleaned_data['check_in']
            check_out = form.cleaned_data['check_out']
            duration = form.cleaned_data['duration']
            extras = form.cleaned_data['extras']

            # Calculate base costs
            total_hours = duration
            room_cost = room.price_per_hour * Decimal(str(total_hours))
            service_charge = room_cost * Decimal('0.10')
            extras_cost = sum(extra.price for extra in extras)

            # Apply discount based on loyalty points
            discount_amount = Decimal('0.00')
            points_used = 0
            if is_customer and form.cleaned_data.get('use_points'):
                discount_percentage = form.cleaned_data.get('discount', 0)
                points_used = form.cleaned_data.get('points_to_use', 0)
                if discount_percentage > 0 and points_used > 0:
                    discount_amount = room_cost * (Decimal(discount_percentage) / Decimal('100'))
                    request.user.loyalty_points -= points_used
                    request.user.save()

            # Calculate final prices
            total_price_with_discount = room_cost - discount_amount
            total_amount = total_price_with_discount + service_charge + extras_cost

            # Create booking instance
            booking = form.save(commit=False)
            booking.room = room
            booking.check_in = check_in
            booking.check_out = check_out
            booking.total_hours = total_hours
            booking.total_price = total_price_with_discount
            booking.service_charge = service_charge
            booking.discount_applied = discount_amount
            booking.points_used = points_used
            booking.total_amount = total_amount
            booking.name = form.cleaned_data['name']
            booking.phone_number = form.cleaned_data['phone_number']
            booking.email = form.cleaned_data['email']

            # Associate user if authenticated
            if request.user.is_authenticated:
                booking.content_type = ContentType.objects.get_for_model(request.user)
                booking.object_id = request.user.pk

            if not is_room_available(room, booking.check_in, booking.check_out):
                form.add_error(None, "This room is not available for the selected time slot.")
                return render(request, 'bookings/book_room.html', {'form': form, 'room': room, 'is_customer': is_customer})

            booking.save()
            form.save_m2m()

            # Send notifications (email + SMS)
            try:
                # Email to hotel owner
                subject = 'New Booking Notification'
                message = render_to_string('bookings/booking_notification.html', {'booking': booking})
                send_mail(subject, '', None, [booking.room.hotel.owner.email], html_message=message)
                
                # SMS to hotel owner
                owner_sms = f"New booking #{booking.booking_reference} for {booking.room.room_type} at {booking.room.hotel.name} on {booking.check_in}."
                send_sms_notification(booking.room.hotel.owner.phone_number, owner_sms)
                
                # SMS to customer
                customer_sms = f"Your booking #{booking.booking_reference} is confirmed for {booking.check_in}. Total: ₦{booking.total_amount}."
                send_sms_notification(booking.phone_number, customer_sms)
            except Exception as e:
                logger.error(f"Failed to send notifications for booking {booking.booking_reference}: {str(e)}")

            return redirect('booking_confirmation', booking_reference=booking.booking_reference)
    else:
        form = BookingForm(room=room, user=request.user)
    return render(request, 'bookings/book_room.html', {'form': form, 'room': room, 'is_customer': is_customer})

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
        'amount': int(booking.total_amount * 100),
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
            # Send confirmation notifications
            try:
                # Email to customer
                subject = 'Payment Confirmation'
                message = render_to_string('bookings/payment_confirmation.html', {'booking': booking})
                send_mail(subject, '', None, [booking.email], html_message=message)
                
                # SMS to customer
                sms_message = f"Payment confirmed for booking #{booking.booking_reference}. Check-in: {booking.check_in}. Thank you!"
                send_sms_notification(booking.phone_number, sms_message)
            except Exception as e:
                logger.error(f"Failed to send payment confirmation for booking {booking.booking_reference}: {str(e)}")
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
    extras_cost = sum(extra.price for extra in booking.extras.all())
    original_room_cost = booking.room.price_per_hour * Decimal(str(booking.total_hours))
    discount_percentage = (booking.discount_applied / original_room_cost * 100) if original_room_cost > 0 else Decimal('0')
    context = {
        'booking': booking,
        'extras_cost': extras_cost,
        'original_room_cost': original_room_cost,
        'discount_percentage': discount_percentage,
    }
    return render(request, 'bookings/confirmation.html', context)

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
            # Send cancellation notifications
            try:
                # Email to customer
                subject = 'Booking Cancellation'
                message = render_to_string('bookings/cancellation_notification.html', {'booking': booking})
                send_mail(subject, '', None, [booking.email], html_message=message)
                
                # SMS to customer
                sms_message = f"Your booking #{booking.booking_reference} has been cancelled."
                send_sms_notification(booking.phone_number, sms_message)
            except Exception as e:
                logger.error(f"Failed to send cancellation notifications for booking {booking.booking_reference}: {str(e)}")
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

def get_loyalty_discount(request):
    if not request.user.is_authenticated or not isinstance(request.user, Customer):
        return JsonResponse({'discount': 0, 'min_points': 0})
    
    rule = LoyaltyRule.objects.filter(active=True).first()
    if not rule:
        return JsonResponse({'discount': 0, 'min_points': 0})
    
    user_points = request.user.loyalty_points
    if user_points < rule.min_points_to_use:
        return JsonResponse({'discount': 0, 'min_points': rule.min_points_to_use})
    
    possible_discount = (user_points / rule.points_per_percent)
    discount_percentage = min(possible_discount, float(rule.max_discount_percentage))
    return JsonResponse({'discount': discount_percentage, 'min_points': rule.min_points_to_use})