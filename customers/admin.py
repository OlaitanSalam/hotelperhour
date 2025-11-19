from django.contrib import admin
from django.utils.html import format_html
from .models import Customer, LoyaltyRule


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'full_name',
        'phone_number',
        'loyalty_points',
        'is_active',
        'is_staff',
        'date_joined',
        'colored_status',
        'favorite_count'
    )
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'full_name', 'phone_number')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined',)
    list_per_page = 25

    fieldsets = (
        ('Personal Info', {
            'fields': ('email', 'full_name', 'username', 'phone_number', 'favorite_hotels')
        }),
        ('Account Details', {
            'fields': ('is_active', 'is_staff', 'password')
        }),
        ('Loyalty Info', {
            'fields': ('loyalty_points',),
        }),
        ('Important Dates', {
            'fields': ('date_joined',),
        }),
    )

    def colored_status(self, obj):
        """Display active status with colored badge."""
        color = "#28a745" if obj.is_active else "#dc3545"
        status = "Active" if obj.is_active else "Inactive"
        return format_html(
            f'<span style="background-color:{color};color:white;padding:3px 8px;border-radius:8px;font-size:0.85em;">{status}</span>'
        )

    colored_status.short_description = "Status"

    def has_delete_permission(self, request, obj=None):
        # Optional: prevent accidental deletion of customers
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        """Auto-hash password if manually entered in admin."""
        raw_password = form.cleaned_data.get("password")
        if raw_password and not raw_password.startswith("pbkdf2_"):
            obj.set_password(raw_password)
        obj.save()

    def favorite_count(self, obj):
        return obj.favorite_hotels.count()
    favorite_count.short_description = "Favorites"


@admin.register(LoyaltyRule)
class LoyaltyRuleAdmin(admin.ModelAdmin):
    list_display = ('points_per_percent', 'max_discount_percentage', 'min_points_to_use', 'active')
    list_filter = ('active',)
    ordering = ('-active',)
    search_fields = ('points_per_percent',)
    actions = None  # Disable bulk actions (optional)

    def has_add_permission(self, request):
        # Optional: allow only one active rule
        return not LoyaltyRule.objects.filter(active=True).exists()

    def save_model(self, request, obj, form, change):
        # Ensure only one active rule at a time
        if obj.active:
            LoyaltyRule.objects.exclude(id=obj.id).update(active=False)
        super().save_model(request, obj, form, change)


# ===== Customize Admin Branding =====
admin.site.site_header = "HotelPerHour Administration"
admin.site.site_title = "HotelPerHour Admin"
admin.site.index_title = "Welcome to the HotelPerHour Control Panel"
