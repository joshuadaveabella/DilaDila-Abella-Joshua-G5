from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from library.models import Phrase


class PhrasebookEntry(models.Model):
    """
    A phrase a student saves in their personal phrasebook. SDD table: phrasebook_entries.
    An entry points to a library phrase, holds the student's own text, or both.
    """

    entry_id = models.AutoField(primary_key=True)
    # BR-07: every entry belongs to exactly one student
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="phrasebook_entries", db_column="user_id",
    )
    # PROTECT: a library phrase that students have saved cannot be deleted (BR-15); admins deactivate it instead
    phrase = models.ForeignKey(
        Phrase, on_delete=models.PROTECT, null=True, blank=True,
        related_name="phrasebook_entries", db_column="phrase_id",
    )
    custom_text = models.CharField(max_length=255, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "phrasebook_entries"
        ordering = ["-created_at", "-entry_id"]
        verbose_name_plural = "phrasebook entries"
        constraints = [
            # BR-06: an entry needs a library phrase, custom text, or both
            models.CheckConstraint(
                condition=Q(phrase__isnull=False) | Q(custom_text__isnull=False),
                name="phrasebook_phrase_or_text_check",
            ),
            # custom_text is NULL or real text, never an empty/space-only string
            models.CheckConstraint(
                condition=Q(custom_text__isnull=True) | Q(custom_text__regex=r"\S"),
                name="phrasebook_custom_text_not_blank",
            ),
            # A student can save the same library phrase only once
            models.UniqueConstraint(
                fields=["user", "phrase"], condition=Q(phrase__isnull=False),
                name="phrasebook_user_phrase_uniq",
            ),
        ]

    def __str__(self):
        return self.display_text

    @property
    def display_text(self):
        return self.phrase.cebuano_text if self.phrase_id else (self.custom_text or "")
