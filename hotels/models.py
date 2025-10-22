from django.db import models
from users.models import CustomUser
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.utils import timezone
from PIL import Image, ImageOps
import os
from django.conf import settings
from django.core.exceptions import ValidationError
import logging


logger = logging.getLogger(__name__)

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
    image = models.ImageField(upload_to='hotels/images/default/', null=True, blank=True, default='images/default_hotel.webp')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    account_name = models.CharField(max_length=255, null=True, blank=True)
    bank_name = models.CharField(max_length=255, null=True, blank=True)
    amenities = models.ManyToManyField(Amenity, related_name='hotels', blank=True)
    

    def save(self, *args, **kwargs):
        # Generate slug if not present
        if not self.slug:
            base_slug = slugify(self.get_public_name())  # Changed from self.name
            self.slug = base_slug
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

        # Update image path to hotel-specific folder and convert to WebP
        if self.image and 'default' in self.image.name:  # Skip default image
            pass
        elif self.image:
            new_path = f'hotels/{self.slug}/images/{os.path.basename(self.image.name)}'
            if self.image.name != new_path:
                self.image.name = new_path
                super().save(update_fields=['image'])
            self._convert_image_to_webp(self.image.path)

    def _convert_image_to_webp(self, img_path):
        try:
            img = Image.open(img_path)
            img = ImageOps.exif_transpose(img)
            max_size = (1200, 1200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            webp_path = os.path.splitext(img_path)[0] + ".webp"
            img.save(webp_path, "WEBP", quality=80, method=6)
            self.image.name = os.path.splitext(self.image.name)[0] + ".webp"
            super().save(update_fields=["image"])
            if img_path != webp_path and os.path.exists(img_path):
                os.remove(img_path)
        except Exception as e:
            print("Image processing failed:", e)

    def get_public_name(self):
        return f"Hotel in {self.city}"
    
    def clean(self):
        if not self.image:
            raise ValidationError("An image file is required.")

    def __str__(self):
        return self.name

    def get_featured_image(self):
        if self.image:
            return self.image
        images = self.images.all()
        return images.first().image if images.exists() else 'images/default_hotel.webp'



class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.CharField(max_length=100)
    total_units = models.PositiveIntegerField(default=1, help_text="Number of physical rooms for this category")
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='hotels/rooms/images/default/', null=True, blank=True, default='images/default_room.webp')
    description = models.TextField()
    capacity = models.IntegerField()
    is_available = models.BooleanField(default=True)
    twelve_hour_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)], help_text='Discounted price for 12 hours (optional)')
    twenty_four_hour_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)], help_text='Discounted price for 24 hours (optional)')

    def clean(self):
        if self.twelve_hour_price and self.price_per_hour and self.twelve_hour_price >= self.price_per_hour * 12:
            logger.warning(f"Validation failed for room {self.id}: twelve_hour_price ({self.twelve_hour_price}) >= price_per_hour * 12 ({self.price_per_hour * 12})")
            raise ValidationError("12-hour price must be less than 12 * hourly rate for discount.")
        if self.twenty_four_hour_price and self.price_per_hour and self.twenty_four_hour_price >= self.price_per_hour * 24:
            logger.warning(f"Validation failed for room {self.id}: twenty_four_hour_price ({self.twenty_four_hour_price}) >= price_per_hour * 24 ({self.price_per_hour * 24})")
            raise ValidationError("24-hour price must be less than 24 * hourly rate for discount.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Validate before saving
        super().save(*args, **kwargs)

        # Update image path to hotel-specific folder and convert to WebP
        if self.image and 'default' in self.image.name:  # Skip default image
            pass
        elif self.image:
            new_path = f'hotels/{self.hotel.slug}/rooms/images/{os.path.basename(self.image.name)}'
            if self.image.name != new_path:
                self.image.name = new_path
                super().save(update_fields=['image'])
            self._convert_image_to_webp(self.image.path)

    def _convert_image_to_webp(self, img_path):
        try:
            img = Image.open(img_path)
            img = ImageOps.exif_transpose(img)
            max_size = (1200, 1200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            webp_path = os.path.splitext(img_path)[0] + ".webp"
            img.save(webp_path, "WEBP", quality=80, method=6)
            self.image.name = os.path.splitext(self.image.name)[0] + ".webp"
            super().save(update_fields=["image"])
            if img_path != webp_path and os.path.exists(img_path):
                os.remove(img_path)
        except Exception as e:
            print("Room image processing failed:", e)

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
    image = models.ImageField(upload_to='hotels/images/default/', null=True, blank=True)
    alt_text = models.CharField(max_length=255, blank=True, help_text="Optional description for accessibility")
    order = models.PositiveIntegerField(default=0, help_text="Order for display (lower first)")

    class Meta:
        ordering = ['order']

    @property
    def hotel_slug(self):
        return self.hotel.slug  

    def save(self, *args, **kwargs):
        if not self.hotel_id:
            raise ValueError("Hotel must be set before saving HotelImage")
        
        self.image.field.upload_to = f'hotels/images/{self.hotel.slug}/'
        super().save(*args, **kwargs)
        if self.image and hasattr(self.image, 'path') and os.path.exists(self.image.path):
            self._convert_image_to_webp(self.image.path)


    def _convert_image_to_webp(self, img_path):
        try:
            img = Image.open(img_path)
            img = ImageOps.exif_transpose(img)
            max_size = (1200, 1200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            webp_path = os.path.splitext(img_path)[0] + ".webp"
            img.save(webp_path, "WEBP", quality=80, method=6)
            self.image.name = os.path.splitext(self.image.name)[0] + ".webp"
            super().save(update_fields=["image"])
            if img_path != webp_path and os.path.exists(img_path):
                os.remove(img_path)
        except Exception as e:
            logger.error(f"HotelImage processing failed: {e}")

    def __str__(self):
        return f"Image for {self.hotel.name} ({self.order})"
    


class HotelPolicy(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='policies')
    policy_text = models.TextField(max_length=500, help_text="Enter the policy rule, e.g., 'Check-in: 2:00 PM'")

    def __str__(self):
        return self.policy_text[:50]  # Truncate for display
    
    
