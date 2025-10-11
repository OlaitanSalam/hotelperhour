from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from bookings.models import Booking, BookingDuration
from .serializers import BookingSerializer, BookingDurationSerializer
from .permissions import IsBookingOwnerOrHotelOwner
from django.utils import timezone
from hotels.models import Room
from rest_framework import status
from django.contrib.contenttypes.models import ContentType

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated, IsBookingOwnerOrHotelOwner]
    lookup_field = 'booking_reference'

    def get_queryset(self):
        if self.request.user.is_hotel_owner:
            return Booking.objects.filter(room__hotel__owner=self.request.user)
        user_content_type = ContentType.objects.get_for_model(self.request.user)
        return Booking.objects.filter(
            content_type=user_content_type,
            object_id=self.request.user.id
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='check-availability/(?P<room_id>\d+)')
    def check_availability(self, request, room_id=None):
        check_in_str = request.query_params.get('check_in')
        duration = request.query_params.get('duration')
        if not (check_in_str and duration):
            return Response({'error': 'Missing parameters'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            check_in = timezone.datetime.fromisoformat(check_in_str)
            check_out = check_in + timezone.timedelta(hours=int(duration))
            room = Room.objects.get(id=room_id)
            
            # First check if room is manually marked as unavailable
            if not room.is_available:
                return Response({
                    'available': False,
                    'message': 'This room is currently not available for booking.',
                    'available_units': 0,
                    'total_units': room.total_units
                })
            
            # Then check unit availability
            available_units = room.get_available_units(check_in, check_out)
            return Response({
                'available': available_units > 0,
                'available_units': available_units,
                'total_units': room.total_units,
                'message': f'{available_units} unit(s) available for this period' if available_units > 0 
                          else 'No units available for this period'
            })
        except ValueError:
            return Response({'error': 'Invalid input'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, booking_reference=None):
        booking = self.get_object()
        if booking.is_paid:
            return Response({'error': 'Cannot cancel paid booking'}, status=status.HTTP_403_FORBIDDEN)
        booking.delete()
        return Response({'success': 'Booking cancelled'})

class BookingDurationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BookingDuration.objects.all()
    serializer_class = BookingDurationSerializer
    permission_classes = [permissions.AllowAny]  # Public for listing durations