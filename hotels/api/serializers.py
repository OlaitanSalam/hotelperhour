from rest_framework import serializers
from django.utils import timezone
from hotels.models import Hotel, Room, Amenity, ExtraService, Review, AppFeedback, HotelImage, HotelPolicy

class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'icon_class', 'description']  # Expose all relevant fields

class ExtraServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraService
        fields = ['id', 'name', 'price']

class HotelImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelImage
        fields = ['id', 'image', 'alt_text', 'order']

class HotelPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelPolicy
        fields = ['id', 'policy_text']

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'name', 'email', 'review_text', 'rating', 'created_at', 'is_approved']

class AppFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppFeedback
        fields = ['id', 'name', 'email', 'review_text', 'rating', 'created_at', 'is_approved']

class RoomSerializer(serializers.ModelSerializer):
    available_units = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ['id', 'hotel', 'room_type', 'total_units', 'available_units', 'price_per_hour', 'image', 'description', 'capacity', 'is_available', 'twelve_hour_price', 'twenty_four_hour_price']
        read_only_fields = ['hotel']  # Prevent changing hotel via API

    def get_available_units(self, obj):
        # If request includes check_in and check_out parameters, return available units for that period
        request = self.context.get('request')
        if request and request.query_params.get('check_in') and request.query_params.get('check_out'):
            try:
                check_in = timezone.datetime.fromisoformat(request.query_params.get('check_in'))
                check_out = timezone.datetime.fromisoformat(request.query_params.get('check_out'))
                return obj.get_available_units(check_in, check_out)
            except (ValueError, TypeError):
                pass
        return obj.total_units  # Default to total units if no date range specified

class HotelSerializer(serializers.ModelSerializer):
    amenities = AmenitySerializer(many=True, read_only=True)  # Nested
    extras = ExtraServiceSerializer(many=True, read_only=True)  # Nested
    images = HotelImageSerializer(many=True, read_only=True)  # Nested
    policies = HotelPolicySerializer(many=True, read_only=True)  # Nested
    reviews = ReviewSerializer(many=True, read_only=True)  # Nested
    rooms = RoomSerializer(many=True, read_only=True)  # Nested for rooms in hotel

    class Meta:
        model = Hotel
        fields = ['id', 'name', 'owner', 'address', 'city', 'suburb', 'hotel_phone', 'hotel_email', 'description', 'image', 'latitude', 'longitude', 'is_approved', 'created_at', 'slug', 'account_number', 'account_name', 'bank_name', 'amenities', 'rooms', 'extras', 'images', 'policies', 'reviews']
        read_only_fields = ['owner', 'slug', 'created_at', 'is_approved']  # Protect sensitive/auto fields