from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

# ==========================================
# 1. REGISTER FORM (Clean Version)
# ==========================================
class UserRegisterForm(forms.ModelForm):
    # 1. EXPLICIT DEFINITIONS (This handles styling & widgets for ALL fields)
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}))
    
    # We define phone, email, and passwords here to ensure they all get the 'form-input' class
    phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Mobile Number'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email Address'}))
    
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Confirm Password'}))

    class Meta:
        model = CustomUser
        # We only list the fields that go into the database
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'password']
        # NOTE: I removed the 'widgets' dictionary because the explicit definitions above replace it.

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        email = cleaned_data.get("email")

        # FIX: Attach error specifically to the 'confirm_password' field
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")
            
        # FIX: Attach error specifically to the 'email' field
        if email and CustomUser.objects.filter(email=email).exists():
            self.add_error('email', "This email is already registered. Please Login.")
            
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email 
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# ==========================================
# 2. LOGIN FORM
# ==========================================
class UserLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email Address'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password'}))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise forms.ValidationError("Invalid email or password.")
            self.user = user
        return cleaned_data

    def get_user(self):
        return getattr(self, 'user', None)
    
    # ==========================================
# 3. CHECKOUT FORM
# ==========================================
class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Full Name'}))
    address = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Address'}))
    city = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'City'}))
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))