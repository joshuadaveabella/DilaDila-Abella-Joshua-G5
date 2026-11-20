from django import forms
from django.db.models import Q

from library.models import Phrase

from .models import PhrasebookEntry


class PhrasebookEntryForm(forms.ModelForm):
    phrase = forms.ModelChoiceField(
        queryset=Phrase.objects.none(), required=False, empty_label="— None (my own phrase) —",
        label="Library phrase (optional)",
    )
    custom_text = forms.CharField(
        max_length=255, required=False, label="My own phrase (optional)",
        help_text="Something you heard in real life that is not in the library.",
    )
    note = forms.CharField(max_length=255, required=False, label="Note (where did you hear it?)")

    class Meta:
        model = PhrasebookEntry
        fields = ["phrase", "custom_text", "note"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        # Only active phrases can be picked (plus the one already chosen, if it was deactivated later)
        allowed = Q(is_active=True)
        if self.instance.pk and self.instance.phrase_id:
            allowed |= Q(pk=self.instance.phrase_id)
        self.fields["phrase"].queryset = Phrase.objects.filter(allowed).select_related("category")
        self.fields["phrase"].label_from_instance = lambda p: f"{p.cebuano_text} — {p.english_translation}"

    def clean_custom_text(self):
        # Store NULL instead of an empty string so the database CHECK constraint works
        return self.cleaned_data["custom_text"].strip() or None

    def clean(self):
        cleaned = super().clean()
        phrase = cleaned.get("phrase")
        custom_text = cleaned.get("custom_text")
        if not phrase and not custom_text and "custom_text" not in self.errors:
            self.add_error(None, "Choose a library phrase or type your own phrase.")
        if phrase:
            duplicate = PhrasebookEntry.objects.filter(user=self.user, phrase=phrase).exclude(pk=self.instance.pk)
            if duplicate.exists():
                self.add_error("phrase", "This phrase is already in your phrasebook.")
        return cleaned

    def save(self, commit=True):
        entry = super().save(commit=False)
        entry.user = self.user
        if commit:
            entry.save()
        return entry
