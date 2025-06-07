# bookings/admin.py
from django.contrib import admin
from .models import Booking


class BookingAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Booking model.
    - Displays key fields for quick reference.
    - Filters and searches for efficient data retrieval.
    - Includes a method to check if the booking user is a hotel owner.
    """
    list_display = ['id', 'room', 'user', 'is_hotel_owner', 'booking_reference',
                    'check_in', 'check_out', 'is_paid', 'name', 'email', 'phone_number']
    list_filter = ['is_paid', 'room__hotel']
    search_fields = ['name', 'email', 'phone_number', 'room__hotel__name', 'booking_reference']
    list_per_page = 20  # Pagination: 20 bookings per page
    ordering = ['-created_at']  # Order by most recent bookings first
    readonly_fields = ['created_at', 'booking_reference', 'payment_reference']
    fieldsets = (
        ('Booking Details', {
            'fields': ('room', 'user', 'check_in', 'check_out', 'total_hours', 'total_price')
        }),
        ('Payment Information', {
            'fields': ('is_paid', 'payment_reference')
        }),
        ('User Information', {
            'fields': ('name', 'email', 'phone_number')
        }),
        ('Additional Information', {
            'fields': ('booking_reference', 'created_at')
        }),
    )

    def is_hotel_owner(self, obj):
        """
        Check if the booking user is a hotel owner.
        Returns True if the user is a hotel owner, False otherwise.
        """
        if obj.user:
            return obj.user.is_hotel_owner
        return False
    is_hotel_owner.boolean = True  # Display as a boolean icon in admin
    is_hotel_owner.short_description = 'Hotel Owner'

admin.site.register(Booking, BookingAdmin)