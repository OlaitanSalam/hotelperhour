from django import forms
from .models import CustomUser

class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)
    is_hotel_owner = forms.BooleanField(label='Register as Hotel Owner', required=False)

    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'phone_number',)

    def clean_email(self):
        # Convert email to lowercase (e.g., "user@example.com")
        return self.cleaned_data['email'].lower()

    def clean_full_name(self):
        # Convert full name to title case (e.g., "Jane Doe")
        return self.cleaned_data['full_name'].title()

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def clean(self):
        cleaned_data = super().clean()
        is_hotel_owner = cleaned_data.get('is_hotel_owner')
        full_name = cleaned_data.get('full_name')
        phone_number = cleaned_data.get('phone_number')
        if is_hotel_owner and not (full_name and phone_number):
            raise forms.ValidationError("Full name and phone number are required for hotel owners.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_hotel_owner = True  # Automatically set
        if commit:
            user.save()
        return user