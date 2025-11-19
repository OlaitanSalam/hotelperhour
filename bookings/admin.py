# bookings/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Booking, BookingDuration


@admin.register(BookingDuration)
class BookingDurationAdmin(admin.ModelAdmin):
    list_display = ('hours',)
    ordering = ('hours',)


class PaidFilter(admin.SimpleListFilter):
    """Custom filter for payment status."""
    title = _('Payment Status')
    parameter_name = 'is_paid'

    def lookups(self, request, model_admin):
        return [
            ('paid', _('Paid')),
            ('unpaid', _('Unpaid')),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'paid':
            return queryset.filter(is_paid=True)
        if self.value() == 'unpaid':
            return queryset.filter(is_paid=False)
        return queryset


class DateRangeFilter(admin.DateFieldListFilter):
    """Custom date filter for bookings."""
    pass


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """
    Improved admin configuration for the Booking model.
    - Adds color-coded status for payments.
    - Includes date hierarchy for quick navigation.
    - Extra filters (by payment status, date, and hotel).
    - Better grouping in fieldsets.
    """

    list_display = [
        'booking_reference',
        'room',
        'hotel_name',
        'get_user',
        'check_in',
        'check_out',
        'colored_payment_status',
        'total_price',
        'service_charge',
        'discount_applied',
        'hotel_revenue_display',
        'total_amount_display',
    ]
    list_filter = [PaidFilter, ('check_in', DateRangeFilter), 'room__hotel']
    search_fields = [
        'name', 'email', 'phone_number',
        'room__hotel__name', 'booking_reference'
    ]
    date_hierarchy = 'check_in'  # Nice navigation by check-in date
    list_per_page = 25
    ordering = ['-created_at']

    readonly_fields = [
        'created_at', 'booking_reference', 'payment_reference',
        'content_type', 'object_id', 'get_user', 'is_paid', 'total_amount_display',
        'total_price', 'total_hours'
    ]

    fieldsets = (
        (_('Booking Details'), {
            'fields': (
                'room',  'get_user',
                'check_in', 'check_out', 'total_hours',
                'total_price', 'total_amount', 'hotel_revenue_snapshot'
            )
        }),
        (_('Payment Information'), {
            'fields': ('is_paid', 'payment_reference')
        }),
        (_('Guest Information'), {
            'fields': ('name', 'email', 'phone_number')
        }),
        (_('System Info'), {
            'fields': ('booking_reference', 'created_at')
        }),
    )

    def get_user(self, obj):
        if obj.user:
            return obj.user
        return "Guest"
    get_user.short_description = 'User'

    def hotel_name(self, obj):
        return obj.room.hotel.name if obj.room and obj.room.hotel else "-"
    hotel_name.short_description = 'Hotel'

    def colored_payment_status(self, obj):
        """Show payment status with color badges."""
        if obj.is_paid:
            return format_html('<span style="color: green; font-weight: bold;">✔ Paid</span>')
        return format_html('<span style="color: red; font-weight: bold;">✘ Unpaid</span>')
    colored_payment_status.short_description = 'Payment Status'

    def total_amount_display(self, obj):
        return f"₦{obj.total_amount:,.2f}"
    total_amount_display.short_description = 'Total Amount'

    def hotel_revenue_display(self, obj):
        return obj.hotel_revenue
    hotel_revenue_display.short_description = 'Hotel Revenue'
