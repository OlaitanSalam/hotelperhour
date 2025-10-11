from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import Booking, ExtraService
from .forms import BookingForm
from hotels.models import Room, Hotel
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
from users.models import CustomUser

# Setup logging
logger = logging.getLogger(__name__)



def book_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    is_customer = request.user.is_authenticated and isinstance(request.user, Customer)
    
    if request.method == 'POST':
        form = BookingForm(request.POST, room=room, user=request.user)
        if form.is_valid():
            # Calculate totals
            check_in = form.cleaned_data['check_in']
            check_out = form.cleaned_data['check_out']
            duration = form.cleaned_data['duration']
            extras = form.cleaned_data['extras']
            total_hours = duration
            # Use special pricing for 12/24 hours if set, else standard
            if total_hours in [12, 24] and getattr(room, f"{'twelve' if total_hours == 12 else 'twenty_four'}_hour_price", None):
                room_cost = room.twelve_hour_price if total_hours == 12 else room.twenty_four_hour_price
            else:
                room_cost = room.price_per_hour * Decimal(str(total_hours))
            service_charge = room_cost * Decimal('0.10')
            extras_cost = sum(extra.price for extra in extras)
            discount_amount = Decimal('0.00')
            points_used = 0
            if is_customer and form.cleaned_data.get('use_points'):
                discount_percentage = form.cleaned_data.get('discount', 0)
                points_used = form.cleaned_data.get('points_to_use', 0)
                if discount_percentage > 0 and points_used > 0:
                    discount_amount = room_cost * (Decimal(discount_percentage) / Decimal('100'))
            total_price_with_discount = room_cost - discount_amount
            total_amount = total_price_with_discount + service_charge + extras_cost
            

            # Determine user model for content type
            user_content_type_id = None
            if request.user.is_authenticated:
                # Force resolution of SimpleLazyObject
                _ = request.user.pk  # Access pk to ensure user is resolved
                # Explicitly determine model based on user properties
                if hasattr(request.user, 'is_hotel_owner') and request.user.is_hotel_owner:
                    user_model = CustomUser
                else:
                    user_model = Customer
                user_content_type_id = ContentType.objects.get_for_model(user_model).id

            # Store data in session
            booking_data = {
                'room_id': room.id,
                'check_in': check_in.isoformat(),
                'check_out': check_out.isoformat(),
                'total_hours': total_hours,
                'name': form.cleaned_data['name'],
                'phone_number': form.cleaned_data['phone_number'],
                'email': form.cleaned_data['email'],
                'extras_ids': [extra.id for extra in extras],
                'discount_amount': float(discount_amount),
                'points_used': points_used,
                'service_charge': float(service_charge),
                'total_amount': float(total_amount),
                'user_content_type_id': user_content_type_id,
                'user_object_id': request.user.id if request.user.is_authenticated else None,
            }
            request.session['pending_booking_data'] = booking_data
            # Generate reference early
            reference = Booking.generate_booking_reference()
            request.session['pending_booking_reference'] = reference

            return redirect('initiate_payment', booking_reference=reference)
    else:
        form = BookingForm(room=room, user=request.user)
    return render(request, 'bookings/book_room.html', {'form': form, 'room': room, 'is_customer': is_customer})

def initiate_payment(request, booking_reference):
    booking_data = request.session.get('pending_booking_data')
    reference = request.session.get('pending_booking_reference')
    if not booking_data or not reference:
        return redirect('hotel_list')  # Or error page

    url = 'https://api.paystack.co/transaction/initialize'
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'email': booking_data['email'],
        'amount': int(Decimal(str(booking_data['total_amount'])) * 100),
        'reference': reference,
        'callback_url': request.build_absolute_uri(reverse('payment_callback'))
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return redirect(response.json()['data']['authorization_url'])
    else:
        # Handle error
        del request.session['pending_booking_data']
        del request.session['pending_booking_reference']
        return render(request, 'bookings/payment_error.html', {'error': 'Failed to initiate payment. Please try again.'})

