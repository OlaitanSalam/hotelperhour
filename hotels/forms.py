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
        name = self.cleaned_data.get('name')
        return name.title() if name else name

    def clean_address(self):
        address = self.cleaned_data.get('address')
        return address.title() if address else address

    def clean_hotel_email(self):
        email = self.cleaned_data.get('hotel_email')
        if email:
            return email.lower()
        return email  # leave it as None if not provided



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
        fields = ('room_type', 'price_per_hour', 'description', 'capacity', 'image', 'twelve_hour_price', 'twenty_four_hour_price')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2, 'cols': 30}),
            'twelve_hour_price': forms.NumberInput(attrs={'placeholder': 'e.g., ₦50,000 for discounted flat rate'}),
            'twenty_four_hour_price': forms.NumberInput(attrs={'placeholder': 'e.g., ₦100,000 for discounted flat rate'}),
        }

    def clean_room_type(self):
        room_type = self.cleaned_data.get('room_type')
        return room_type.title() if room_type else room_type
    
    def clean(self):
        cleaned_data = super().clean()
        price_per_hour = cleaned_data.get('price_per_hour')
        twelve_hour_price = cleaned_data.get('twelve_hour_price')
        twenty_four_hour_price = cleaned_data.get('twenty_four_hour_price')
        if price_per_hour:
            if twelve_hour_price and twelve_hour_price >= price_per_hour * 12:
                self.add_error('twelve_hour_price', "Must be less than 12 * hourly rate.")
            if twenty_four_hour_price and twenty_four_hour_price >= price_per_hour * 24:
                self.add_error('twenty_four_hour_price', "Must be less than 24 * hourly rate.")
        return cleaned_data



class ExtraServiceForm(forms.ModelForm):
    class Meta:
        model = ExtraService
        fields = ('name', 'price')


RoomFormSet = inlineformset_factory(
    Hotel,
    Room,
    fields=('room_type', 'price_per_hour', 'description', 'capacity', 'image', 'twelve_hour_price', 'twenty_four_hour_price'),
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
