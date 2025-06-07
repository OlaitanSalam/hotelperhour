from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

class CustomUserManager(BaseUserManager):
       # Create a regular user
       def create_user(self, email, password=None, **extra_fields):
           if not email:
               raise ValueError('The Email field must be set')
           email = self.normalize_email(email)
           user = self.model(email=email, **extra_fields)
           user.set_password(password)
           user.save(using=self._db)
           return user

       # Create a superuser (admin)
       def create_superuser(self, email, password=None, **extra_fields):
           extra_fields.setdefault('is_staff', True)
           extra_fields.setdefault('is_active', True)
           extra_fields.setdefault('is_superuser', True)
           return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
       email = models.EmailField(unique=True, max_length=254)
       full_name = models.CharField(max_length=255, blank=True)  # Added for hotel owners
       phone_number = models.CharField(max_length=20, blank=True)
       is_hotel_owner = models.BooleanField(default=False)  # Differentiate regular users and hotel owners
       is_active = models.BooleanField(default=False)  # For email confirmation
       is_staff = models.BooleanField(default=False)  # For admin access
       date_joined = models.DateTimeField(default=timezone.now)

       objects = CustomUserManager()

       USERNAME_FIELD = 'email'  # Use email for login instead of username
       REQUIRED_FIELDS = ['full_name', 'phone_number']  # No additional required fields

       def __str__(self):
           return self.email