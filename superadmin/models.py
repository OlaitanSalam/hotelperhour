from django.db import models
from django.utils import timezone
from hotels.models import Hotel
from bookings.models import Booking
from decimal import Decimal

# your models here

class PayoutRecord(models.Model):
    """
    Tracks all payouts made to hotels.
    Uses rolling settlement: bookings must be 8+ days old to be payable.
    """
    PAYOUT_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved - Ready to Pay'),
        ('processing', 'Processing Payment'),
        ('completed', 'Payment Completed'),
        ('failed', 'Payment Failed'),
    ]
    
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='payouts')
    payout_reference = models.CharField(max_length=50, unique=True, editable=False)
    
    # Period this payout covers
    period_start = models.DateField(help_text="Start date of booking period (inclusive)")
    period_end = models.DateField(help_text="End date of booking period (inclusive)")
    
    # Financial breakdown
    gross_revenue = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Total revenue (room + extras - discounts) before commission"
    )
    commission_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Platform commission (10% of gross revenue)"
    )
    net_payout = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Amount actually paid to hotel (90% of gross revenue)"
    )
    booking_count = models.PositiveIntegerField(default=0)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=PAYOUT_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'users.CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_payouts'
    )
    
    # Payment details
    paystack_transfer_code = models.CharField(max_length=100, blank=True, null=True)
    paystack_response = models.JSONField(null=True, blank=True)
    
    # Notes and metadata
    notes = models.TextField(blank=True, help_text="Internal notes about this payout")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hotel', 'status']),
            models.Index(fields=['period_start', 'period_end']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.payout_reference:
            self.payout_reference = self.generate_payout_reference()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_payout_reference():
        """Generate unique payout reference like PO-20241113-ABC123"""
        from django.utils.crypto import get_random_string
        prefix = f"HPH-PO-{timezone.now().strftime('%Y%m%d')}"
        while True:
            code = get_random_string(6, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            reference = f"{prefix}-{code}"
            if not PayoutRecord.objects.filter(payout_reference=reference).exists():
                return reference
    
    def __str__(self):
        return f"{self.payout_reference} - {self.hotel.name} (₦{self.net_payout:,.2f})"
    
    def get_related_bookings(self):
        """Get all bookings included in this payout"""
        from django.db.models import Q
        return Booking.objects.filter(
            room__hotel=self.hotel,
            is_paid=True,
            created_at__date__gte=self.period_start,
            created_at__date__lte=self.period_end
        ).select_related('room')