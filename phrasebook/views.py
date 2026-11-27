from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from accounts.utils import clean_param, safe_redirect
from library.models import Category, Phrase

from .forms import PhrasebookEntryForm
from .models import PhrasebookEntry

student_only = role_required(User.Role.STUDENT)
admin_only = role_required(User.Role.ADMIN)


def _search(request, queryset):
    q = clean_param(request, "q")
    category_id = clean_param(request, "category", 10)
    if q:
        queryset = queryset.filter(
            Q(custom_text__icontains=q) | Q(note__icontains=q)
            | Q(phrase__cebuano_text__icontains=q) | Q(phrase__english_translation__icontains=q)
        )
    if category_id.isdigit():
        queryset = queryset.filter(phrase__category_id=int(category_id))
    return queryset, q, category_id


# ---------- Student: own entries only ----------

@student_only
def my_phrasebook(request):
    entries, q, category_id = _search(
        request, request.user.phrasebook_entries.select_related("phrase", "phrase__category")
    )
    context = {
        "page": Paginator(entries, 10).get_page(request.GET.get("page")),
        "categories": Category.objects.all(),
        "q": q,
        "selected_category": category_id,
    }
    return render(request, "phrasebook/my_phrasebook.html", context)


@student_only
def entry_create(request):
    form = PhrasebookEntryForm(request.POST or None, user=request.user)
    if request.method == "POST":
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, "Added to your phrasebook.")
            return redirect("phrasebook:my_phrasebook")
        messages.error(request, "Please fix the errors below.")
    return render(request, "phrasebook/entry_form.html", {"form": form, "title": "Add to my phrasebook"})


@student_only
def entry_update(request, pk):
    # Filtering by user means another student's entry gives a 404
    entry = get_object_or_404(PhrasebookEntry, pk=pk, user=request.user)
    form = PhrasebookEntryForm(request.POST or None, instance=entry, user=request.user)
    if request.method == "POST":
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, "Phrasebook entry updated.")
            return redirect("phrasebook:my_phrasebook")
        messages.error(request, "Please fix the errors below.")
    return render(request, "phrasebook/entry_form.html", {"form": form, "title": "Edit phrasebook entry"})


@student_only
def entry_delete(request, pk):
    entry = get_object_or_404(PhrasebookEntry, pk=pk, user=request.user)
    if request.method == "POST":
        with transaction.atomic():
            entry.delete()
        messages.success(request, "Removed from your phrasebook.")
        return redirect("phrasebook:my_phrasebook")
    return render(request, "library/confirm_delete.html", {"object_name": entry.display_text, "kind": "phrasebook entry", "cancel_url": reverse("phrasebook:my_phrasebook")})


@student_only
@require_POST
def save_from_library(request, phrase_pk):
    """One-click 'Save to my phrasebook' button on the phrase library."""
    phrase = get_object_or_404(Phrase, pk=phrase_pk, is_active=True)
    with transaction.atomic():
        entry, created = PhrasebookEntry.objects.get_or_create(user=request.user, phrase=phrase)
    if created:
        messages.success(request, f"“{phrase.cebuano_text}” saved to your phrasebook.")
    else:
        messages.info(request, "That phrase is already in your phrasebook.")
    return safe_redirect(request, request.POST.get("next"), "library:phrase_list")


# ---------- Admin: read-only overview of all students ----------

@admin_only
def all_phrasebooks(request):
    entries, q, category_id = _search(
        request, PhrasebookEntry.objects.select_related("user", "phrase", "phrase__category")
    )
    student = clean_param(request, "student")
    if student:
        entries = entries.filter(Q(user__email__icontains=student) | Q(user__full_name__icontains=student))
    context = {
        "page": Paginator(entries, 15).get_page(request.GET.get("page")),
        "categories": Category.objects.all(),
        "q": q,
        "selected_category": category_id,
        "student": student,
    }
    return render(request, "phrasebook/all_phrasebooks.html", context)
