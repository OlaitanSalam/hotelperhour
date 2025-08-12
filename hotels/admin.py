# hotels/admin.py
from django.contrib import admin
from django.contrib import messages
from .models import Hotel, Room
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from bookings.models import Booking
from django.forms import Textarea
from django.db import models

class RoomInline(admin.TabularInline):
    model = Room
    extra = 0

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Hotel model.
    - Displays key fields and allows inline room management.
    - Includes actions to approve or decline hotels with email notifications.
    """
    list_display = ('name', 'owner', 'address', 'hotel_phone', 'hotel_email', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    search_fields = ('name', 'address')
    inlines = [RoomInline]
    actions = ['approve_hotels', 'decline_hotels']
    list_per_page = 20  # Pagination: 20 hotels per page
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Hotel Information', {
            'fields': ('name', 'owner', 'address', 'description', 'hotel_phone', 'hotel_email', 'is_approved')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Bank Details', {
            'fields': ('account_number', 'account_name', 'bank_name'),
            'classes': ('collapse',)
        }),
        ('Images', {
            'fields': ('image',),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('created_at',)
        }),
    )
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={
            'rows': 10,  # Height in rows
            'cols': 30,  # Width in columns
            'style': 'width: 40%; height: 80px;'  # CSS for more precise control
        })},
    }

    def send_approval_email(self, hotel):
        """Send an approval email to the hotel owner."""
        subject = 'Your Hotel Has Been Approved'
        html_message = render_to_string('hotels/approval_email.html', {'hotel': hotel})
        plain_message = strip_tags(html_message)
        email = EmailMultiAlternatives(
            subject, plain_message, 'Hotel Per Hour<no-reply@hotelsperhour.com>', [hotel.owner.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send()

    def send_decline_email(self, hotel):
        """Send a decline email to the hotel owner."""
        subject = 'Your Hotel Has Been Declined'
        html_message = render_to_string('hotels/decline_email.html', {'hotel': hotel})
        plain_message = strip_tags(html_message)
        email = EmailMultiAlternatives(
            subject, plain_message, 'Hotel Per Hour<no-reply@hotelsperhour.com>', [hotel.owner.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send()

    def save_model(self, request, obj, form, change):
        """
        Override save_model to handle saving without sending emails.
        """
        super().save_model(request, obj, form, change)

    def approve_hotels(self, request, queryset):
        """Approve selected hotels and send approval emails."""
        for hotel in queryset:
            if not hotel.is_approved:  # Only update and email if not already approved
                hotel.is_approved = True
                hotel.save()
                self.send_approval_email(hotel)
        self.message_user(request, "Selected hotels have been approved and emails sent.")
    approve_hotels.short_description = "Approve selected hotels"

    def decline_hotels(self, request, queryset):
        """Decline selected hotels and send decline emails."""
        for hotel in queryset:
            if hotel.is_approved:  # Only update and email if currently approved
                hotel.is_approved = False
                hotel.save()
                self.send_decline_email(hotel)
        self.message_user(request, "Selected hotels have been declined and emails sent.")
    decline_hotels.short_description = "Decline selected hotels"

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Room model.
    - Displays room details and availability status.
    - Includes a method to check if the room is currently booked.
    """
    list_display = ('room_type', 'hotel', 'price_per_hour', 'is_available', 'is_currently_booked')
    list_per_page = 20  # Pagination: 20 rooms per page
    search_fields = ('room_type', 'hotel__name', 'description')
    list_filter = ('hotel', 'is_available')
    fieldsets = (
        ('Room Information', {
            'fields': ('hotel', 'room_type', 'price_per_hour', 'description', 'capacity', 'is_available')
        }),
        ('Images', {
            'fields': ('image',),
            'classes': ('collapse',)
        }),
    )
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={
            'rows': 10,  # Height in rows
            'cols': 30,  # Width in columns
            'style': 'width: 40%; height: 80px;'  # CSS for more precise control
        })},
    }

    def is_currently_booked(self, obj):
        """
        Check if the room is currently booked.
        Returns True if there is an active booking at the current time.
        """
        now = timezone.now()
        return Booking.objects.filter(
            room=obj,
            check_in__lte=now,
            check_out__gte=now
        ).exists()
    is_currently_booked.boolean = True  # Display as a boolean icon in admin
    is_currently_booked.short_description = 'Currently Booked'



from .models import Review

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'rating', 'review_text_short', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('name', 'email', 'review_text')
    ordering = ('-created_at',)
    readonly_fields = ('rating', 'created_at')

    def review_text_short(self, obj):
        return obj.review_text[:50] + '...' if len(obj.review_text) > 50 else obj.review_text
    review_text_short.short_description = 'Review Text'

admin.site.register(Review, ReviewAdmin)