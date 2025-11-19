from django.db import models
from users.models import CustomUser
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.utils import timezone
from PIL import Image
import os
from django.conf import settings
from django.core.exceptions import ValidationError
import logging
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import timedelta
from django.utils.deconstruct import deconstructible




logger = logging.getLogger(__name__)

DURATION_MODE_CHOICES = [
    ('all', 'All Durations Available'),
    ('12_only', '12-Hour Bookings Only'),
    ('24_only', '24-Hour Bookings Only'),
    ('12_and_24', '12-Hour and 24-Hour Only'),
]

def validate_image_size(value):
    if value.size > 2 * 1024 * 1024:  # 2 MB
        raise ValidationError("Image must be under 2MB")
    
@deconstructible
class UploadToPath:
    def __init__(self, subfolder):
        self.subfolder = subfolder.rstrip('/')

    def __call__(self, instance, filename):
        hotel = instance if hasattr(instance, 'slug') else instance.hotel
        slug = getattr(hotel, 'slug', 'unsaved')
        name, ext = os.path.splitext(filename)
        safe_name = name.replace(' ', '_')
        return f"hotels/{slug}/{self.subfolder}/{safe_name}{ext.lower()}"

class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon_class = models.CharField(max_length=100, blank=True, help_text="Font Awesome class, e.g., 'fa-solid fa-wifi'")
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name

