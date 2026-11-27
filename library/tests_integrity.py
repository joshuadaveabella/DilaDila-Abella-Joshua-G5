"""PD3 data-integrity tests: DB constraints, on_delete rules, atomic saves and query counts."""
from unittest import mock

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from accounts.tests import GOOD_PASSWORD, make_admin, make_student
from library.models import Category, Phrase
from phrasebook.models import PhrasebookEntry


def make_phrase(category, text="Maayong buntag", english="Good morning", **extra):
    return Phrase.objects.create(category=category, cebuano_text=text, english_translation=english, **extra)


class ConstraintTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Greetings")

    def assertDbRejects(self, fn):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                fn()

    def test_blank_category_name_rejected_by_database(self):
        self.assertDbRejects(lambda: Category.objects.create(name="   "))

    def test_blank_phrase_text_rejected_by_database(self):
        self.assertDbRejects(lambda: make_phrase(self.cat, text="  "))
        self.assertDbRejects(lambda: make_phrase(self.cat, english=""))

    def test_duplicate_phrase_in_category_rejected_by_database(self):
        make_phrase(self.cat)
        self.assertDbRejects(lambda: make_phrase(self.cat))

    def test_same_phrase_allowed_in_other_category(self):
        make_phrase(self.cat)
        other = Category.objects.create(name="School")
        make_phrase(other)
        self.assertEqual(Phrase.objects.count(), 2)

    def test_phrasebook_blank_custom_text_rejected_by_database(self):
        student = make_student()
        self.assertDbRejects(lambda: PhrasebookEntry.objects.create(user=student, custom_text="  "))

    def test_phrasebook_entry_without_phrase_or_text_rejected(self):
        student = make_student()
        self.assertDbRejects(lambda: PhrasebookEntry.objects.create(user=student))

    def test_same_phrase_twice_for_one_student_rejected(self):
        student, phrase = make_student(), make_phrase(self.cat)
        PhrasebookEntry.objects.create(user=student, phrase=phrase)
        self.assertDbRejects(lambda: PhrasebookEntry.objects.create(user=student, phrase=phrase))


class OnDeleteTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Food")
        self.phrase = make_phrase(self.cat, "Gutom ko", "I am hungry")
        self.student = make_student()

    def test_category_with_phrases_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.cat.delete()

    def test_saved_phrase_is_protected(self):
        PhrasebookEntry.objects.create(user=self.student, phrase=self.phrase)
        with self.assertRaises(ProtectedError):
            self.phrase.delete()

    def test_deleting_student_removes_their_entries_only(self):
        other = make_student(email="o@example.com")
        PhrasebookEntry.objects.create(user=self.student, phrase=self.phrase)
        PhrasebookEntry.objects.create(user=other, custom_text="Salamat")
        self.student.delete()
        self.assertEqual(PhrasebookEntry.objects.count(), 1)
        self.assertTrue(Phrase.objects.filter(pk=self.phrase.pk).exists())


class AtomicTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.cat = Category.objects.create(name="Food")
        self.client.login(username="admin@example.com", password=GOOD_PASSWORD)

    def test_failed_phrase_delete_keeps_phrase_and_shows_message(self):
        phrase = make_phrase(self.cat)
        PhrasebookEntry.objects.create(user=make_student(), phrase=phrase)
        response = self.client.post(reverse("library:phrase_delete", args=[phrase.pk]), follow=True)
        self.assertContains(response, "cannot be deleted")
        self.assertTrue(Phrase.objects.filter(pk=phrase.pk).exists())

    def test_database_error_during_save_rolls_back_and_is_not_half_saved(self):
        with mock.patch("library.forms.PhraseForm.save", side_effect=IntegrityError("boom")):
            client = self.client
            client.raise_request_exception = False
            response = client.post(reverse("library:phrase_create"), {
                "category": self.cat.pk, "cebuano_text": "Unsa ni", "english_translation": "What is this",
            })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(Phrase.objects.count(), 0)


class QueryCountTests(TestCase):
    """select_related keeps list pages at a constant number of queries however many rows there are."""

    def setUp(self):
        self.student = make_student()
        self.admin = make_admin()
        for i in range(3):
            cat = Category.objects.create(name=f"Cat{i}")
            for j in range(4):
                p = make_phrase(cat, f"Cebuano {i}-{j}", f"English {i}-{j}")
                PhrasebookEntry.objects.create(user=self.student, phrase=p)

    def count_queries(self, url, email):
        self.client.login(username=email, password=GOOD_PASSWORD)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(self.client.get(url).status_code, 200)
        self.client.logout()
        return len(ctx)

    def test_phrase_list_query_count_does_not_grow_with_rows(self):
        before = self.count_queries(reverse("library:phrase_list"), "student@example.com")
        c = Category.objects.get(name="Cat0")
        for j in range(10):
            make_phrase(c, f"Extra {j}", f"Extra {j}")
        after = self.count_queries(reverse("library:phrase_list"), "student@example.com")
        self.assertEqual(before, after)

    def test_my_phrasebook_query_count_does_not_grow_with_rows(self):
        before = self.count_queries(reverse("phrasebook:my_phrasebook"), "student@example.com")
        c = Category.objects.get(name="Cat1")
        for j in range(10):
            p = make_phrase(c, f"More {j}", f"More {j}")
            PhrasebookEntry.objects.create(user=self.student, phrase=p)
        after = self.count_queries(reverse("phrasebook:my_phrasebook"), "student@example.com")
        self.assertEqual(before, after)

    def test_admin_lists_do_not_grow_with_rows(self):
        for name in ("library:manage_phrases", "phrasebook:all_phrasebooks"):
            self.assertLessEqual(self.count_queries(reverse(name), "admin@example.com"), 12, name)
