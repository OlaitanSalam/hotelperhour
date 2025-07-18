from django import forms
from .models import Booking, BookingDuration
from hotels.models import ExtraService
from django.utils import timezone

class BookingForm(forms.ModelForm):
    check_in_date = forms.DateField(label="Check-in Date", widget=forms.DateInput(attrs={'type': 'date'}))
    check_in_hour = forms.ChoiceField(label="Check-in Time", choices=[
        ('0', '12:00 AM'), ('1', '1:00 AM'), ('2', '2:00 AM'), ('3', '3:00 AM'),
        ('4', '4:00 AM'), ('5', '5:00 AM'), ('6', '6:00 AM'), ('7', '7:00 AM'),
        ('8', '8:00 AM'), ('9', '9:00 AM'), ('10', '10:00 AM'), ('11', '11:00 AM'),
        ('12', '12:00 PM'), ('13', '1:00 PM'), ('14', '2:00 PM'), ('15', '3:00 PM'),
        ('16', '4:00 PM'), ('17', '5:00 PM'), ('18', '6:00 PM'), ('19', '7:00 PM'),
        ('20', '8:00 PM'), ('21', '9:00 PM'), ('22', '10:00 PM'), ('23', '11:00 PM'),
    ])
    duration = forms.ChoiceField(label="Duration", choices=lambda: [(d.hours, f"{d.hours} hours") for d in BookingDuration.objects.all()])
    name = forms.CharField(max_length=100, label="Full Name")
    email = forms.EmailField(label="Email Address")
    phone_number = forms.CharField(max_length=15, label="Phone Number")
    extras = forms.ModelMultipleChoiceField(
        queryset=ExtraService.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Booking
        fields = ['check_in_date', 'check_in_hour', 'duration', 'name', 'email', 'phone_number', 'extras']

    def __init__(self, *args, **kwargs):
        room = kwargs.pop('room', None)
        super().__init__(*args, **kwargs)
        if room:
            self.fields['extras'].queryset = ExtraService.objects.filter(hotel=room.hotel)

    def clean_name(self):
        return self.cleaned_data['name'].title()

    def clean_email(self):
        return self.cleaned_data['email'].lower()

    def clean(self):
        cleaned_data = super().clean()
        check_in_date = cleaned_data.get('check_in_date')
        check_in_hour = cleaned_data.get('check_in_hour')
        duration = cleaned_data.get('duration')

        if check_in_date and check_in_hour and duration:
            check_in = timezone.datetime.combine(check_in_date, timezone.datetime.strptime(check_in_hour, "%H").time())
            duration = int(duration)
            check_out = check_in + timezone.timedelta(hours=duration)

            if check_out <= check_in:
                raise forms.ValidationError("Invalid booking duration.")
            if duration < 3:
                raise forms.ValidationError("Minimum booking duration is 3 hours.")

            cleaned_data['check_in'] = check_in
            cleaned_data['check_out'] = check_out
            cleaned_data['duration'] = duration
        return cleaned_data