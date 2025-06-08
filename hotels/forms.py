from django import forms
from .models import Hotel, Room
from django.forms import formset_factory, inlineformset_factory
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

class HotelForm(forms.ModelForm):
    image = forms.ImageField(
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            lambda f: (f.size <= 2*1024*1024 or ValidationError("Image must be under 2MB"))
        ],
        required=False
    )
    latitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    longitude = forms.FloatField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Hotel
        fields = ('name', 'address', 'hotel_phone', 'hotel_email', 'description', 'latitude', 'longitude', 'image',)
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }
    def clean_name(self):
        # Convert hotel name to title case (e.g., "Grand Hotel")
        return self.cleaned_data['name'].title()

    def clean_address(self):
        # Convert address to title case (e.g., "123 Main St, Lagos")
        return self.cleaned_data['address'].title()

    def clean_hotel_email(self):
        # Convert hotel email to lowercase (e.g., "hotel@example.com")
        return self.cleaned_data['hotel_email'].lower()

class RoomForm(forms.ModelForm):
    image = forms.ImageField(
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            lambda f: (f.size <= 2*1024*1024 or ValidationError("Image must be under 2MB"))
        ],
        required=False
    )
    class Meta:
        model = Room
        fields = ('room_type', 'price_per_hour', 'description', 'capacity', 'image',)
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2, 'cols': 30}),
        }

    def clean_room_type(self):
        # Convert room type to title case (e.g., "Deluxe Suite")
        return self.cleaned_data['room_type'].title()

RoomFormSet = inlineformset_factory(
    Hotel,
    Room,
    fields=('room_type', 'price_per_hour', 'description', 'capacity', 'image'),
    extra=0,
    can_delete=True
)
class DateRangeForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))