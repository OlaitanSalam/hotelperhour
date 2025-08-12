# customers/forms.py
from django import forms
from .models import Customer
from django.contrib.auth.forms import UserCreationForm

class CustomerCreationForm(UserCreationForm):
    email = forms.EmailField()
    full_name = forms.CharField(max_length=255)
    phone_number = forms.CharField(max_length=20)

    class Meta:
        model = Customer
        fields = ('email', 'full_name', 'username', 'phone_number', 'password1', 'password2')

    def clean_email(self):
        return self.cleaned_data['email'].lower()

    def clean_username(self):
        return self.cleaned_data['username'].lower()

    def clean_full_name(self):
        return self.cleaned_data['full_name'].title()
    

class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['full_name', 'phone_number', 'username']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Enter your full name', 'class': 'form-control', 'autocomplete': 'name'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'Enter your phone number', 'class': 'form-control', 'autocomplete': 'tel'}),
            'username': forms.TextInput(attrs={'placeholder': 'Enter your username', 'class': 'form-control', 'autocomplete': 'username'}),
        }

class CustomerLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))