def payment_callback(request):
    reference = request.GET.get('reference')
    if not reference:
        return render(request, 'bookings/payment_error.html', {'error': 'No reference provided.'})

    # Verify payment with Paystack
    if not verify_payment(reference):
        return render(request, 'bookings/payment_error.html', {'error': 'Payment verification failed.'})

    booking_data = request.session.get('pending_booking_data')
    pending_reference = request.session.get('pending_booking_reference')
    if not booking_data or reference != pending_reference:
        return render(request, 'bookings/payment_error.html', {'error': 'Invalid session data.'})

    required_keys = [
        'room_id', 'check_in', 'check_out', 'total_hours', 'name', 'phone_number',
        'email', 'service_charge', 'total_amount', 'discount_amount', 'points_used', 'extras_ids'
    ]
    if not all(key in booking_data for key in required_keys):
        logger.error(f"Missing keys in booking_data: {booking_data}")
        return render(request, 'bookings/payment_error.html', {'error': 'Invalid booking data.'})

    # Prepare booking
    room = Room.objects.get(id=booking_data['room_id'])
    check_in = timezone.datetime.fromisoformat(booking_data['check_in'])
    check_out = timezone.datetime.fromisoformat(booking_data['check_out'])
    if not timezone.is_aware(check_in):
        check_in = timezone.make_aware(check_in)
    if not timezone.is_aware(check_out):
        check_out = timezone.make_aware(check_out)

    if not is_room_available(room, check_in, check_out):
        return render(request, 'bookings/payment_error.html', {'error': 'Room no longer available. Payment will be refunded.'})

    try:
        content_type = ContentType.objects.get(id=booking_data['user_content_type_id']) if booking_data.get('user_content_type_id') else None
    except ContentType.DoesNotExist:
        content_type = None

    # Create booking
    booking = Booking(
        room=room,
        check_in=check_in,
        check_out=check_out,
        total_hours=booking_data['total_hours'],
        is_paid=True,
        payment_reference=reference,
        name=booking_data['name'],
        email=booking_data['email'],
        phone_number=booking_data['phone_number'],
        booking_reference=reference,
        total_price=Decimal(str(booking_data['total_amount'])) - Decimal(str(booking_data['service_charge'])) - Decimal(str(booking_data['discount_amount'])),
        service_charge=Decimal(str(booking_data['service_charge'])),
        discount_applied=Decimal(str(booking_data['discount_amount'])),
        points_used=booking_data['points_used'],
        content_type=content_type,
        object_id=booking_data['user_object_id'] if booking_data.get('user_object_id') else None,
        total_amount=Decimal(str(booking_data['total_amount'])),
    )
    booking.save()

    # Set extras
    extras = ExtraService.objects.filter(id__in=booking_data['extras_ids'])
    booking.extras.set(extras)

    # Deduct points if applicable
    if booking_data.get('user_object_id') and booking.points_used > 0:
        try:
            user = Customer.objects.get(id=booking_data['user_object_id'])
            user.loyalty_points -= booking.points_used
            user.save()
        except Customer.DoesNotExist:
            logger.warning(f"No Customer found for user_id {booking_data['user_object_id']} when deducting points")

    # Cost breakdown
    if booking.total_hours in [12, 24]:
        if booking.total_hours == 12 and room.twelve_hour_price:
            base_room_cost = room.twelve_hour_price
        elif booking.total_hours == 24 and room.twenty_four_hour_price:
            base_room_cost = room.twenty_four_hour_price
        else:
            base_room_cost = room.price_per_hour * Decimal(str(booking.total_hours))
    else:
        base_room_cost = room.price_per_hour * Decimal(str(booking.total_hours))

    extras_cost = sum(extra.price for extra in extras)
    final_room_cost = base_room_cost - booking.discount_applied
    hotel_revenue = final_room_cost + extras_cost

    # Notifications
    try:
        # Hotel owner email
        subject = 'New Booking Notification'
        context = {
            'booking': booking,
            'base_room_cost': base_room_cost,
            'extras_cost': extras_cost,
            'final_room_cost': final_room_cost,
            'hotel_revenue': hotel_revenue,
        }
        message = render_to_string('bookings/booking_notification.html', context)
        send_mail(subject, '', None, [booking.room.hotel.owner.email], html_message=message)

        # Customer email
        if booking.email:
            subject = 'Booking Confirmation - Hotel per Hour'
            discount_percentage = (
                (booking.discount_applied / base_room_cost * 100) if base_room_cost > 0 else Decimal('0')
            )
            context = {
                'booking': booking,
                'extras_cost': extras_cost,
                'base_room_cost': base_room_cost,
                'final_room_cost': final_room_cost,
                'discount_percentage': discount_percentage,
            }
            customer_html = render_to_string('bookings/customer_confirmation_email.html', context)
            send_mail(subject, '', settings.DEFAULT_FROM_EMAIL, [booking.email], html_message=customer_html, fail_silently=False)
    except Exception as e:
        logger.error(f"Failed to send notifications for booking {booking.booking_reference}: {str(e)}")

    # Clear session
    del request.session['pending_booking_data']
    del request.session['pending_booking_reference']

    return redirect('booking_confirmation', booking_reference=booking.booking_reference)


