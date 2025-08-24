from django.db import models
from users.models import CustomUser
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.utils import timezone

class Hotel(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True)
    hotel_phone = models.CharField(max_length=20, null=True, blank=True)
    hotel_email = models.EmailField(max_length=255, null=True, blank=True)
    description = models.TextField()
    image = models.ImageField(upload_to='hotels/images/', null=True, blank=True, default='images/default_hotel.jpg')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True)
    account_number = models.CharField(max_length=20, null=True, blank=True)  # Bank account number (Nigerian standard: 10 digits)
    account_name = models.CharField(max_length=255, null=True, blank=True)  # Name on the bank account
    bank_name = models.CharField(max_length=255, null=True, blank=True)  # Name of the bank (e.g., GTBank, First Bank)

    def save(self, *args, **kwargs):
        # Generate slug from name if not provided
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            counter = 1
            while Hotel.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        # Populate city from address if empty (fallback)
        if not self.city and self.address:
            parts = self.address.split(',')
            self.city = parts[1].strip() if len(parts) > 1 else "Unknown"
        super().save(*args, **kwargs)

    def get_public_name(self):
        """Return anonymized name for public display"""
        return f"Hotel in {self.city}"

    def __str__(self):
        return self.name

class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.CharField(max_length=100)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='rooms/images/', null=True, blank=True, default='images/default_room.jpg')
    description = models.TextField()
    capacity = models.IntegerField()
    is_available = models.BooleanField(default=True)

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
