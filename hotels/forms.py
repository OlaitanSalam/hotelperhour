from django import forms
from .models import Hotel, Room, ExtraService
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from .models import Review, AppFeedback, HotelImage, Amenity, HotelPolicy


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
        required=True
    )
    latitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    longitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Hotel
        fields = (
            'name', 'address', 'city', 'suburb',
            'hotel_phone', 'hotel_email', 'description',
            'latitude', 'longitude', 'image',
            'account_number', 'account_name', 'bank_name', 'amenities'
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
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
        required=True
    )

    class Meta:
        model = Room
        fields = ('room_type', 'total_units', 'price_per_hour', 'description', 'capacity', 'image', 'twelve_hour_price', 'twenty_four_hour_price')
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

    def clean_name(self):
        name = self.cleaned_data.get('name')
        return name.title() if name else name  # Title case for service name


RoomFormSet = inlineformset_factory(
    Hotel,
    Room,
    fields=('room_type', 'price_per_hour', 'description','capacity', 'total_units', 'image', 'twelve_hour_price', 'twenty_four_hour_price'),
    extra=1,
    can_delete=True,
    min_num=1,  # Require at least one room
    validate_min=True
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

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['name', 'email', 'review_text', 'rating']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name *'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address *'}),
            'review_text': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your Feedback *', 'rows': 4}),
            'rating': forms.Select(attrs={'class': 'form-select'}),
        }

class AppFeedbackForm(forms.ModelForm):
    class Meta:
        model = AppFeedback
        fields = ['name', 'email', 'review_text', 'rating']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name *'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address *'}),
            'review_text': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your Feedback *', 'rows': 4}),
            'rating': forms.Select(attrs={'class': 'form-select'}),
        }

class HotelImageForm(forms.ModelForm):
    image = forms.ImageField(
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            validate_image_size  
        ],
        required=True
    )

    class Meta:
        model = HotelImage
        fields = ('image', 'alt_text')
        widgets = {
            'alt_text': forms.TextInput(attrs={'placeholder': 'e.g., Hotel lobby view'})
        }

HotelImageFormSet = inlineformset_factory(
    Hotel,
    HotelImage,
    form=HotelImageForm,
    fields=('image', 'alt_text'),
    extra=1,  # Start with 1 empty form
    can_delete=True,
    max_num=10,  # Limit to 10 images
    validate_max=True  # Enforce max_num
)

class HotelPolicyForm(forms.ModelForm):
    class Meta:
        model = HotelPolicy
        fields = ('policy_text',)
        widgets = {
            'policy_text': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'e.g., Check-in: 2:00 PM'}),
        }

    def clean_policy_text(self):
        policy_text = self.cleaned_data.get('policy_text')
        if policy_text:
            # Capitalize first letter of each sentence for readability
            return '. '.join(sentence.capitalize() for sentence in policy_text.split('. ') if sentence)
        return policy_text

HotelPolicyFormSet = inlineformset_factory(
    Hotel,
    HotelPolicy,
    form=HotelPolicyForm,
    extra=1,
    can_delete=True,
    max_num=10,
    validate_max=True,
)