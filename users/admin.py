from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from django.utils.html import format_html

class CustomUserAdmin(UserAdmin):
    """
    Custom admin interface for the CustomUser model with 
    hotel owner status and activity indicators
    """
    model = CustomUser
    list_display = ('email', 'full_name', 'phone_number', 
                    'is_hotel_owner', 'is_active', 'is_staff', 
                    'date_joined', 'last_login')
    list_filter = ('is_hotel_owner', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'full_name', 'phone_number')
    list_per_page = 30
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login', 'hotel_count')
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal Info', {
            'fields': ('full_name', 'phone_number')
        }),
        ('Permissions', {
            'fields': ('is_hotel_owner', 'is_active', 'is_staff', 'is_superuser', 
                       'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined')
        }),
        ('Hotel Stats', {
            'fields': ('hotel_count',),
            'classes': ('collapse',)
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'full_name', 'phone_number', 
                       'is_hotel_owner', 'is_active', 'is_staff', 'is_superuser')}
        ),
    )
    
    def hotel_count(self, obj):
        """Display count of hotels owned by this user"""
        count = obj.hotel_set.count()
        return format_html(
            '<a href="/admin/hotels/hotel/?owner__id__exact={}">{}</a> hotels',
            obj.id, count
        )
    hotel_count.short_description = 'Hotels Owned'

admin.site.register(CustomUser, CustomUserAdmin)