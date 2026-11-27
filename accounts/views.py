from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.db import transaction
from django.urls import reverse_lazy
from django.shortcuts import redirect, render

from .decorators import role_required
from .forms import EmailLoginForm, ProfileForm, RegistrationForm
from .models import User
from library.models import Category, Phrase
from phrasebook.models import PhrasebookEntry


def home(request):
    """Landing page: send logged-in users to their dashboard, others to login."""
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    return redirect("accounts:login")


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created! You can now log in.")
            return redirect("accounts:login")
        messages.error(request, "Please fix the errors below.")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


class DilaLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().get_short_name()}!")
        return super().form_valid(form)


@login_required
def dashboard(request):
    """After login, each role is sent to its own dashboard."""
    if request.user.role == User.Role.ADMIN:
        return redirect("accounts:admin_dashboard")
    return redirect("accounts:student_dashboard")


@role_required(User.Role.STUDENT)
def student_dashboard(request):
    context = {
        "phrase_count": Phrase.objects.filter(is_active=True).count(),
        "entry_count": request.user.phrasebook_entries.count(),
    }
    return render(request, "accounts/student_dashboard.html", context)


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    context = {
        "total_users": User.objects.count(),
        "total_students": User.objects.filter(role=User.Role.STUDENT).count(),
        "total_admins": User.objects.filter(role=User.Role.ADMIN).count(),
        "total_phrases": Phrase.objects.count(),
        "total_categories": Category.objects.count(),
        "total_entries": PhrasebookEntry.objects.count(),
        "recent_users": User.objects.order_by("-created_at")[:5],
    }
    return render(request, "accounts/admin_dashboard.html", context)


@login_required
def profile(request):
    """View the logged-in user's own profile (no user id in the URL, so nobody else's can be opened)."""
    return render(request, "accounts/profile.html")


@login_required
def profile_edit(request):
    """Edit the logged-in user's own profile."""
    old_photo = request.user.profile_photo.name if request.user.profile_photo else ""
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                new_photo = user.profile_photo.name if user.profile_photo else ""
                if old_photo and old_photo != new_photo:
                    storage = User._meta.get_field("profile_photo").storage
                    transaction.on_commit(lambda: storage.delete(old_photo))
            messages.success(request, "Your profile was updated.")
            return redirect("accounts:profile")
        messages.error(request, "Please fix the errors below.")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile_edit.html", {"form": form})


def permission_denied(request, exception=None):
    """Friendly 403 page, shown when a user opens another role's page."""
    return render(request, "403.html", status=403)


class DilaPasswordChangeView(PasswordChangeView):
    """Logged-in users change their own password (the old password is required)."""

    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        messages.success(self.request, "Your password was changed.")
        return super().form_valid(form)