class Hotel(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True)
    suburb = models.CharField(max_length=100, blank=True)
    hotel_phone = models.CharField(max_length=20, null=True, blank=True)
    hotel_email = models.EmailField(max_length=255, null=True, blank=True)
    description = models.TextField()
    image = models.ImageField(upload_to=UploadToPath('cover'), null=True, blank=True, default='images/default_hotel.webp', validators=[validate_image_size],)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    account_name = models.CharField(max_length=255, null=True, blank=True)
    bank_name = models.CharField(max_length=255, null=True, blank=True)
    amenities = models.ManyToManyField(Amenity, related_name='hotels', blank=True)
    blackout_start = models.TimeField(
        null=True, blank=True,
        help_text="Start of blackout (e.g. 22:00). App bookings blocked during this window."
    )
    blackout_end = models.TimeField(
        null=True, blank=True,
        help_text="End of blackout (e.g. 06:00). Supports overnight (e.g. 22:00 → 06:00)."
    )
    duration_mode = models.CharField(
    max_length=20,
    choices=DURATION_MODE_CHOICES,
    default='all',
    help_text="Control which booking durations guests can select"
    )
    

    def save(self, *args, **kwargs):
        # Generate slug if not present
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            counter = 1
            while Hotel.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        # Set city from address if not provided
        if not self.city and self.address:
            parts = self.address.split(',')
            self.city = parts[1].strip() if len(parts) > 1 else "Unknown"

        super().save(*args, **kwargs)  # Save to generate slug if new

        # === PROCESS IMAGE (only if uploaded and not WebP) ===
        if self.image and not self.image.name.lower().endswith('.webp'):
            self._process_image()


    def _process_image(self):
        try:
            # Open original file
            original_path = self.image.path
            img = Image.open(original_path)
            img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

            # Save as WebP
            webp_path = os.path.splitext(original_path)[0] + ".webp"
            img.save(webp_path, "WEBP", quality=80, method=6)

            # Update DB path
            old_name = self.image.name
            new_name = os.path.splitext(old_name)[0] + ".webp"
            self.image.name = new_name
            self.save(update_fields=['image'])

            # Delete original file
            if os.path.exists(original_path) and original_path != webp_path:
                os.remove(original_path)
                logger.info(f"Deleted original: {original_path}")

            logger.info(f"Converted: {old_name} → {new_name}")

        except Exception as e:
            logger.error(f"Image processing failed: {e}")


    def get_public_name(self):
        return f"Hotel in {self.city}"

    def __str__(self):
        return self.name

    def get_featured_image(self):
        if self.image:
            return self.image
        images = self.images.all()
        return images.first().image if images.exists() else 'images/default_hotel.webp'
    
    def clean(self):
        if self.blackout_start and self.blackout_end:
            if self.blackout_start == self.blackout_end:
                raise ValidationError("Blackout start and end times cannot be the same.")
        super().clean()

    def is_in_blackout(self, dt=None):
        """
        Returns True if `dt` (datetime) falls in blackout window.
        If dt is None, uses current time.
        Handles overnight (e.g. 22:00 → 06:00).
        """
        if not self.blackout_start or not self.blackout_end:
            return False

        dt = dt or timezone.localtime()
        time_now = dt.time()
        start = self.blackout_start
        end = self.blackout_end

        if start < end:
            return start <= time_now < end
        else:  # overnight
            return time_now >= start or time_now < end

    def __str__(self):
        if self.blackout_start and self.blackout_end:
            s = self.blackout_start.strftime("%I:%M %p")
            e = self.blackout_end.strftime("%I:%M %p")
            return f"{self.name}"
        return self.name
    
    def get_available_durations(self):
        """
        Returns list of (hours, display_name) based on hotel mode.
        Shows price if ANY room has it set.
        """
        try:
            from bookings.models import BookingDuration
        except ImportError:
            logger.error("Could not import BookingDuration")
            return []

        durations = []

        # Use correct reverse relation
        rooms = self.rooms.all()  # ← CHANGE THIS LINE

        if self.duration_mode == 'all':
            # 1. Standard hourly durations
            for d in BookingDuration.objects.all():
                durations.append((d.hours, f"{d.hours} hours"))

            # 2. 12-hour: show if ANY room has price
            if rooms.filter(twelve_hour_price__isnull=False, twelve_hour_price__gt=0).exists():
                sample = rooms.filter(twelve_hour_price__isnull=False).first()
                durations.append((12, f"12 hours (₦{sample.twelve_hour_price})"))

            # 3. 24-hour: show if ANY room has price
            if rooms.filter(twenty_four_hour_price__isnull=False, twenty_four_hour_price__gt=0).exists():
                sample = rooms.filter(twenty_four_hour_price__isnull=False).first()
                durations.append((24, f"24 hours (₦{sample.twenty_four_hour_price})"))

        elif self.duration_mode == '12_only':
            room = rooms.filter(twelve_hour_price__isnull=False).first()
            if room and room.twelve_hour_price:
                durations = [(12, f"12 hours (₦{room.twelve_hour_price})")]
            else:
                durations = [(12, "12 hours")]

        elif self.duration_mode == '24_only':
            room = rooms.filter(twenty_four_hour_price__isnull=False).first()
            if room and room.twenty_four_hour_price:
                durations = [(24, f"24 hours (₦{room.twenty_four_hour_price})")]
            else:
                durations = [(24, "24 hours (Full Day)")]

        elif self.duration_mode == '12_and_24':
            room_12 = rooms.filter(twelve_hour_price__isnull=False).first()
            room_24 = rooms.filter(twenty_four_hour_price__isnull=False).first()

            if room_12 and room_12.twelve_hour_price:
                durations.append((12, f"12 hours (₦{room_12.twelve_hour_price})"))
            else:
                durations.append((12, "12 hours"))

            if room_24 and room_24.twenty_four_hour_price:
                durations.append((24, f"24 hours (₦{room_24.twenty_four_hour_price})"))
            else:
                durations.append((24, "24 hours (Full Day)"))

        return durations
    def get_display_pricing_info(self):
       
       """
       Returns the appropriate pricing information to display based on duration mode.
       Returns: dict with 'price', 'unit', 'mode_label', 'mode_badge_color', 'description'
       """
       rooms = self.rooms.all()
       if not rooms.exists():
           return {
               'price': 'N/A',
               'unit': '',
               'mode_label': 'No rooms',
               'mode_badge_color': 'secondary',
               'description': 'Contact hotel for pricing'
           }

       # === SAFE: Always define sample_room before using it ===
       sample_room = None

       if self.duration_mode == 'all':
           sample_room = rooms.filter(price_per_hour__gt=0).first()
           if not sample_room:
               sample_room = rooms.first()
           price = sample_room.price_per_hour or 0
           return {
               'price': f"₦{price:,.0f}" if price else "N/A",
               'unit': '/hour' if price else '',
               'mode_label': 'Flexible Booking',
               'mode_badge_color': 'success',
               'description': '3, 6, 9 hours + optional 12/24'
           }

       elif self.duration_mode == '12_only':
           sample_room = rooms.filter(twelve_hour_price__gt=0).first() or rooms.first()
           price = (sample_room.twelve_hour_price or 0) if sample_room else 0
           return {
               'price': f"₦{price:,.0f}" if price else "N/A",
               'unit': '/12 hours' if price else '',
               'mode_label': '12-Hour Stays',
               'mode_badge_color': 'info',
               'description': 'Half-day bookings only'
           }

       elif self.duration_mode == '24_only':
           sample_room = rooms.filter(twenty_four_hour_price__gt=0).first() or rooms.first()
           price = (sample_room.twenty_four_hour_price or 0) if sample_room else 0
           return {
               'price': f"₦{price:,.0f}" if price else "N/A",
               'unit': '/day' if price else '',
               'mode_label': 'Full Day',
               'mode_badge_color': 'warning',
               'description': '24-hour bookings only'
           }

       elif self.duration_mode == '12_and_24':
           sample_room = rooms.filter(twelve_hour_price__gt=0).first() or rooms.first()
           price_12 = (sample_room.twelve_hour_price or 0) if sample_room else 0
           return {
               'price': f"From ₦{price_12:,.0f}" if price_12 else "N/A",
               'unit': '',
               'mode_label': '12 & 24 Hours',
               'mode_badge_color': 'primary',
               'description': 'Choose 12 or 24-hour stays'
           }

       # Fallback
       return {
           'price': 'Contact Hotel',
           'unit': '',
           'mode_label': 'Contact Hotel',
           'mode_badge_color': 'secondary',
           'description': 'Call for pricing information'
       }
    
    def get_pending_revenue(self):
        """
        Revenue from bookings 0-3 days old (not yet payable).
        These bookings are in the "holding period" for refunds/disputes.
        """
        from bookings.models import Booking
        
        cutoff_date = timezone.now().date() - timedelta(days=3)
        
        bookings = Booking.objects.filter(
            room__hotel=self,
            is_paid=True,
            created_at__date__gt=cutoff_date  # Last 3 days
        ).select_related('room').prefetch_related('extras')
        
        # ✅ Calculate manually using the property
        total = Decimal('0.00')
        for booking in bookings:
            total += booking.hotel_revenue
        
        return total

    def get_payable_revenue(self):
        """
        Revenue from bookings 4+ days old (ready for payout).
        These have passed the holding period and can be safely disbursed.
        Excludes already-paid bookings.
        """
        from bookings.models import Booking
        from superadmin.models import PayoutRecord
        
        cutoff_date = timezone.now().date() - timedelta(days=3)
        
        # Get all booking IDs that have already been paid
        paid_booking_ids = []
        for payout in PayoutRecord.objects.filter(
            hotel=self,
            status__in=['completed', 'processing']
        ):
            paid_booking_ids.extend(
                list(payout.get_related_bookings().values_list('id', flat=True))
            )
        
        # Get unpaid bookings older than 3 days
        bookings = Booking.objects.filter(
            room__hotel=self,
            is_paid=True,
            created_at__date__lte=cutoff_date  # 4+ days ago
        ).exclude(
            id__in=paid_booking_ids  # Not already included in a payout
        ).select_related('room').prefetch_related('extras')
        
        # ✅ Calculate manually using the property
        total = Decimal('0.00')
        for booking in bookings:
            total += booking.hotel_revenue
        
        return total

    def get_last_payout_date(self):
        """Get the date of the most recent completed payout"""
        from superadmin.models import PayoutRecord
        
        last_payout = PayoutRecord.objects.filter(
            hotel=self,
            status='completed'
        ).order_by('-paid_at').first()
        
        return last_payout.paid_at if last_payout else None

    def calculate_next_payout_due(self):
        """
        Calculate when the next payout is due.
        Returns None if no payment schedule is set.
        Payouts are processed every 3 days after bookings are made.
        """
        last_payout = self.get_last_payout_date()
        
        if not last_payout:
            # If never paid, next payout is 3 days from now
            return timezone.now().date() + timedelta(days=3)
        
        # Next payout is 3 days after last payout
        return last_payout.date() + timedelta(days=3)
    



