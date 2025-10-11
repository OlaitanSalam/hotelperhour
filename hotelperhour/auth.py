from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from customers.models import Customer
from django.contrib.auth import authenticate

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Accept either 'username' or 'email' from client payload; normalize input
        raw_username = attrs.get('username')
        raw_email = attrs.get('email')
        email = (raw_username or raw_email or '').strip().lower()
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError({
                'non_field_errors': ['Email and password are required.']
            })

        # Try case-insensitive lookup by email
        try:
            customer = Customer.objects.get(email__iexact=email)
        except Customer.DoesNotExist:
            # If not found, try matching by username field as a fallback
            try:
                customer = Customer.objects.get(username__iexact=email)
            except Customer.DoesNotExist:
                raise serializers.ValidationError({
                    'non_field_errors': ['No account found with this email.']
                })

        if not customer.is_active:
            raise serializers.ValidationError({
                'non_field_errors': ['Your account is not activated. Please check your email.']
            })

        # First try authenticate() which will use configured auth backends
        user = authenticate(request=self.context.get('request'), username=customer.email, password=password)

        # If authenticate failed, fallback to direct password check against model
        if not user:
            if not customer.check_password(password):
                raise serializers.ValidationError({
                    'non_field_errors': ['Invalid credentials']
                })
            # treat customer as authenticated
            user = customer

        # Generate token for authenticated customer
        refresh = RefreshToken.for_user(user)

        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_type': 'customer',
            'email': user.email,
            'full_name': user.full_name,
            'id': user.id,
            'loyalty_points': getattr(user, 'loyalty_points', 0)
        }

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add customer-specific claims
        token['email'] = user.email
        token['user_type'] = 'customer'
        token['full_name'] = user.full_name
        token['loyalty_points'] = user.loyalty_points
        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer