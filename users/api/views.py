from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, extend_schema_view
from users.models import CustomUser
from .serializers import CustomUserSerializer
from .permissions import IsOwnerOrAdmin
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings

@extend_schema_view(
    activate=extend_schema(parameters=[
        OpenApiParameter('uidb64', OpenApiTypes.STR, description='Base64 encoded user id'),
        OpenApiParameter('token', OpenApiTypes.STR, description='Activation token'),
    ]),
    reset_confirm=extend_schema(parameters=[
        OpenApiParameter('uidb64', OpenApiTypes.STR, description='Base64 encoded user id'),
        OpenApiParameter('token', OpenApiTypes.STR, description='Password reset token'),
    ]),
)
class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsOwnerOrAdmin]
    lookup_field = 'email'
    lookup_value_regex = '[^/]+'

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return CustomUser.objects.none()
        
        if user.is_superuser:
            return CustomUser.objects.all()
        
        return CustomUser.objects.filter(id=user.id)

    def perform_create(self, serializer):
        user = serializer.save()
        current_site = get_current_site(self.request)
        subject = 'Activate Your Hotel per Hour Business Account'
        html_message = render_to_string('users/activation_email.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user),
        })
        plain_message = strip_tags(html_message)
        email = EmailMultiAlternatives(subject, plain_message, settings.DEFAULT_FROM_EMAIL, [user.email])
        email.attach_alternative(html_message, "text/html")
        email.send()

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {'message': 'Registration successful. Check your email for activation.'},
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        parameters=[
            OpenApiParameter('uidb64', OpenApiTypes.STR, description='Base64 encoded user id'),
            OpenApiParameter('token', OpenApiTypes.STR, description='Activation token'),
        ]
    )
    @action(detail=False, methods=['get'], url_path='activate/(?P<uidb64>[^/.]+)/(?P<token>[^/.]+)')
    def activate(self, request, uidb64=None, token=None):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response(
                {'error': 'Invalid activation link'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({'message': 'Account activated successfully'})
        return Response(
            {'error': 'Invalid or expired token'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'], url_path='password-reset')
    def password_reset(self, request, email=None):
        user = self.get_object()
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = request.build_absolute_uri(f'/api/v1/users/{uid}/{token}/reset-confirm/')
        subject = 'Password Reset'
        message = f"Hello {user.full_name},\n\nClick to reset: {reset_url}"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
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
            user = CustomUser.objects.get(pk=uid)
        except:
            return Response(
                {'error': 'Invalid link'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if default_token_generator.check_token(user, token):
            password = request.data.get('password')
            confirm_password = request.data.get('confirm_password')
            if password and password == confirm_password:
                user.set_password(password)
                user.save()
                return Response({'message': 'Password reset successful'})
            return Response(
                {'error': 'Passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_400_BAD_REQUEST
        )