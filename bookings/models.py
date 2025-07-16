import uuid
from django.db import models
from hotels.models import Room, ExtraService
from users.models import CustomUser
from decimal import Decimal
from django.utils.crypto import get_random_string

class BookingDuration(models.Model):
    hours = models.PositiveIntegerField(unique=True, help_text="Duration in hours (e.g., 3, 6, 9)")
    
    def __str__(self):
        return f"{self.hours} hours"
    
    class Meta:
        ordering = ['hours']

class Booking(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    total_hours = models.FloatField()
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

    def save(self, *args, **kwargs):
        update_total_amount = kwargs.pop('update_total_amount', True)
        if not self.booking_reference:
            self.booking_reference = self.generate_booking_reference()
        if self.check_in and self.check_out:
            duration = self.check_out - self.check_in
            self.total_hours = duration.total_seconds() / 3600
            self.total_price = self.room.price_per_hour * Decimal(str(self.total_hours))
            self.service_charge = self.total_price * Decimal('0.10')
            if update_total_amount:
                self.total_amount = self.total_price + self.service_charge
        super().save(*args, **kwargs)
    

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