from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from library.models import Category, Phrase

from .models import PhrasebookEntry

PW = "Bisaya-Learner-2026"


class PhrasebookTestBase(TestCase):
    def setUp(self):
        self.maria = User.objects.create_user("maria@example.com", PW, full_name="Maria Santos")
        self.juan = User.objects.create_user("juan@example.com", PW, full_name="Juan Dela Cruz")
        self.admin = User.objects.create_superuser("admin@example.com", PW, full_name="Admin")
        self.cat = Category.objects.create(name="Food")
        self.phrase = Phrase.objects.create(category=self.cat, cebuano_text="Lami kaayo!", english_translation="Very delicious!")
        self.other_phrase = Phrase.objects.create(category=self.cat, cebuano_text="Busog na ko.", english_translation="I'm full.")
        self.inactive = Phrase.objects.create(category=self.cat, cebuano_text="Tago", english_translation="Hidden", is_active=False)
        self.entry = PhrasebookEntry.objects.create(user=self.maria, phrase=self.phrase, note="Heard at the canteen")
        self.juan_entry = PhrasebookEntry.objects.create(user=self.juan, custom_text="Kapoy kaayo ko", note="After class")

    def login(self, who):
        self.client.login(username=f"{who}@example.com", password=PW)


class ConstraintTests(PhrasebookTestBase):
    def test_check_constraint_requires_phrase_or_text(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PhrasebookEntry.objects.create(user=self.maria, phrase=None, custom_text=None)

    def test_unique_user_phrase_enforced_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PhrasebookEntry.objects.create(user=self.maria, phrase=self.phrase)

    def test_two_students_can_save_same_phrase(self):
        PhrasebookEntry.objects.create(user=self.juan, phrase=self.phrase)

    def test_same_student_can_have_many_custom_entries(self):
        PhrasebookEntry.objects.create(user=self.maria, custom_text="A")
        PhrasebookEntry.objects.create(user=self.maria, custom_text="B")

    def test_deleting_user_removes_their_entries(self):
        self.maria.delete()
        self.assertFalse(PhrasebookEntry.objects.filter(pk=self.entry.pk).exists())

    def test_saved_phrase_cannot_be_deleted_by_admin(self):
        self.login("admin")
        response = self.client.post(reverse("library:phrase_delete", args=[self.phrase.pk]), follow=True)
        self.assertContains(response, "cannot be deleted")
        self.assertTrue(Phrase.objects.filter(pk=self.phrase.pk).exists())

    def test_unsaved_phrase_can_be_deleted_by_admin(self):
        self.login("admin")
        self.client.post(reverse("library:phrase_delete", args=[self.other_phrase.pk]))
        self.assertFalse(Phrase.objects.filter(pk=self.other_phrase.pk).exists())


class AccessTests(PhrasebookTestBase):
    def test_logged_out_redirected(self):
        for name in ["my_phrasebook", "entry_create", "all_phrasebooks"]:
            url = reverse(f"phrasebook:{name}")
            self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}", msg_prefix=name)

    def test_admin_cannot_use_student_pages(self):
        self.login("admin")
        for url in [reverse("phrasebook:my_phrasebook"), reverse("phrasebook:entry_create"),
                    reverse("phrasebook:entry_update", args=[self.entry.pk])]:
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_student_cannot_open_admin_overview(self):
        self.login("maria")
        self.assertEqual(self.client.get(reverse("phrasebook:all_phrasebooks")).status_code, 403)