@csrf_exempt
def paystack_webhook(request):
    if request.method == 'POST':
        payload = json.loads(request.body)
        if payload['event'] == 'charge.success':
            reference = payload['data']['reference']
            # Check if booking exists; if not, log (since created in callback)
            try:
                booking = Booking.objects.get(booking_reference=reference)
                if not booking.is_paid:
                    booking.is_paid = True
                    booking.payment_reference = reference
                    booking.save()
                    # Send notifications if needed (but already sent in callback)
            except Booking.DoesNotExist:
                logger.warning(f"Webhook received for non-existent booking reference: {reference}")
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

def verify_payment(reference):
    url = f'https://api.paystack.co/transaction/verify/{reference}'
    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    response = requests.get(url, headers=headers)
    return response.status_code == 200 and response.json()['data']['status'] == 'success'

def booking_confirmation(request, booking_reference):
    booking = get_object_or_404(Booking, booking_reference=booking_reference)

    # Correct room cost
    if booking.total_hours in [12, 24]:
        if booking.total_hours == 12 and booking.room.twelve_hour_price:
            base_room_cost = booking.room.twelve_hour_price
        elif booking.total_hours == 24 and booking.room.twenty_four_hour_price:
            base_room_cost = booking.room.twenty_four_hour_price
        else:
            base_room_cost = booking.room.price_per_hour * Decimal(str(booking.total_hours))
    else:
        base_room_cost = booking.room.price_per_hour * Decimal(str(booking.total_hours))

    extras_cost = sum(extra.price for extra in booking.extras.all())
    final_room_cost = base_room_cost - booking.discount_applied
    discount_percentage = (
        (booking.discount_applied / base_room_cost * 100) if base_room_cost > 0 else Decimal('0')
    )

    context = {
        'booking': booking,
        'extras_cost': extras_cost,
        'base_room_cost': base_room_cost,
        'final_room_cost': final_room_cost,
        'discount_percentage': discount_percentage,
    }
    return render(request, 'bookings/confirmation.html', context)


def is_room_available(room, check_in, check_out):
    """
    Check if the room is available for booking based on:
    1. Manual availability toggle (is_available)
    2. Available units for the given time period
    """
    if not room.is_available:
        return False
    available_units = room.get_available_units(check_in, check_out)
    return available_units > 0

@login_required
def verify_booking(request):
    # Check user permission
    user = request.user
    is_superuser = user.is_superuser
    is_hotel_owner = Hotel.objects.filter(owner=user).exists()

    if not (is_superuser or is_hotel_owner):
        return HttpResponseForbidden("Only hotel owners and superusers can verify bookings.")

    if request.method == 'POST':
        reference = request.POST.get('reference', '').strip()
        if not reference:
            return render(request, 'bookings/verify.html', {
                'error': 'Please enter a booking reference.'
            })

        try:
            booking = Booking.objects.get(booking_reference=reference)
            # Restrict to hotels owned by this user
            if not is_superuser and booking.room.hotel.owner != user:
                return render(request, 'bookings/verify.html', {
                    'error': 'This booking does not belong to your hotel.'
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

    if not room.is_available:
        return JsonResponse({
            'available': False,
            'message': 'This room is currently not available for booking.'
        })

    if check_in_str and duration:
        try:
            check_in = timezone.make_aware(timezone.datetime.strptime(check_in_str, '%Y-%m-%dT%H:%M'))
            duration = int(duration)
            check_out = check_in + timezone.timedelta(hours=duration)
            available_units = room.get_available_units(check_in, check_out)
            return JsonResponse({
                'available': available_units > 0,
                'message': f'{available_units} unit(s) available for this period' if available_units > 0 else 'No units available for this period'
            })
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