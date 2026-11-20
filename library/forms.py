from django import forms

from .models import Category, Phrase


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        labels = {"name": "Category name", "description": "Description (optional)"}

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Please enter a category name.")
        taken = Category.objects.filter(name__iexact=name).exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError("A category with this name already exists.")
        return name


class PhraseForm(forms.ModelForm):
    class Meta:
        model = Phrase
        fields = [
            "category", "cebuano_text", "english_translation",
            "regional_language", "regional_translation", "audio_url", "is_active",
        ]
        labels = {
            "cebuano_text": "Cebuano phrase",
            "english_translation": "English translation",
            "regional_language": "Other language (optional)",
            "regional_translation": "Translation in other language (optional)",
            "audio_url": "Audio link (optional)",
            "is_active": "Active (visible to students)",
        }

    def clean_cebuano_text(self):
        return self.cleaned_data["cebuano_text"].strip()

    def clean_english_translation(self):
        return self.cleaned_data["english_translation"].strip()

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        text = cleaned.get("cebuano_text")
        # BR-05: unique Cebuano text per category (case-insensitive)
        if category and text:
            duplicate = Phrase.objects.filter(category=category, cebuano_text__iexact=text).exclude(pk=self.instance.pk)
            if duplicate.exists():
                self.add_error("cebuano_text", "This phrase already exists in the selected category.")
        # Other-language fields must come as a pair
        language = (cleaned.get("regional_language") or "").strip()
        translation = (cleaned.get("regional_translation") or "").strip()
        if translation and not language:
            self.add_error("regional_language", "Enter the language name for this translation.")
        if language and not translation:
            self.add_error("regional_translation", "Enter the translation, or clear the language name.")
        cleaned["regional_language"] = language
        cleaned["regional_translation"] = translation
        return cleaned
