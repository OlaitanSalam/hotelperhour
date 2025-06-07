# bookings/forms.py
from django import forms
from .models import Booking

class BookingForm(forms.ModelForm):
    name = forms.CharField(max_length=100, label="Full Name")
    email = forms.EmailField(label="Email Address")
    phone_number = forms.CharField(max_length=15, label="Phone Number")

    class Meta:
        model = Booking
        fields = ['check_in', 'check_out', 'name', 'email', 'phone_number']
        widgets = {
            'check_in': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'check_out': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean_name(self):
        # Convert name to title case (e.g., "John Doe")
        return self.cleaned_data['name'].title()

    def clean_email(self):
        # Convert email to lowercase (e.g., "user@example.com")
        return self.cleaned_data['email'].lower()

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        if check_in and check_out:
            if check_out <= check_in:
                raise forms.ValidationError("Check-out must be after check-in.")
            duration = check_out - check_in
            total_hours = duration.total_seconds() / 3600
            if total_hours < 3:
                raise forms.ValidationError("Minimum booking duration is 3 hours.")
        return cleaned_data