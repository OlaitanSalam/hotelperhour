from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from hotels.models import Hotel

class CustomerManager(BaseUserManager):
    def create_customer(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        customer = self.model(email=email, **extra_fields)
        customer.set_password(password)
        customer.save(using=self._db)
        return customer

class Customer(AbstractBaseUser):
    email = models.EmailField(unique=True, max_length=254)
    full_name = models.CharField(max_length=255, blank=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    loyalty_points = models.IntegerField(default=0)
    favorite_hotels = models.ManyToManyField(
        Hotel,
        related_name='favorited_by',
        blank=True,
        help_text="Hotels this customer has favorited"
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone_number']
    
    objects = CustomerManager()

    def __str__(self):
        return self.email
    
    @property
    def is_customer(self):
        return True

    @property
    def is_hotel_owner(self):
        return False
    
class LoyaltyRule(models.Model):
    points_per_percent = models.IntegerField(help_text="Points required for 1% discount", default=100)
    max_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100, help_text="Maximum discount percentage (e.g., 100 for 100%)")
    min_points_to_use = models.IntegerField(help_text="Minimum points required to use loyalty discount", default=100)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.points_per_percent} points per 1%, max {self.max_discount_percentage}%, min {self.min_points_to_use} points"