from django.contrib import admin

from .models import PhrasebookEntry


@admin.register(PhrasebookEntry)
class PhrasebookEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "phrase", "custom_text", "created_at")
    search_fields = ("user__email", "custom_text", "phrase__cebuano_text")
