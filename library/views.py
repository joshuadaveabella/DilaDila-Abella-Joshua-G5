from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from accounts.utils import clean_param, safe_redirect
from phrasebook.models import PhrasebookEntry

from .forms import CategoryForm, PhraseForm
from .models import Category, Phrase

admin_only = role_required(User.Role.ADMIN)


def _filter_phrases(request, queryset):
    """Apply the ?q= search and ?category= filter from the URL."""
    q = clean_param(request, "q")
    category_id = clean_param(request, "category", 10)
    if q:
        queryset = queryset.filter(
            Q(cebuano_text__icontains=q)
            | Q(english_translation__icontains=q)
            | Q(regional_translation__icontains=q)
        )
    if category_id.isdigit():
        queryset = queryset.filter(category_id=int(category_id))
    return queryset, q, category_id


def _page(request, queryset, per_page=12):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


# ---------- Browse (students and admins) ----------

@login_required
def phrase_list(request):
    phrases, q, category_id = _filter_phrases(
        request, Phrase.objects.filter(is_active=True).select_related("category")
    )
    page = _page(request, phrases)
    saved_ids = set()
    if request.user.role == User.Role.STUDENT:
        # Which of the phrases on this page the student already saved
        saved_ids = set(
            PhrasebookEntry.objects.filter(user=request.user, phrase__in=list(page.object_list))
            .values_list("phrase_id", flat=True)
        )
    context = {
        "page": page,
        "categories": Category.objects.all(),
        "q": q,
        "selected_category": category_id,
        "saved_ids": saved_ids,
    }
    return render(request, "library/phrase_list.html", context)


# ---------- Admin: phrases ----------

@admin_only
def manage_phrases(request):
    phrases, q, category_id = _filter_phrases(request, Phrase.objects.select_related("category"))
    status = clean_param(request, "status", 10)
    if status == "active":
        phrases = phrases.filter(is_active=True)
    elif status == "inactive":
        phrases = phrases.filter(is_active=False)
    context = {
        "page": _page(request, phrases, per_page=15),
        "categories": Category.objects.all(),
        "q": q,
        "selected_category": category_id,
        "status": status,
    }
    return render(request, "library/manage_phrases.html", context)


@admin_only
def phrase_create(request):
    form = PhraseForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            with transaction.atomic():
                phrase = form.save()
            messages.success(request, f"Phrase “{phrase.cebuano_text}” was added.")
            return redirect("library:manage_phrases")
        messages.error(request, "Please fix the errors below.")
    return render(request, "library/phrase_form.html", {"form": form, "title": "Add phrase"})


@admin_only
def phrase_update(request, pk):
    phrase = get_object_or_404(Phrase, pk=pk)
    old_audio = phrase.audio_file.name if phrase.audio_file else ""
    form = PhraseForm(request.POST or None, request.FILES or None, instance=phrase)
    if request.method == "POST":
        if form.is_valid():
            with transaction.atomic():
                phrase = form.save()
                new_audio = phrase.audio_file.name if phrase.audio_file else ""
                if old_audio and old_audio != new_audio:
                    # The old clip was replaced or cleared: remove it once the change is committed
                    storage = Phrase._meta.get_field("audio_file").storage
                    transaction.on_commit(lambda: storage.delete(old_audio))
            messages.success(request, "Phrase updated.")
            return redirect("library:manage_phrases")
        messages.error(request, "Please fix the errors below.")
    return render(request, "library/phrase_form.html", {"form": form, "title": "Edit phrase"})


@admin_only
def phrase_delete(request, pk):
    phrase = get_object_or_404(Phrase, pk=pk)
    if request.method == "POST":
        try:
            with transaction.atomic():
                phrase.delete()
        except ProtectedError:
            messages.error(
                request,
                "This phrase is used elsewhere (for example in a student's phrasebook) and cannot be deleted. "
                "Deactivate it instead.",
            )
        else:
            messages.success(request, "Phrase deleted.")
        return redirect("library:manage_phrases")
    return render(request, "library/confirm_delete.html", {"object_name": phrase.cebuano_text, "kind": "phrase", "cancel_url": reverse("library:manage_phrases")})


@admin_only
@require_POST
def phrase_toggle(request, pk):
    phrase = get_object_or_404(Phrase, pk=pk)
    phrase.is_active = not phrase.is_active
    phrase.save(update_fields=["is_active"])
    state = "activated" if phrase.is_active else "deactivated"
    messages.success(request, f"Phrase {state}.")
    return safe_redirect(request, request.POST.get("next"), "library:manage_phrases")


# ---------- Admin: categories ----------

@admin_only
def manage_categories(request):
    categories = Category.objects.annotate(phrase_count=Count("phrases"))
    return render(request, "library/manage_categories.html", {"categories": categories})


@admin_only
def category_create(request):
    form = CategoryForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            with transaction.atomic():
                category = form.save()
            messages.success(request, f"Category “{category.name}” was added.")
            return redirect("library:manage_categories")
        messages.error(request, "Please fix the errors below.")
    return render(request, "library/category_form.html", {"form": form, "title": "Add category"})


@admin_only
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST":
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, "Category updated.")
            return redirect("library:manage_categories")
        messages.error(request, "Please fix the errors below.")
    return render(request, "library/category_form.html", {"form": form, "title": "Edit category"})


@admin_only
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        try:
            with transaction.atomic():
                category.delete()
        except ProtectedError:
            messages.error(request, "This category still has phrases. Move or delete them first.")
        else:
            messages.success(request, "Category deleted.")
        return redirect("library:manage_categories")
    return render(request, "library/confirm_delete.html", {"object_name": category.name, "kind": "category", "cancel_url": reverse("library:manage_categories")})
