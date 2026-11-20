"""
Fill the database with test accounts and sample Cebuano phrases.

    python manage.py seed_demo

Safe to run more than once (it never creates duplicates).
"""

from django.core.management.base import BaseCommand

from accounts.models import User
from library.models import Category, Phrase
from phrasebook.models import PhrasebookEntry

TEST_PASSWORD = "DilaDila#Test2026"

CATEGORIES = {
    "School": "Phrases for class, teachers and classmates",
    "Food": "Ordering, paying and talking about food",
    "Transportation": "Jeepneys, fares and getting around Cebu",
    "Small Talk": "Greetings and everyday conversation",
}

# (category, Cebuano, English)
PHRASES = [
    ("School", "Asa ang classroom?", "Where is the classroom?"),
    ("School", "Pwede ko mangutana?", "May I ask a question?"),
    ("School", "Wala ko kasabot.", "I don't understand."),
    ("School", "Unsa ang buot ipasabot niana?", "What does that mean?"),
    ("School", "Unsa'y oras karon?", "What time is it now?"),
    ("Food", "Tagpila ni?", "How much is this?"),
    ("Food", "Gusto ko ug kan-on.", "I want rice."),
    ("Food", "Palihug ug tubig.", "Water, please."),
    ("Food", "Lami kaayo!", "Very delicious!"),
    ("Food", "Busog na ko.", "I'm already full."),
    ("Food", "Unsa'y lami dinhi?", "What's delicious here?"),
    ("Transportation", "Para!", "Stop! (said to the jeepney driver)"),
    ("Transportation", "Tagpila ang plete?", "How much is the fare?"),
    ("Transportation", "Asa ko makasakay ug jeep padulong sa Colon?", "Where can I ride a jeep going to Colon?"),
    ("Transportation", "Dinhi ra ko manaog.", "I'll get off right here."),
    ("Small Talk", "Kumusta ka?", "How are you?"),
    ("Small Talk", "Maayo ra ko.", "I'm fine."),
    ("Small Talk", "Unsa imong ngalan?", "What is your name?"),
    ("Small Talk", "Taga-asa ka?", "Where are you from?"),
    ("Small Talk", "Hinay-hinay lang ang pagsulti, palihug.", "Please speak slowly."),
    ("Small Talk", "Salamat!", "Thank you!"),
    ("Small Talk", "Pasayloa ko.", "Sorry / excuse me."),
]


class Command(BaseCommand):
    help = "Create test accounts and sample phrases."

    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            email="admin@dila.test",
            defaults={"full_name": "Test Admin", "role": User.Role.ADMIN, "is_staff": True, "is_superuser": True},
        )
        student, _ = User.objects.get_or_create(
            email="student@dila.test",
            defaults={"full_name": "Test Student", "home_region": "Hiligaynon", "role": User.Role.STUDENT},
        )
        for user in (admin, student):
            user.set_password(TEST_PASSWORD)
            user.save()

        categories = {}
        for name, description in CATEGORIES.items():
            categories[name], _ = Category.objects.get_or_create(name=name, defaults={"description": description})

        created = 0
        for category, cebuano, english in PHRASES:
            _, was_created = Phrase.objects.get_or_create(
                category=categories[category], cebuano_text=cebuano, defaults={"english_translation": english}
            )
            created += was_created

        # A couple of sample phrasebook entries for the test student
        PhrasebookEntry.objects.get_or_create(
            user=student, phrase=Phrase.objects.get(cebuano_text="Lami kaayo!"), defaults={"note": "Said by the canteen staff"}
        )
        if not PhrasebookEntry.objects.filter(user=student, custom_text="Kapoy kaayo ko").exists():
            PhrasebookEntry.objects.create(user=student, custom_text="Kapoy kaayo ko", note="Heard after a long day")

        self.stdout.write(self.style.SUCCESS(
            f"Done. {created} new phrase(s). Test accounts: admin@dila.test and student@dila.test "
            f"(password: {TEST_PASSWORD})"
        ))
