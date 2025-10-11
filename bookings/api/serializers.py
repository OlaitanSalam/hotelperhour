from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from bookings.models import Booking, BookingDuration
from hotels.api.serializers import RoomSerializer, ExtraServiceSerializer
from customers.models import LoyaltyRule, Customer
from hotels.models import Room
from decimal import Decimal
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

class BookingDurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingDuration
        fields = ['id', 'hours']

class BookingSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    extras = ExtraServiceSerializer(many=True, read_only=True)
    user_type = serializers.CharField(source='content_type.model', read_only=True)
    hotel_revenue = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    user_identifier = serializers.SerializerMethodField()
    total_hours = serializers.FloatField(read_only=True)  # Make read_only to avoid input

    class Meta:
        model = Booking
        fields = ['id', 'user_identifier', 'user_type', 'room', 'check_in', 'check_out', 'total_hours', 'is_paid', 'payment_reference', 'name', 'email', 'phone_number', 'created_at', 'booking_reference', 'total_price', 'service_charge', 'total_amount', 'extras', 'discount_applied', 'points_used', 'hotel_revenue']
        read_only_fields = ['user_identifier', 'user_type', 'total_hours', 'is_paid', 'payment_reference', 'created_at', 'booking_reference', 'total_price', 'service_charge', 'total_amount', 'discount_applied', 'points_used', 'hotel_revenue']

    @extend_schema_field(OpenApiTypes.STR)
    def get_user_identifier(self, obj):
        if obj.user:
            return getattr(obj.user, 'email', 'Anonymous')
        return 'Anonymous'

    def validate(self, data):
        required_fields = ['room', 'check_in', 'check_out', 'name', 'phone_number']
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError({field: "This field is required and cannot be empty/null."})
        check_in = data['check_in']
        check_out = data['check_out']
        if check_out <= check_in:
            raise ValidationError({"check_out": "Check-out must be after check-in."})
        
        room = data['room']
        # Check if room is manually marked as unavailable
        if not room.is_available:
            raise ValidationError({"room": "This room category is currently not available for booking."})
            
        # Check unit availability
        available_units = room.get_available_units(check_in, check_out)
        if available_units <= 0:
            raise ValidationError({"room": "No units available in this room category for the selected time period."})
            
        return data

    def create(self, validated_data):
        room = validated_data['room']
        total_hours = (validated_data['check_out'] - validated_data['check_in']).total_seconds() / 3600
        if total_hours in [12, 24] and getattr(room, f"{'twelve' if total_hours == 12 else 'twenty_four'}_hour_price", None):
            room_cost = room.twelve_hour_price if total_hours == 12 else room.twenty_four_hour_price
        else:
            room_cost = room.price_per_hour * Decimal(total_hours)
        extras = validated_data.pop('extras', [])
        extras_cost = sum(extra.price for extra in extras)
        service_charge = room_cost * Decimal('0.10')
        discount_applied = Decimal('0.00')
        points_used = 0
        user = self.context['request'].user if self.context['request'].user.is_authenticated else None
        if user and isinstance(user, Customer):
            rule = LoyaltyRule.objects.filter(active=True).first()
            if rule and rule.min_points_to_use > 0:
                user_points = user.loyalty_points
                if user_points >= rule.min_points_to_use:
                    discount_percentage = min(user_points / rule.points_per_percent, rule.max_discount_percentage)
                    discount_applied = room_cost * (Decimal(discount_percentage) / 100)
                    points_used = int(discount_percentage * rule.points_per_percent)
        total_price = room_cost - discount_applied + extras_cost
        total_amount = total_price + service_charge

        # Handle SimpleLazyObject
        actual_user = user._wrapped if user and hasattr(user, '_wrapped') else user
        content_type = ContentType.objects.get_for_model(actual_user.__class__) if actual_user else None
        object_id = actual_user.id if actual_user else None

        booking = Booking.objects.create(
            content_type=content_type,
            object_id=object_id,
            total_hours=total_hours,
            total_price=total_price,
            service_charge=service_charge,
            total_amount=total_amount,
            discount_applied=discount_applied,
            points_used=points_used,
            **validated_data
        )
        booking.extras.set(extras)
        return booking