# bookings/models.py
import uuid
from django.db import models
from hotels.models import Room
from users.models import CustomUser
from decimal import Decimal

class Booking(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    total_hours = models.FloatField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)
    booking_reference = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    

    def save(self, *args, **kwargs):
        if self.check_in and self.check_out:
            duration = self.check_out - self.check_in
            self.total_hours = duration.total_seconds() / 3600
            self.total_price = self.room.price_per_hour * Decimal(str(self.total_hours))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.booking_reference} for {self.room} by {self.name}"
