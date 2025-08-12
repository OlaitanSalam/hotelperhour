from django.shortcuts import render, redirect
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.contrib.auth import login
from .forms import CustomUserCreationForm
from .models import CustomUser
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.urls import reverse
from django.contrib import messages

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            current_site = get_current_site(request)
            subject = 'Activate Your Hotel per Hour Account'
            html_message = render_to_string('users/activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            plain_message = strip_tags(html_message)
            email = EmailMultiAlternatives(subject, plain_message, settings.DEFAULT_FROM_EMAIL, [user.email])
            email.attach_alternative(html_message, "text/html")
            email.send()
            return redirect('activation_sent')
        else:
            return render(request, 'users/register.html', {'form': form})
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})

def activation_sent(request):
    return render(request, 'users/activation_sent.html')

    

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Your account has been activated. Please log in.")
        return redirect('login')
    return render(request, 'users/activation_invalid.html')



class CustomLoginView(LoginView):
    template_name = 'users/login.html'

    def get_success_url(self):
        if self.request.user.is_hotel_owner:
            return reverse('hotel_dashboard')
        elif self.request.user.is_customer:
            return reverse('customer_dashboard')
        return reverse('home')


def dashboard(request):
    if request.user.is_hotel_owner:
        return redirect('hotel_dashboard')
    return render(request, 'users/dashboard.html')
    
def logout_view(request):
    logout(request)
    return redirect('home')

def unified_logout(request):
    logout(request)
    return redirect('home')


def home(request):
    return render(request, 'home.html')