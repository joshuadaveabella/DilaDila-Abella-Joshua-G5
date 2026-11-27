from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Phrase


@receiver(post_delete, sender=Phrase)
def delete_audio_file(sender, instance, **kwargs):
    """When a phrase is deleted, remove its uploaded audio from disk (only if the delete is committed)."""
    if instance.audio_file:
        storage, name = instance.audio_file.storage, instance.audio_file.name
        transaction.on_commit(lambda: storage.delete(name))
