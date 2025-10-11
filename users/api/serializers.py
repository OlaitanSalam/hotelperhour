from rest_framework import serializers
from users.models import CustomUser
from customers.models import Customer

class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'full_name', 'phone_number', 'is_hotel_owner', 
                 'is_active', 'password', 'confirm_password']
        read_only_fields = ['is_active']
        extra_kwargs = {
            'email': {'required': True},
            'full_name': {'required': True},
            'phone_number': {'required': True}
        }

    def create(self, validated_data):
        # Enforce password confirmation when provided
        confirm = validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')
        if confirm is not None and password != confirm:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})

        user = CustomUser(**validated_data)
        user.set_password(password)
        user.is_hotel_owner = True  # Set this by default for CustomUser
        user.save()
        return user

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)
        return super().update(instance, validated_data)
    
    def validate_email(self, value):
        if Customer.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered as a customer. Please use a different email.")
        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()