class OwnershipTests(PhrasebookTestBase):
    def test_list_shows_only_own_entries(self):
        self.login("maria")
        response = self.client.get(reverse("phrasebook:my_phrasebook"))
        self.assertContains(response, "Lami kaayo!")
        self.assertNotContains(response, "Kapoy kaayo ko")

    def test_cannot_edit_other_students_entry(self):
        self.login("maria")
        url = reverse("phrasebook:entry_update", args=[self.juan_entry.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {"phrase": "", "custom_text": "hacked", "note": ""}).status_code, 404)
        self.juan_entry.refresh_from_db()
        self.assertEqual(self.juan_entry.custom_text, "Kapoy kaayo ko")

    def test_cannot_delete_other_students_entry(self):
        self.login("maria")
        response = self.client.post(reverse("phrasebook:entry_delete", args=[self.juan_entry.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(PhrasebookEntry.objects.filter(pk=self.juan_entry.pk).exists())

    def test_created_entry_is_linked_to_logged_in_user(self):
        self.login("maria")
        self.client.post(reverse("phrasebook:entry_create"), {"phrase": "", "custom_text": "Unsa na?", "note": ""})
        self.assertEqual(PhrasebookEntry.objects.get(custom_text="Unsa na?").user, self.maria)


class CrudTests(PhrasebookTestBase):
    def setUp(self):
        super().setUp()
        self.login("maria")

    def test_create_from_library_phrase(self):
        response = self.client.post(reverse("phrasebook:entry_create"),
                                    {"phrase": self.other_phrase.pk, "custom_text": "", "note": "Lunch"}, follow=True)
        self.assertContains(response, "Added to your phrasebook")
        entry = PhrasebookEntry.objects.get(user=self.maria, phrase=self.other_phrase)
        self.assertIsNone(entry.custom_text)  # blank is stored as NULL

    def test_create_requires_phrase_or_text(self):
        response = self.client.post(reverse("phrasebook:entry_create"), {"phrase": "", "custom_text": "   ", "note": "x"})
        self.assertContains(response, "Choose a library phrase or type your own phrase")
        self.assertNotContains(response, "is violated")  # no raw database message
        self.assertEqual(PhrasebookEntry.objects.filter(user=self.maria).count(), 1)

    def test_duplicate_library_phrase_rejected(self):
        response = self.client.post(reverse("phrasebook:entry_create"), {"phrase": self.phrase.pk, "custom_text": "", "note": ""})
        self.assertContains(response, "already in your phrasebook", count=1)
        self.assertNotContains(response, "is violated")

    def test_inactive_phrase_cannot_be_chosen(self):
        response = self.client.post(reverse("phrasebook:entry_create"), {"phrase": self.inactive.pk, "custom_text": "", "note": ""})
        self.assertContains(response, "Select a valid choice")

    def test_text_too_long_rejected(self):
        response = self.client.post(reverse("phrasebook:entry_create"), {"phrase": "", "custom_text": "x" * 300, "note": ""})
        self.assertContains(response, "at most 255")

    def test_update(self):
        response = self.client.post(reverse("phrasebook:entry_update", args=[self.entry.pk]),
                                    {"phrase": self.phrase.pk, "custom_text": "", "note": "New note"}, follow=True)
        self.assertContains(response, "updated")
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.note, "New note")

    def test_update_keeps_deactivated_phrase_selectable(self):
        self.phrase.is_active = False
        self.phrase.save()
        response = self.client.post(reverse("phrasebook:entry_update", args=[self.entry.pk]),
                                    {"phrase": self.phrase.pk, "custom_text": "", "note": "still ok"})
        self.assertEqual(response.status_code, 302)

    def test_delete_with_confirmation(self):
        url = reverse("phrasebook:entry_delete", args=[self.entry.pk])
        self.assertContains(self.client.get(url), "Delete this phrasebook entry?")
        self.assertTrue(PhrasebookEntry.objects.filter(pk=self.entry.pk).exists())
        self.client.post(url)
        self.assertFalse(PhrasebookEntry.objects.filter(pk=self.entry.pk).exists())

    def test_search_and_category_filter(self):
        PhrasebookEntry.objects.create(user=self.maria, custom_text="Pila na?", note="jeepney")
        r = self.client.get(reverse("phrasebook:my_phrasebook"), {"q": "jeepney"})
        self.assertContains(r, "Pila na?")
        self.assertNotContains(r, "Lami kaayo!")
        r2 = self.client.get(reverse("phrasebook:my_phrasebook"), {"category": self.cat.pk})
        self.assertContains(r2, "Lami kaayo!")
        self.assertNotContains(r2, "Pila na?")


class SaveFromLibraryTests(PhrasebookTestBase):
    def setUp(self):
        super().setUp()
        self.login("maria")

    def test_save_creates_entry(self):
        response = self.client.post(reverse("phrasebook:save_from_library", args=[self.other_phrase.pk]), {"next": "/library/"}, follow=True)
        self.assertContains(response, "saved to your phrasebook")
        self.assertTrue(PhrasebookEntry.objects.filter(user=self.maria, phrase=self.other_phrase).exists())

    def test_saving_twice_does_not_duplicate(self):
        url = reverse("phrasebook:save_from_library", args=[self.phrase.pk])
        self.client.post(url)
        self.assertEqual(PhrasebookEntry.objects.filter(user=self.maria, phrase=self.phrase).count(), 1)

    def test_requires_post(self):
        self.assertEqual(self.client.get(reverse("phrasebook:save_from_library", args=[self.phrase.pk])).status_code, 405)

    def test_inactive_phrase_cannot_be_saved(self):
        response = self.client.post(reverse("phrasebook:save_from_library", args=[self.inactive.pk]))
        self.assertEqual(response.status_code, 404)

    def test_external_next_url_ignored(self):
        response = self.client.post(reverse("phrasebook:save_from_library", args=[self.other_phrase.pk]), {"next": "https://evil.example"})
        self.assertRedirects(response, reverse("library:phrase_list"))

    def test_library_shows_saved_state_and_button(self):
        response = self.client.get(reverse("library:phrase_list"))
        self.assertContains(response, "In your phrasebook")  # Lami kaayo! already saved
        self.assertContains(response, "Save to my phrasebook")  # Busog na ko. not yet

    def test_admin_does_not_see_save_button(self):
        self.client.logout()
        self.login("admin")
        self.assertNotContains(self.client.get(reverse("library:phrase_list")), "Save to my phrasebook")


class AdminOverviewTests(PhrasebookTestBase):
    def test_admin_sees_all_entries_read_only(self):
        self.login("admin")
        response = self.client.get(reverse("phrasebook:all_phrasebooks"))
        self.assertContains(response, "Lami kaayo!")
        self.assertContains(response, "Kapoy kaayo ko")
        self.assertNotContains(response, "Edit")

    def test_admin_can_filter_by_student(self):
        self.login("admin")
        response = self.client.get(reverse("phrasebook:all_phrasebooks"), {"student": "juan"})
        self.assertContains(response, "Kapoy kaayo ko")
        self.assertNotContains(response, "Lami kaayo!")


class DashboardTests(PhrasebookTestBase):
    def test_student_dashboard_shows_count_and_link(self):
        self.login("maria")
        response = self.client.get(reverse("accounts:student_dashboard"))
        self.assertEqual(response.context["entry_count"], 1)
        self.assertContains(response, reverse("phrasebook:my_phrasebook"))

    def test_admin_dashboard_shows_total_entries(self):
        self.login("admin")
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.context["total_entries"], 2)
        self.assertContains(response, reverse("phrasebook:all_phrasebooks"))


class SeedCommandTests(TestCase):
    def test_seed_demo_is_repeatable(self):
        from django.core.management import call_command
        call_command("seed_demo", verbosity=0)
        call_command("seed_demo", verbosity=0)
        self.assertEqual(User.objects.filter(email__in=["admin@dila.test", "student@dila.test"]).count(), 2)
        self.assertEqual(Phrase.objects.count(), 22)
        self.assertTrue(self.client.login(username="student@dila.test", password="DilaDila#Test2026"))
