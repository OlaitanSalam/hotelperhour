import uuid
from django.db import models
from hotels.models import Room, ExtraService, Hotel
from users.models import CustomUser
from decimal import Decimal
from django.utils.crypto import get_random_string
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from customers.models import Customer



class BookingDuration(models.Model):
    hours = models.PositiveIntegerField(unique=True, help_text="Duration in hours (e.g., 3, 6, 9)")
    
    def __str__(self):
        return f"{self.hours} hours"
    
    class Meta:
        ordering = ['hours']

class Booking(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    user = GenericForeignKey('content_type', 'object_id')
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    total_hours = models.FloatField(default=0.0)
    is_paid = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)
    booking_reference = models.CharField(max_length=10, unique=True, editable=False)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    extras = models.ManyToManyField(ExtraService, blank=True)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    points_used = models.IntegerField(default=0)
    hotel_revenue_snapshot = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Hotel's revenue at time of booking (room cost + extras, frozen)"
    )



    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = self.generate_booking_reference()
        # ✅ Calculate and freeze hotel revenue on first save
        if not self.pk:  # Only on creation
            self.hotel_revenue_snapshot = self._calculate_hotel_revenue()
        super().save(*args, **kwargs)
        if self.is_paid and self.user and isinstance(self.user, Customer):
            points_earned = int(self.total_hours * 10)  # 10 points per hour
            self.user.loyalty_points += points_earned
            self.user.save()
    
    
    '''@property
    def hotel_revenue(self):
        """Full revenue hotel earns: full room cost + extras (ignores discount)"""
        if self.total_hours == 12 and self.room.twelve_hour_price:
            room_cost = self.room.twelve_hour_price
        elif self.total_hours == 24 and self.room.twenty_four_hour_price:
            room_cost = self.room.twenty_four_hour_price
        else:
            room_cost = (self.room.price_per_hour or Decimal('0')) * Decimal(str(self.total_hours or 0))
        
        extras_cost = sum(extra.price or 0 for extra in self.extras.all())
        return room_cost + extras_cost'''
    

    def _calculate_hotel_revenue(self):
        """Calculate hotel revenue based on current prices (used only at booking time)"""
        if self.total_hours == 12 and self.room.twelve_hour_price:
            room_cost = self.room.twelve_hour_price
        elif self.total_hours == 24 and self.room.twenty_four_hour_price:
            room_cost = self.room.twenty_four_hour_price
        else:
            room_cost = (self.room.price_per_hour or Decimal('0')) * Decimal(str(self.total_hours or 0))
        
        # Note: extras are added via M2M, so we calculate them separately
        return room_cost
    
    @property
    def hotel_revenue(self):
        """
        Returns the frozen hotel revenue from booking time.
        This ensures financial integrity even if room prices change later.
        """
        # If snapshot exists, use it (for all new bookings)
        if self.hotel_revenue_snapshot and self.hotel_revenue_snapshot > 0:
            return self.hotel_revenue_snapshot
        
        # Fallback for old bookings (before this field was added)
        return self._calculate_hotel_revenue() + sum(
            extra.price or Decimal('0') for extra in self.extras.all()
        )


    @staticmethod
    def generate_booking_reference():
        prefix = "HPH-"
        while True:
            code = get_random_string(6, allowed_chars='0123456789')
            reference = prefix + code  # e.g., HPH-123456
            if not Booking.objects.filter(booking_reference=reference).exists():
                return reference

    def __str__(self):
        return f"Booking {self.booking_reference} for {self.room} by {self.name}"