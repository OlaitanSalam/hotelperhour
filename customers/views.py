from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from urllib.parse import urlencode
from users.models import CustomUser
from .forms import CustomerCreationForm, CustomerLoginForm
from .models import Customer
from bookings.models import Booking
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import authenticate
from .forms import CustomerProfileForm
from django.core.exceptions import ValidationError
# customers/views.py
from django.conf import settings
from django.core.mail import send_mail
from django.views.generic import FormView
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.urls import reverse_lazy


def customer_register(request):
    if request.method == 'POST':
        form = CustomerCreationForm(request.POST)
        if form.is_valid():
            # Use the manager to create customer with hashed password
            customer = Customer.objects.create_customer(
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1'],
                full_name=form.cleaned_data['full_name'],
                phone_number=form.cleaned_data['phone_number'],
                username=form.cleaned_data['username']
            )
            customer.is_active = False
            customer.save()
            current_site = get_current_site(request)
            subject = 'Activate Your Hotel per Hour Customer Account'
            html_message = render_to_string('customers/activation_email.html', {
                'user': customer,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(customer.pk)),
                'token': default_token_generator.make_token(customer),
            })
            plain_message = strip_tags(html_message)
            email = EmailMultiAlternatives(subject, plain_message, settings.DEFAULT_FROM_EMAIL, [customer.email])
            email.attach_alternative(html_message, "text/html")
            email.send()
            messages.success(request, "Registration successful. Please check your email to activate your account.")
            return redirect('customer_activation_sent')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerCreationForm()
    return render(request, 'customers/register.html', {'form': form})

def customer_activation_sent(request):
    return render(request, 'customers/activation_sent.html')

def customer_activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        customer = Customer.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Customer.DoesNotExist):
        customer = None
    
    if customer is not None and default_token_generator.check_token(customer, token):
        customer.is_active = True
        customer.save()
        messages.success(request, "Your account has been activated. Please log in.")
        return redirect('customer_login')
    
    messages.error(request, "Activation link is invalid or has expired.")
    return render(request, 'customers/activation_invalid.html')



def customer_login(request):
    if request.method == 'POST':
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']

            try:
                user_obj = Customer.objects.get(email=email)
            except Customer.DoesNotExist:
                user_obj = None

            if user_obj is None:
                messages.error(request, "No account found with this email.")
            else:
                if not user_obj.is_active:
                    messages.error(request, "Your account is not activated. Please check your email.")
                else:
                    user = authenticate(request, username=email, password=password)
                    if user is None:
                        messages.error(request, "Invalid password. Please try again.")
                    else:
                        login(request, user)
                        # Redirect based on role
                        if user.is_hotel_owner:
                            return redirect('hotel_dashboard')
                        elif user.is_customer:
                            return redirect('customer_dashboard')
                        return redirect('home')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerLoginForm()

    return render(request, 'customers/login.html', {'form': form})



@login_required
def customer_dashboard(request):
    if not isinstance(request.user, Customer):
        messages.error(request, "Access restricted to customers.")
        return redirect('home')
    bookings = Booking.objects.filter(content_type=ContentType.objects.get_for_model(Customer), object_id=request.user.pk).order_by('-created_at')
    paginator = Paginator(bookings, 10)  # 10 bookings per page, matching hotel_bookings
    page = request.GET.get('page')
    try:
        bookings_page = paginator.page(page)
    except PageNotAnInteger:
        bookings_page = paginator.page(1)
    except EmptyPage:
        bookings_page = paginator.page(paginator.num_pages)
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = urlencode(query_params)
    context = {
        'bookings': bookings_page,
        'loyalty_points': request.user.loyalty_points,
        'query_string': query_string,
    }
    return render(request, 'customers/dashboard.html', context)



@login_required
def customer_profile(request):
    if not request.user.is_customer:
        return redirect('home')
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('customer_dashboard')
    else:
        form = CustomerProfileForm(instance=request.user)
    return render(request, 'customers/profile.html', {'form': form})

def verify_booking(request):
    if request.method == 'POST':
        reference = request.POST.get('reference', '').strip()
        email = request.POST.get('email', '').strip()
        try:
            booking = Booking.objects.get(booking_reference=reference, email=email)
            return render(request, 'customers/verify_booking.html', {'booking': booking})
        except Booking.DoesNotExist:
            return render(request, 'customers/verify_booking.html', {'error': 'No booking found with this reference and email.'})
        except ValidationError:
            return render(request, 'customers/verify_booking.html', {'error': 'Invalid booking reference format.'})
    return render(request, 'customers/verify_booking.html')





class CustomerPasswordResetView(FormView):
    template_name = "customers/password_reset.html"
    form_class = PasswordResetForm
    success_url = reverse_lazy("customer_password_reset_done")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        try:
            customer = Customer.objects.get(email=email)
        except Customer.DoesNotExist:
            # Always pretend success for security
            return super().form_valid(form)

        token = default_token_generator.make_token(customer)
        uid = urlsafe_base64_encode(force_bytes(customer.pk))
        reset_url = self.request.build_absolute_uri(
            reverse_lazy("customer_password_reset_confirm", kwargs={"uidb64": uid, "token": token})
        )

        message = f"Hello {customer.full_name},\n\n"
        message += "We received a request to reset your password.\n"
        message += f"Click the link below to set a new password:\n{reset_url}\n\n"
        message += "If you didn’t request this, you can ignore this email.\n\n"
        message += "Thanks,\nHotelsPerHour Team"

        send_mail(
            subject="Password Reset",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
        )
        return super().form_valid(form)


class CustomerPasswordResetConfirmView(FormView):
    template_name = "customers/password_reset_confirm.html"
    form_class = SetPasswordForm
    success_url = reverse_lazy("customer_password_reset_complete")

    def get_customer(self, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            return Customer.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, Customer.DoesNotExist):
            return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        customer = self.get_customer(self.kwargs["uidb64"])
        if customer:
            kwargs["user"] = customer
        return kwargs

    def form_valid(self, form):
        customer = self.get_customer(self.kwargs["uidb64"])
        token = self.kwargs["token"]
        if customer and default_token_generator.check_token(customer, token):
            form.save()
            return super().form_valid(form)
        return render(self.request, "customers/password_reset_confirm.html", {
            "form": form,
            "validlink": False
        })


def customer_password_reset_done(request):
    return render(request, "customers/password_reset_done.html")


def customer_password_reset_complete(request):
    return render(request, "customers/password_reset_complete.html")
