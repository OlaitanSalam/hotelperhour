# bookings/tasks.py
from django_q.tasks import async_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging
from decimal import Decimal
#from utils.sms import send_sms


logger = logging.getLogger(__name__)

def send_booking_emails(booking_id):
    from bookings.models import Booking
    try:
        booking = Booking.objects.select_related('room__hotel__owner').prefetch_related('extras').get(id=booking_id)
        room = booking.room

        # Recalculate pricing (same as in view)
        if booking.total_hours == 12 and room.twelve_hour_price:
            base_cost = room.twelve_hour_price
        elif booking.total_hours == 24 and room.twenty_four_hour_price:
            base_cost = room.twenty_four_hour_price
        else:
            base_cost = room.price_per_hour * Decimal(str(booking.total_hours))

        extras_cost = sum(e.price for e in booking.extras.all())
        final_room_cost = base_cost - booking.discount_applied
        hotel_revenue = base_cost + extras_cost

        price_per_hour_display = (
            room.twelve_hour_price if booking.total_hours == 12 and room.twelve_hour_price else
            room.twenty_four_hour_price if booking.total_hours == 24 and room.twenty_four_hour_price else
            room.price_per_hour
        )

        # 1. Hotel Owner Email
        hotel_html = render_to_string('bookings/booking_notification.html', {
            'booking': booking,
            'base_room_cost': base_cost,
            'extras_cost': extras_cost,
            'final_room_cost': final_room_cost,
            'hotel_revenue': hotel_revenue,
            'hours_paid': booking.total_hours,
            'price_per_hour_display': price_per_hour_display,
        })
        send_mail(
            'New Booking Notification',
            '',
            None,
            [room.hotel.owner.email],
            html_message=hotel_html,
            fail_silently=False,
        )

        # 2. Customer Email
        if booking.email:
            discount_percentage = (booking.discount_applied / base_cost * 100) if base_cost > 0 else 0
            customer_html = render_to_string('bookings/customer_confirmation_email.html', {
                'booking': booking,
                'base_room_cost': base_cost,
                'final_room_cost': final_room_cost,
                'extras_cost': extras_cost,
                'discount_percentage': discount_percentage,
                'hours_paid': booking.total_hours,
                'price_per_hour_display': price_per_hour_display,
            })
            send_mail(
                'Booking Confirmation - Hotel per Hour',
                '',
                settings.DEFAULT_FROM_EMAIL,
                [booking.email],
                html_message=customer_html,
                fail_silently=False,
            )

        # 3. Admin Email
        admin_html = render_to_string('bookings/admin_booking_notification.html', {
            'booking': booking,
            'total_amount': booking.total_amount,
            'service_charge': booking.service_charge,
            'hotel_revenue': hotel_revenue,
        })
        send_mail(
            f'New Booking #{booking.booking_reference}',
            '',
            settings.DEFAULT_FROM_EMAIL,
            ['admin@inovacaong.com'],
            html_message=admin_html,
            fail_silently=False,
        )

    except Exception as e:
        logger.error(f"Failed to send emails for booking {booking_id}: {e}", exc_info=True)
    
    # === SEND SMS TO HOTEL OWNER AFTER EMAILS ===
    '''try:
        hotel_phone = room.hotel.hotel_phone

        if hotel_phone:
            # Normalize phone number
            phone = hotel_phone.strip()
            if phone.startswith("0"):
                phone = "234" + phone[1:]
            if phone.startswith("+"):
                phone = phone.replace("+", "")

            sms_message = (
                f"New Booking!\n"
                f"Hotel: {room.hotel.name}\n"
                f"Room: {room.room_type}\n"
                f"Guest: {booking.name}\n"
                f"Ref: {booking.booking_reference}"
            )

            send_sms(sms_message, phone)

    except Exception as sms_err:
        logger.error(f"Failed to send SMS for booking {booking_id}: {sms_err}")'''
