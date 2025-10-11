from rest_framework import serializers
from customers.models import Customer, LoyaltyRule
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from users.models import CustomUser

class LoyaltyRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyRule
        fields = ['id', 'points_per_percent', 'max_discount_percentage', 'min_points_to_use', 'active']
        read_only_fields = ['id']  # Auto-generated

class CustomerSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)  # For create/update, not shown in output
    confirm_password = serializers.CharField(write_only=True, required=False)  # Validation only

    class Meta:
        model = Customer
        fields = ['id', 'email', 'full_name', 'username', 'phone_number', 'is_active', 'date_joined', 'loyalty_points', 'password', 'confirm_password']
        read_only_fields = ['id', 'date_joined', 'is_active', 'loyalty_points']  # Protect auto/calculated fields

    def validate(self, data):
        # Password validation (like your CustomerCreationForm)
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
    # Use manager to create with hashed password (mirrors customer_register)
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)  # Remove password from validated_data
        customer = Customer.objects.create_customer(
            password=password,
            **validated_data  # Includes email, full_name, etc.
        )
        customer.is_active = False  # Require activation
        return customer
    

    def update(self, instance, validated_data):
        # Handle partial updates (e.g., profile edit)
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    
    def validate_email(self, value):
        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered as a hotel owner. Please use a different email.")
        if Customer.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A customer with this email already exists.")
        return value.lower()