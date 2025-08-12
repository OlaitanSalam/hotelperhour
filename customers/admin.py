from django.contrib import admin
from .models import CustomerManager, Customer , LoyaltyRule
# Register your models here.
admin.site.register(Customer)

class LoyaltyRuleAdmin(admin.ModelAdmin):
    list_display = ('points_per_percent', 'active')
    list_filter = ('active',)  # Filter by active status

admin.site.site_header = 'HotelPerHour Admin'
admin.site.site_title = 'HotelPerHour Admin'
admin.site.index_title = 'Welcome to HotelPerHour Admin'

admin.site.register(LoyaltyRule, LoyaltyRuleAdmin)