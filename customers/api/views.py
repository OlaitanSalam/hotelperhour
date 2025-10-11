# Update customers/api/views.py with this complete file
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, extend_schema_view
from customers.models import Customer, LoyaltyRule
from .serializers import CustomerSerializer, LoyaltyRuleSerializer
from .permissions import IsCustomerOwnerOrAdmin, IsAdminForLoyaltyRule
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

@extend_schema_view(
    activate=extend_schema(parameters=[
        OpenApiParameter('uidb64', OpenApiTypes.STR, description='Base64 encoded user id'),
        OpenApiParameter('token', OpenApiTypes.STR, description='Password reset / activation token'),
    ]),
    reset_confirm=extend_schema(parameters=[
        OpenApiParameter('uidb64', OpenApiTypes.STR, description='Base64 encoded user id'),
        OpenApiParameter('token', OpenApiTypes.STR, description='Password reset token'),
    ]),
)
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsCustomerOwnerOrAdmin]
    lookup_field = 'email'
    lookup_value_regex = '[^/]+'

    def get_permissions(self):
        if self.action in ['register', 'activate']:
            return []
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        # For unauthenticated requests to public endpoints
        if not user.is_authenticated:
            return Customer.objects.none()
            
        # Handle SimpleLazyObject
        actual_user = user._wrapped if hasattr(user, '_wrapped') else user
        
        # Superuser can see all
        if actual_user.is_superuser:
            return Customer.objects.all()
        
        # For Customers, only return their own record
        if hasattr(actual_user, 'is_customer') and actual_user.is_customer:
            return Customer.objects.filter(email=actual_user.email)
            
        # Staff can see all but can't modify
        if actual_user.is_staff:
            return Customer.objects.all()
            
        # For other authenticated users, return none
        return Customer.objects.none()

    def perform_create(self, serializer):
        customer = serializer.save()
        current_site = get_current_site(self.request)
        subject = 'Activate Your Hotel per Hour Customer Account'
        html_message = render_to_string('customers/activation_email.html', {
            'user': customer,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(customer.pk)),
            'token': default_token_generator.make_token(customer),
        })
        plain_message = strip_tags(html_message)
        email = EmailMultiAlternatives(subject, plain_message, settings.DEFAULT_FROM_EMAIL, [customer.email])
        email.attach_alternative(html_message, "text/html")
        email.send()

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'message': 'Registration successful. Check your email for activation.'}, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[
            OpenApiParameter('uidb64', OpenApiTypes.STR, description='Base64 encoded user id'),
            OpenApiParameter('token', OpenApiTypes.STR, description='Password reset / activation token'),
        ]
    )
    @action(detail=False, methods=['get'], url_path='activate/(?P<uidb64>[^/.]+)/(?P<token>[^/.]+)')
    def activate(self, request, uidb64=None, token=None):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            customer = Customer.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, Customer.DoesNotExist):
            return Response({'error': 'Invalid activation link'}, status=status.HTTP_400_BAD_REQUEST)
        
        if default_token_generator.check_token(customer, token):
            customer.is_active = True
            customer.save()
            return Response({'message': 'Account activated successfully'})
        return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='password-reset')
    def password_reset(self, request, email=None):
        customer = self.get_object()
        token = default_token_generator.make_token(customer)
        uid = urlsafe_base64_encode(force_bytes(customer.pk))
        reset_url = request.build_absolute_uri(f'/api/v1/customers/customers/{uid}/{token}/reset-confirm/')
        subject = 'Password Reset'
        message = f"Hello {customer.full_name},\n\nClick to reset: {reset_url}"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [customer.email])
        return Response({'message': 'Password reset email sent'})

    @extend_schema(
        parameters=[
            OpenApiParameter('uidb64', OpenApiTypes.STR, description='Base64 encoded user id'),
            OpenApiParameter('token', OpenApiTypes.STR, description='Password reset token'),
        ]
    )
    @action(detail=False, methods=['post'], url_path='(?P<uidb64>[^/.]+)/(?P<token>[^/.]+)/reset-confirm')
    def reset_confirm(self, request, uidb64=None, token=None):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            customer = Customer.objects.get(pk=uid)
        except:
            return Response({'error': 'Invalid link'}, status=status.HTTP_400_BAD_REQUEST)
        
        if default_token_generator.check_token(customer, token):
            password = request.data.get('password')
            confirm_password = request.data.get('confirm_password')
            if password and password == confirm_password:
                customer.set_password(password)
                customer.save()
                return Response({'message': 'Password reset successful'})
            return Response({'error': 'Passwords do not match'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

class LoyaltyRuleViewSet(viewsets.ModelViewSet):
    queryset = LoyaltyRule.objects.all()
    serializer_class = LoyaltyRuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminForLoyaltyRule]