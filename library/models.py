from django.db import models
from django.utils import timezone


class Category(models.Model):
    """Situational grouping of phrases (school, food, transportation, small talk). SDD table: categories."""

    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "categories"
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Phrase(models.Model):
    """A Cebuano phrase in the library. SDD table: phrases."""

    phrase_id = models.AutoField(primary_key=True)
    # PROTECT: a category that still has phrases cannot be deleted (BR-04)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="phrases", db_column="category_id"
    )
    cebuano_text = models.CharField(max_length=255)
    english_translation = models.CharField(max_length=255)
    regional_language = models.CharField(max_length=50, blank=True)
    regional_translation = models.CharField(max_length=255, blank=True)
    audio_url = models.URLField(max_length=255, blank=True)
    # Phrases that are still referenced elsewhere are deactivated instead of deleted (BR-15)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "phrases"
        ordering = ["cebuano_text"]
        constraints = [
            # BR-05: same Cebuano text cannot appear twice in one category
            models.UniqueConstraint(fields=["category", "cebuano_text"], name="phrases_category_text_uniq"),
        ]

    def __str__(self):
        return self.cebuano_text
