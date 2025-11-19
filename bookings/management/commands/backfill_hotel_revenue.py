from django.core.management.base import BaseCommand
from bookings.models import Booking
from decimal import Decimal

class Command(BaseCommand):
    help = 'Backfill hotel_revenue_snapshot for existing bookings'

    def handle(self, *args, **options):
        bookings = Booking.objects.filter(
            hotel_revenue_snapshot=0
        ).select_related('room').prefetch_related('extras')
        
        count = 0
        for booking in bookings:
            # Calculate revenue based on prices at booking time (best effort)
            if booking.total_hours == 12 and booking.room.twelve_hour_price:
                room_cost = booking.room.twelve_hour_price
            elif booking.total_hours == 24 and booking.room.twenty_four_hour_price:
                room_cost = booking.room.twenty_four_hour_price
            else:
                room_cost = (booking.room.price_per_hour or Decimal('0')) * Decimal(str(booking.total_hours or 0))
            
            extras_cost = sum(extra.price or Decimal('0') for extra in booking.extras.all())
            booking.hotel_revenue_snapshot = room_cost + extras_cost
            booking.save(update_fields=['hotel_revenue_snapshot'])
            count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully backfilled {count} bookings')
        )