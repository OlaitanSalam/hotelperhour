from django.db import models
from users.models import CustomUser
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.utils import timezone
from PIL import Image
import os
from django.conf import settings

class Hotel(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True)
    suburb = models.CharField(max_length=100, blank=True)
    hotel_phone = models.CharField(max_length=20, null=True, blank=True)
    hotel_email = models.EmailField(max_length=255, null=True, blank=True)
    description = models.TextField()
    image = models.ImageField(upload_to='hotels/images/', null=True, blank=True, default='images/default_hotel.webp')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    account_name = models.CharField(max_length=255, null=True, blank=True)
    bank_name = models.CharField(max_length=255, null=True, blank=True)

    def save(self, *args, **kwargs):
        # normal slug + city logic
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            counter = 1
            while Hotel.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        if not self.city and self.address:
            parts = self.address.split(',')
            self.city = parts[1].strip() if len(parts) > 1 else "Unknown"

        super().save(*args, **kwargs)  # save first to create file path

        # compress image if exists
        if self.image:
            self._convert_image_to_webp(self.image.path)

    def _convert_image_to_webp(self, img_path):
        try:
            img = Image.open(img_path)
            max_size = (1200, 1200)   # resize max 1200px width/height
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            webp_path = os.path.splitext(img_path)[0] + ".webp"
            img.save(webp_path, "WEBP", quality=80, method=6)

            # update model to use new WebP file
            self.image.name = os.path.splitext(self.image.name)[0] + ".webp"
            super().save(update_fields=["image"])

            # delete old non-webp file if exists
            if img_path != webp_path and os.path.exists(img_path):
                os.remove(img_path)

        except Exception as e:
            print("Image processing failed:", e)

    def get_public_name(self):
        return f"Hotel in {self.city}"

    def __str__(self):
        return self.name


class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.CharField(max_length=100)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='rooms/images/', null=True, blank=True, default='images/default_room.webp')
    description = models.TextField()
    capacity = models.IntegerField()
    is_available = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            self._convert_image_to_webp(self.image.path)

    def _convert_image_to_webp(self, img_path):
        try:
            img = Image.open(img_path)
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


class ExtraService(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='extras')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    def __str__(self):
        return f"{self.name} - {self.hotel.name}"


class Review(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    review_text = models.TextField()
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Review by {self.name} - {self.rating}/5"