class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.CharField(max_length=100)
    total_units = models.PositiveIntegerField(default=1, help_text="Number of physical rooms for this category")
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, null=True,  blank=True, validators=[MinValueValidator(0)], help_text="Hourly rate (required only if offering 3, 6, 9 hour bookings)")
    image = models.ImageField(upload_to=UploadToPath('rooms'), null=True, blank=True, default='images/default_room.webp', validators=[validate_image_size])
    description = models.TextField()
    capacity = models.IntegerField()
    is_available = models.BooleanField(default=True)
    twelve_hour_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)], help_text='Fixed price for 12-hour booking')
    twenty_four_hour_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)], help_text='Fixed price for 24-hour booking')

    '''def clean(self):
        """
        Smart validation based on hotel's duration mode:
        - 'all' mode: Requires price_per_hour + optional 12/24 (if set, must be discounted)
        - '12_only': Requires twelve_hour_price only
        - '24_only': Requires twenty_four_hour_price only
        - '12_and_24': Requires both twelve and twenty_four prices
        """
        hotel_mode = self.hotel.duration_mode if self.hotel else 'all'
        
        # ========== VALIDATION LOGIC BASED ON HOTEL MODE ==========
        
        if hotel_mode == 'all':
            # Standard mode: Must have hourly rate
            if not self.price_per_hour:
                raise ValidationError({
                    'price_per_hour': 'Hourly rate is required when hotel accepts all durations.'
                })
            
            # If 12-hour price is set, it must be a discount
            if self.twelve_hour_price:
                if self.twelve_hour_price >= self.price_per_hour * 12:
                    raise ValidationError({
                        'twelve_hour_price': f'Must be less than ₦{self.price_per_hour * 12:,.2f} (12 × hourly rate) to be a discount.'
                    })
            
            # If 24-hour price is set, it must be a discount
            if self.twenty_four_hour_price:
                if self.twenty_four_hour_price >= self.price_per_hour * 24:
                    raise ValidationError({
                        'twenty_four_hour_price': f'Must be less than ₦{self.price_per_hour * 24:,.2f} (24 × hourly rate) to be a discount.'
                    })
        
        elif hotel_mode == '12_only':
            # Only 12-hour bookings: Must have 12-hour price, others optional
            if not self.twelve_hour_price:
                raise ValidationError({
                    'twelve_hour_price': 'This hotel only accepts 12-hour bookings. You must set a 12-hour price.'
                })
        
        elif hotel_mode == '24_only':
            # Only 24-hour bookings: Must have 24-hour price, others optional
            if not self.twenty_four_hour_price:
                raise ValidationError({
                    'twenty_four_hour_price': 'This hotel only accepts 24-hour bookings. You must set a 24-hour price.'
                })
        
        elif hotel_mode == '12_and_24':
            # Both 12 and 24-hour: Must have both prices
            errors = {}
            if not self.twelve_hour_price:
                errors['twelve_hour_price'] = 'This hotel requires 12-hour pricing.'
            if not self.twenty_four_hour_price:
                errors['twenty_four_hour_price'] = 'This hotel requires 24-hour pricing.'
            
            if errors:
                raise ValidationError(errors)'''

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

        if self.image and not self.image.name.lower().endswith('.webp'):
            self._process_image()

    def _process_image(self):
        try:
            # Open original file
            original_path = self.image.path
            img = Image.open(original_path)
            img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

            # Save as WebP
            webp_path = os.path.splitext(original_path)[0] + ".webp"
            img.save(webp_path, "WEBP", quality=80, method=6)

            # Update DB path
            old_name = self.image.name
            new_name = os.path.splitext(old_name)[0] + ".webp"
            self.image.name = new_name
            self.save(update_fields=['image'])

            # Delete original file
            if os.path.exists(original_path) and original_path != webp_path:
                os.remove(original_path)
                logger.info(f"Deleted original: {original_path}")

            logger.info(f"Converted: {old_name} → {new_name}")

        except Exception as e:
            logger.error(f"Image processing failed: {e}")

    def __str__(self):
        return f"{self.room_type} - {self.hotel.name}"
    
    def get_available_units(self, check_in, check_out):
        """
        Calculate available units for a specific time period considering overlapping bookings.
        Returns the number of units available for the given time slot.
        """
        from bookings.models import Booking
        from django.db.models import Count
        from django.db.models.functions import Greatest

        # Get all paid bookings that overlap with the requested time period
        overlapping_bookings = Booking.objects.filter(
            room=self,
            check_in__lt=check_out,
            check_out__gt=check_in,
            is_paid=True
        )

        if not overlapping_bookings.exists():
            return self.total_units

        # Count maximum concurrent bookings in the requested period
        max_concurrent_bookings = overlapping_bookings.count()
        return max(0, self.total_units - max_concurrent_bookings)
    
    def get_display_price_info(self):
        """
        Returns room pricing info based on parent hotel's duration mode.
        Returns: dict with 'primary_price', 'primary_unit', 'secondary_info'
        """
        hotel_mode = self.hotel.duration_mode
        
        if hotel_mode == 'all':
            if not self.price_per_hour or self.price_per_hour <= 0:
                return {
                    'primary_price': 'N/A',
                    'primary_unit': '',
                    'secondary_info': None
                }
            # Show hourly rate prominently
            return {
                'primary_price': f"₦{self.price_per_hour:,.0f}" if self.price_per_hour else "N/A",
                'primary_unit': '/hour',
                # When hotel is in 'all' mode and an hourly rate exists, prefer showing the hourly
                # price only in room cards. Do not surface 12/24 prices here so the UI stays clean.
                'secondary_info': None
            }
        
        elif hotel_mode == '12_only':
            return {
                'primary_price': f"₦{self.twelve_hour_price:,.0f}" if self.twelve_hour_price else "N/A",
                'primary_unit': '/12 hours',
                'secondary_info': None
            }
        
        elif hotel_mode == '24_only':
            return {
                'primary_price': f"₦{self.twenty_four_hour_price:,.0f}" if self.twenty_four_hour_price else "N/A",
                'primary_unit': '/day',
                'secondary_info': None
            }
        
        elif hotel_mode == '12_and_24':
            # Show both prices
            price_12 = f"₦{self.twelve_hour_price:,.0f}" if self.twelve_hour_price else "N/A"
            price_24 = f"₦{self.twenty_four_hour_price:,.0f}" if self.twenty_four_hour_price else "N/A"
            return {
                'primary_price': price_12,
                'primary_unit': '/12 hrs',
                'secondary_info': f"{price_24} /24 hrs"
            }
        
        return {
            'primary_price': 'Contact Hotel',
            'primary_unit': '',
            'secondary_info': None
        }
    
    def _get_discount_info(self):
        """Helper to show discount prices if available"""
        info_parts = []
        if self.twelve_hour_price:
            info_parts.append(f"₦{self.twelve_hour_price:,.0f}/12hrs")
        if self.twenty_four_hour_price:
            info_parts.append(f"₦{self.twenty_four_hour_price:,.0f}/24hrs")
        
        return " • ".join(info_parts) if info_parts else None


