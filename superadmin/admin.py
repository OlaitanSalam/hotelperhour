from django.contrib import admin
from .models import PayoutRecord

@admin.register(PayoutRecord)
class PayoutRecordAdmin(admin.ModelAdmin):
    list_display = [
        'payout_reference', 
        'hotel', 
        'net_payout', 
        'status', 
        'booking_count',
        'period_start',
        'period_end',
        'created_at'
    ]
    list_filter = ['status', 'created_at', 'paid_at']
    search_fields = ['payout_reference', 'hotel__name', 'paystack_transfer_code']
    readonly_fields = [
        'payout_reference', 
        'created_at', 
        'approved_at', 
        'paid_at',
        'approved_by'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('hotel', 'payout_reference', 'status')
        }),
        ('Period', {
            'fields': ('period_start', 'period_end', 'booking_count')
        }),
        ('Financial Details', {
            'fields': ('gross_revenue', 'commission_amount', 'net_payout')
        }),
        ('Status Tracking', {
            'fields': ('created_at', 'approved_at', 'approved_by', 'paid_at')
        }),
        ('Payment Details', {
            'fields': ('paystack_transfer_code', 'paystack_response', 'notes')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('hotel', 'approved_by')
    
    def has_add_permission(self, request):
        # Prevent manual creation in admin (should only be created via the payout dashboard)
        return False