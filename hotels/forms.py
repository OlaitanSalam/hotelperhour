from django import forms
from .models import Hotel, Room, ExtraService
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # 2MB

def validate_image_size(f):
    if f.size > MAX_UPLOAD_SIZE:
        raise ValidationError("Image must be under 2MB")

class HotelForm(forms.ModelForm):
    image = forms.ImageField(
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            validate_image_size
        ],
        required=False
    )
    latitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    longitude = forms.FloatField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Hotel
        fields = (
            'name', 'address', 'city', 'suburb',
            'hotel_phone', 'hotel_email', 'description',
            'latitude', 'longitude', 'image',
            'account_number', 'account_name', 'bank_name'
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_name(self):
        return self.cleaned_data['name'].title()

    def clean_address(self):
        return self.cleaned_data['address'].title()

    def clean_hotel_email(self):
        return self.cleaned_data['hotel_email'].lower()


class RoomForm(forms.ModelForm):
    image = forms.ImageField(
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            validate_image_size
        ],
        required=False
    )

    class Meta:
        model = Room
        fields = ('room_type', 'price_per_hour', 'description', 'capacity', 'image')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2, 'cols': 30}),
        }

    def clean_room_type(self):
        return self.cleaned_data['room_type'].title()


class ExtraServiceForm(forms.ModelForm):
    class Meta:
        model = ExtraService
        fields = ('name', 'price')


RoomFormSet = inlineformset_factory(
    Hotel,
    Room,
    fields=('room_type', 'price_per_hour', 'description', 'capacity', 'image'),
    extra=1,
    can_delete=True
)

ExtraServiceFormSet = inlineformset_factory(
    Hotel,
    ExtraService,
    form=ExtraServiceForm,
    fields=('name', 'price'),
    extra=1,
    can_delete=True
)


class DateRangeForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