class ExtraService(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='extras')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    def __str__(self):
        return f"{self.name} - {self.hotel.name}"
    



class Review(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='reviews')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    review_text = models.TextField()
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    created_at = models.DateTimeField(default=timezone.now)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Review for {self.hotel.name} by {self.name} - {self.rating}/5"
    
class AppFeedback(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    review_text = models.TextField()
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    created_at = models.DateTimeField(default=timezone.now)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback by {self.name} - {self.rating}/5"
    



class HotelImage(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=UploadToPath('gallery'), null=True, blank=True, validators=[validate_image_size],)
    alt_text = models.CharField(max_length=255, blank=True, help_text="Optional description for accessibility")
    order = models.PositiveIntegerField(default=0, help_text="Order for display (lower first)")

    class Meta:
        ordering = ['order']

    @property
    def hotel_slug(self):
        return self.hotel.slug  

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.image and not self.image.name.lower().endswith('.webp'):
            self._process_image()

    def _process_image(self):
        try:
            # Open original file
            original_path = self.image.path
            img = Image.open(original_path)
            img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

            # Save as WebP
            webp_path = os.path.splitext(original_path)[0] + ".webp"
            img.save(webp_path, "WEBP", quality=80, method=6)

            # Update DB path
            old_name = self.image.name
            new_name = os.path.splitext(old_name)[0] + ".webp"
            self.image.name = new_name
            self.save(update_fields=['image'])

            # Delete original file
            if os.path.exists(original_path) and original_path != webp_path:
                os.remove(original_path)
                logger.info(f"Deleted original: {original_path}")

            logger.info(f"Converted: {old_name} → {new_name}")

        except Exception as e:
            logger.error(f"Image processing failed: {e}")

    def __str__(self):
        return f"Image for {self.hotel.name} ({self.order})"
    


class HotelPolicy(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='policies')
    policy_text = models.TextField(max_length=500, help_text="Enter the policy rule, e.g., 'Check-in: 2:00 PM'")

    def __str__(self):
        return self.policy_text[:50]  # Truncate for display
    
    
