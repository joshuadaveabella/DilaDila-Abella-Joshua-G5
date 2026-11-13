from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

REGION_CHOICES = [
    ("", "Select your home region (optional)"),
    ("Tagalog", "Tagalog"),
    ("Hiligaynon", "Hiligaynon"),
    ("Waray", "Waray"),
    ("Ilocano", "Ilocano"),
    ("Kapampangan", "Kapampangan"),
    ("Bikol", "Bikol"),
    ("Other", "Other"),
]


def clean_unique_email(form, email, exclude_pk=None):
    """Shared check: the email must not already belong to another user (case-insensitive)."""
    email = email.strip().lower()
    taken = User.objects.filter(email__iexact=email)
    if exclude_pk is not None:
        taken = taken.exclude(pk=exclude_pk)
    if taken.exists():
        raise forms.ValidationError("An account with this email already exists.")
    return email


class RegistrationForm(forms.ModelForm):
    full_name = forms.CharField(max_length=100, label="Full name")
    email = forms.EmailField(max_length=100, label="Email address")
    home_region = forms.ChoiceField(choices=REGION_CHOICES, required=False, label="Home region")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["full_name", "email", "home_region"]

    def clean_full_name(self):
        name = self.cleaned_data["full_name"].strip()
        if not name:
            raise forms.ValidationError("Please enter your full name.")
        return name

    def clean_email(self):
        return clean_unique_email(self, self.cleaned_data["email"])

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "The two passwords do not match.")
        elif p1:
            # Runs Django's password rules (length, common passwords, etc.)
            temp_user = User(email=cleaned.get("email", ""), full_name=cleaned.get("full_name", ""))
            try:
                validate_password(p1, temp_user)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return cleaned

    def save(self, commit=True):
        # create_user hashes the password; new accounts are always STUDENT
        return User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
            full_name=self.cleaned_data["full_name"],
            home_region=self.cleaned_data.get("home_region", ""),
        )


class EmailLoginForm(AuthenticationForm):
    """Login form that asks for an email instead of a username."""

    username = forms.EmailField(label="Email address", widget=forms.EmailInput(attrs={"autofocus": True}))

    error_messages = {
        "invalid_login": "Invalid email or password. Please try again.",
        "inactive": "This account is inactive.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class ProfileForm(forms.ModelForm):
    home_region = forms.ChoiceField(choices=REGION_CHOICES, required=False, label="Home region")

    class Meta:
        model = User
        fields = ["full_name", "email", "home_region"]
        labels = {"full_name": "Full name", "email": "Email address"}

    def clean_email(self):
        return clean_unique_email(self, self.cleaned_data["email"], exclude_pk=self.instance.pk)
