from django.contrib import admin

from .models import Category, Phrase

admin.site.register(Category)


@admin.register(Phrase)
class PhraseAdmin(admin.ModelAdmin):
    list_display = ("cebuano_text", "english_translation", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("cebuano_text", "english_translation")
