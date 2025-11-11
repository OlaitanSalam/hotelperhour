from django import forms
from .models import Hotel, Room, ExtraService
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from .models import Review, AppFeedback, HotelImage, Amenity, HotelPolicy, DURATION_MODE_CHOICES


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
    duration_mode = forms.ChoiceField(
        choices=DURATION_MODE_CHOICES,
        initial='all',
        widget=forms.RadioSelect,  # This will be hidden by our custom JS
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If we have an instance with saved blackout times, populate the form fields
        if self.instance and self.instance.pk:
            if self.instance.blackout_start and self.instance.blackout_end:
                # Set the hidden fields (source of truth)
                self.initial['blackout_start'] = self.instance.blackout_start
                self.initial['blackout_end'] = self.instance.blackout_end
                
                # Convert and set UI fields for start time
                hour = self.instance.blackout_start.hour
                minute = self.instance.blackout_start.minute
                if hour == 0:  # Midnight
                    self.initial['blackout_start_hour'] = '12'
                    self.initial['blackout_start_period'] = 'AM'
                elif hour < 12:  # AM
                    self.initial['blackout_start_hour'] = f"{hour:02d}"
                    self.initial['blackout_start_period'] = 'AM'
                elif hour == 12:  # Noon
                    self.initial['blackout_start_hour'] = '12'
                    self.initial['blackout_start_period'] = 'PM'
                else:  # PM
                    self.initial['blackout_start_hour'] = f"{hour-12:02d}"
                    self.initial['blackout_start_period'] = 'PM'
                self.initial['blackout_start_minute'] = f"{minute:02d}"

                # Convert and set UI fields for end time
                hour = self.instance.blackout_end.hour
                minute = self.instance.blackout_end.minute
                if hour == 0:  # Midnight
                    self.initial['blackout_end_hour'] = '12'
                    self.initial['blackout_end_period'] = 'AM'
                elif hour < 12:  # AM
                    self.initial['blackout_end_hour'] = f"{hour:02d}"
                    self.initial['blackout_end_period'] = 'AM'
                elif hour == 12:  # Noon
                    self.initial['blackout_end_hour'] = '12'
                    self.initial['blackout_end_period'] = 'PM'
                else:  # PM
                    self.initial['blackout_end_hour'] = f"{hour-12:02d}"
                    self.initial['blackout_end_period'] = 'PM'
                self.initial['blackout_end_minute'] = f"{minute:02d}"
            else:
                # If no blackout times set, initialize UI fields to empty
                self.initial.update({
                    'blackout_start_hour': '',
                    'blackout_start_minute': '',
                    'blackout_start_period': '',
                    'blackout_end_hour': '',
                    'blackout_end_minute': '',
                    'blackout_end_period': ''
                })
    # Hidden fields for actual blackout times (source of truth)
    blackout_start = forms.TimeField(required=False, widget=forms.HiddenInput())
    blackout_end = forms.TimeField(required=False, widget=forms.HiddenInput())
    
    # UI fields for time selection (these don't map directly to model)
    blackout_start_hour = forms.ChoiceField(
        choices=[("", "-")] + [(f"{h:02d}", f"{h:02d}") for h in range(1, 13)],
        label="Start Hour",
        required=False
    )
    blackout_start_minute = forms.ChoiceField(
        choices=[("", "-"), ("00", "00"), ("30", "30")],
        label="Minute",
        required=False
    )
    blackout_start_period = forms.ChoiceField(
        choices=[("", "-"), ("AM", "AM"), ("PM", "PM")],
        label="AM/PM",
        required=False
    )

    blackout_end_hour = forms.ChoiceField(
        choices=[("", "-")] + [(f"{h:02d}", f"{h:02d}") for h in range(1, 13)],
        label="End Hour",
        required=False
    )
    blackout_end_minute = forms.ChoiceField(
        choices=[("", "-"), ("00", "00"), ("30", "30")],
        label="Minute",
        required=False
    )
    blackout_end_period = forms.ChoiceField(
        choices=[("", "-"), ("AM", "AM"), ("PM", "PM")],
        label="AM/PM",
        required=False
    )

    class Meta:
        model = Hotel
        fields = (
            'name', 'address', 'city', 'suburb',
            'hotel_phone', 'hotel_email', 'description','duration_mode',
            'latitude', 'longitude', 'image',
            'account_number', 'account_name', 'bank_name', 'amenities','blackout_start', 'blackout_end',
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
    
    def clean(self):
        cleaned_data = super().clean()
        duration_mode = cleaned_data.get('duration_mode')
    
        # Get all UI blackout fields
        start_hour = cleaned_data.get('blackout_start_hour')
        start_min = cleaned_data.get('blackout_start_minute')
        start_period = cleaned_data.get('blackout_start_period')
        end_hour = cleaned_data.get('blackout_end_hour')
        end_min = cleaned_data.get('blackout_end_minute')
        end_period = cleaned_data.get('blackout_end_period')

        # Check if any fields are empty strings (the "-" option)
        has_empty = any(val == "" for val in [start_hour, start_min, start_period, 
                                            end_hour, end_min, end_period])

        # If we're clearing the blackout times or have any empty fields
        if has_empty or not any([start_hour, start_min, start_period, end_hour, end_min, end_period]):
            cleaned_data['blackout_start'] = None
            cleaned_data['blackout_end'] = None
            return cleaned_data

        # Only process if all fields have actual values
        if all([start_hour, start_min, start_period, end_hour, end_min, end_period]):
            from datetime import time
            try:
                # Convert to 24h and create time objects
                start_24 = self._to_24h(start_hour, start_period)
                end_24 = self._to_24h(end_hour, end_period)
                
                start_time = time(int(start_24), int(start_min))
                end_time = time(int(end_24), int(end_min))
                
                # Validate that times are different
                if start_time == end_time:
                    raise ValidationError("Blackout start and end times cannot be the same.")
                
                # Set the hidden fields (source of truth)
                cleaned_data['blackout_start'] = start_time
                cleaned_data['blackout_end'] = end_time
            except (ValueError, TypeError):
                raise ValidationError("Invalid time format submitted.")
            
        return cleaned_data

    def _to_24h(self, hour, period):
        h = int(hour)
        if period == "PM" and h != 12:
            h += 12
        if period == "AM" and h == 12:
            h = 0
        return h



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
            'price_per_hour': forms.NumberInput(attrs={
                'placeholder': 'e.g., ₦5,000 (required for 3, 6, 9 hour bookings)',
                'step': '0.01'
            }),
            'twelve_hour_price': forms.NumberInput(attrs={
                'placeholder': 'e.g., ₦50,000 (fixed price for 12 hours)',
                'step': '0.01'
            }),
            'twenty_four_hour_price': forms.NumberInput(attrs={
                'placeholder': 'e.g., ₦90,000 (fixed price for 24 hours)',
                'step': '0.01'
            }),
        }

    def clean_room_type(self):
        room_type = self.cleaned_data.get('room_type')
        return room_type.title() if room_type else room_type
    
    def clean(self):
        """
        Context-aware validation based on parent hotel's duration mode.
        Handles both creation (hotel doesn't exist yet) and editing cases.
        """
        cleaned_data = super().clean()
        price_per_hour = cleaned_data.get('price_per_hour')
        twelve_hour_price = cleaned_data.get('twelve_hour_price')
        twenty_four_hour_price = cleaned_data.get('twenty_four_hour_price')
        
        # ========== GET HOTEL MODE ==========
        hotel_mode = 'all'  # Default fallback
        
        # Method 1: Try to get from POST data directly (for creation)
        if hasattr(self, 'data') and 'duration_mode' in self.data:
            hotel_mode = self.data.get('duration_mode', 'all')
        
        # Method 2: Try to get from existing instance (for editing)
        elif hasattr(self, 'instance') and self.instance.hotel_id:
            hotel_mode = self.instance.hotel.duration_mode
        
        # Method 3: Try to get from parent form (if available)
        elif hasattr(self, 'parent_form') and self.parent_form:
            if hasattr(self.parent_form, 'cleaned_data') and self.parent_form.cleaned_data:
                hotel_mode = self.parent_form.cleaned_data.get('duration_mode', 'all')
            elif hasattr(self.parent_form, 'data') and 'duration_mode' in self.parent_form.data:
                hotel_mode = self.parent_form.data.get('duration_mode', 'all')
        
        # ========== VALIDATION BASED ON HOTEL MODE ==========
        
        if hotel_mode == 'all':
            # Must have hourly rate
            if not price_per_hour:
                self.add_error('price_per_hour', 
                    'Hourly rate is required when your hotel accepts all durations (3, 6, 9 hours).')
            else:
                # Validate 12-hour discount (if set)
                if twelve_hour_price and twelve_hour_price >= price_per_hour * 12:
                    self.add_error('twelve_hour_price', 
                        f'Must be less than ₦{price_per_hour * 12:,.2f} (12 × ₦{price_per_hour:,.2f}) to offer a discount.')
                
                # Validate 24-hour discount (if set)
                if twenty_four_hour_price and twenty_four_hour_price >= price_per_hour * 24:
                    self.add_error('twenty_four_hour_price', 
                        f'Must be less than ₦{price_per_hour * 24:,.2f} (24 × ₦{price_per_hour:,.2f}) to offer a discount.')
        
        elif hotel_mode == '12_only':
            # Must have 12-hour price
            if not twelve_hour_price:
                self.add_error('twelve_hour_price', 
                    'Your hotel only accepts 12-hour bookings. You must set a 12-hour price.')
            
            # Hourly rate is optional but show helpful message
            if price_per_hour:
                # Don't add error, just informational
                pass
        
        elif hotel_mode == '24_only':
            # Must have 24-hour price
            if not twenty_four_hour_price:
                self.add_error('twenty_four_hour_price', 
                    'Your hotel only accepts 24-hour bookings. You must set a 24-hour price.')
            
            # Hourly rate is optional
            if price_per_hour:
                # Don't add error, just informational
                pass
        
        elif hotel_mode == '12_and_24':
            # Must have both 12 and 24-hour prices
            if not twelve_hour_price:
                self.add_error('twelve_hour_price', 
                    'Your hotel requires 12-hour pricing. Please set a 12-hour rate.')
            
            if not twenty_four_hour_price:
                self.add_error('twenty_four_hour_price', 
                    'Your hotel requires 24-hour pricing. Please set a 24-hour rate.')
        
        return cleaned_data
    
    def add_warning_message(self, message):
        """Helper to add non-blocking warning messages"""
        if not hasattr(self, '_warnings'):
            self._warnings = []
        self._warnings.append(message)


class ExtraServiceForm(forms.ModelForm):
    class Meta:
        model = ExtraService
        fields = ('name', 'price')

    def clean_name(self):
        name = self.cleaned_data.get('name')
        return name.title() if name else name  # Title case for service name

# ========== CUSTOM FORMSET WITH PARENT FORM INJECTION ==========
class RoomFormSetWithParent(inlineformset_factory(
    Hotel,
    Room,
    form=RoomForm,
    fields=('room_type', 'price_per_hour', 'description','capacity', 'total_units', 'image', 'twelve_hour_price', 'twenty_four_hour_price'),
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)):
    def __init__(self, *args, **kwargs):
        self.parent_form = kwargs.pop('parent_form', None)
        super().__init__(*args, **kwargs)
    
    def _construct_form(self, i, **kwargs):
        form = super()._construct_form(i, **kwargs)
        # Inject parent form reference into each room form
        form.parent_form = self.parent_form
        return form

    def clean(self):
        super().clean()
        # Ensure parent form data is available to all forms during validation
        if self.parent_form and hasattr(self.parent_form, 'cleaned_data'):
            for form in self.forms:
                form.parent_form = self.parent_form

# Use the custom formset
RoomFormSet = RoomFormSetWithParent

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