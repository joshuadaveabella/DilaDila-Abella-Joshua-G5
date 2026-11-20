from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Category, Phrase

PW = "Bisaya-Learner-2026"


def make_user(email, role=User.Role.STUDENT):
    return User.objects.create_user(email=email, password=PW, full_name="Test User", role=role)


class LibraryTestBase(TestCase):
    def setUp(self):
        self.student = make_user("student@example.com")
        self.admin = make_user("admin@example.com", User.Role.ADMIN)
        self.school = Category.objects.create(name="School")
        self.food = Category.objects.create(name="Food")
        self.p1 = Phrase.objects.create(category=self.school, cebuano_text="Asa ang classroom?", english_translation="Where is the classroom?")
        self.p2 = Phrase.objects.create(category=self.food, cebuano_text="Lami kaayo!", english_translation="Very delicious!")
        self.hidden = Phrase.objects.create(category=self.food, cebuano_text="Tago ni", english_translation="Hidden phrase", is_active=False)

    def login(self, who):
        self.client.login(username=f"{who}@example.com", password=PW)


class ModelTests(LibraryTestBase):
    def test_tables_live_in_postgresql(self):
        self.assertEqual(connection.vendor, "postgresql")
        tables = connection.introspection.table_names()
        self.assertIn("categories", tables)
        self.assertIn("phrases", tables)

    def test_unique_phrase_per_category_enforced_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Phrase.objects.create(category=self.school, cebuano_text="Asa ang classroom?", english_translation="dup")

    def test_same_text_allowed_in_other_category(self):
        Phrase.objects.create(category=self.food, cebuano_text="Asa ang classroom?", english_translation="ok")

    def test_unique_category_name(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(name="School")


class AccessTests(LibraryTestBase):
    def test_logged_out_redirected_to_login(self):
        for name in ["phrase_list", "manage_phrases", "phrase_create", "manage_categories", "category_create"]:
            url = reverse(f"library:{name}")
            self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}", msg_prefix=name)

    def test_student_cannot_open_admin_pages(self):
        self.login("student")
        urls = [
            reverse("library:manage_phrases"), reverse("library:phrase_create"),
            reverse("library:phrase_update", args=[self.p1.pk]), reverse("library:phrase_delete", args=[self.p1.pk]),
            reverse("library:manage_categories"), reverse("library:category_create"),
            reverse("library:category_update", args=[self.school.pk]), reverse("library:category_delete", args=[self.school.pk]),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_student_cannot_post_admin_actions(self):
        self.login("student")
        self.client.post(reverse("library:phrase_delete", args=[self.p1.pk]))
        self.client.post(reverse("library:phrase_toggle", args=[self.p1.pk]))
        self.p1.refresh_from_db()
        self.assertTrue(self.p1.is_active)
        self.assertTrue(Phrase.objects.filter(pk=self.p1.pk).exists())


class BrowseTests(LibraryTestBase):
    def test_student_sees_only_active_phrases(self):
        self.login("student")
        response = self.client.get(reverse("library:phrase_list"))
        self.assertContains(response, "Asa ang classroom?")
        self.assertContains(response, "Lami kaayo!")
        self.assertNotContains(response, "Hidden phrase")

    def test_search_by_cebuano_and_english(self):
        self.login("student")
        r1 = self.client.get(reverse("library:phrase_list"), {"q": "classroom"})
        self.assertContains(r1, "Asa ang classroom?")
        self.assertNotContains(r1, "Lami kaayo!")
        r2 = self.client.get(reverse("library:phrase_list"), {"q": "delicious"})
        self.assertContains(r2, "Lami kaayo!")

    def test_filter_by_category(self):
        self.login("student")
        response = self.client.get(reverse("library:phrase_list"), {"category": self.food.pk})
        self.assertContains(response, "Lami kaayo!")
        self.assertNotContains(response, "Asa ang classroom?")

    def test_no_results_message(self):
        self.login("student")
        self.assertContains(self.client.get(reverse("library:phrase_list"), {"q": "zzzz"}), "No phrases match")

    def test_pagination(self):
        for i in range(15):
            Phrase.objects.create(category=self.school, cebuano_text=f"Phrase {i}", english_translation=f"T{i}")
        self.login("student")
        response = self.client.get(reverse("library:phrase_list"))
        self.assertEqual(len(response.context["page"].object_list), 12)
        self.assertContains(response, "Page 1 of 2")


class AdminPhraseCrudTests(LibraryTestBase):
    def setUp(self):
        super().setUp()
        self.login("admin")

    def data(self, **extra):
        d = {"category": self.school.pk, "cebuano_text": "Pwede ko mangutana?", "english_translation": "May I ask a question?",
             "regional_language": "", "regional_translation": "", "audio_url": "", "is_active": "on"}
        d.update(extra)
        return d

    def test_create(self):
        response = self.client.post(reverse("library:phrase_create"), self.data(), follow=True)
        self.assertContains(response, "was added")
        self.assertTrue(Phrase.objects.filter(cebuano_text="Pwede ko mangutana?").exists())

    def test_create_requires_fields(self):
        response = self.client.post(reverse("library:phrase_create"), self.data(cebuano_text="", english_translation=""))
        self.assertContains(response, "This field is required")
        self.assertEqual(Phrase.objects.count(), 3)

    def test_duplicate_in_same_category_rejected_case_insensitive(self):
        response = self.client.post(reverse("library:phrase_create"), self.data(cebuano_text="ASA ANG CLASSROOM?"))
        self.assertContains(response, "already exists in the selected category")
        self.assertEqual(Phrase.objects.count(), 3)

    def test_exact_duplicate_shows_one_message(self):
        response = self.client.post(reverse("library:phrase_create"), self.data(cebuano_text="Asa ang classroom?"))
        self.assertContains(response, "already exists", count=1)

    def test_invalid_audio_url_rejected(self):
        response = self.client.post(reverse("library:phrase_create"), self.data(audio_url="not a url"))
        self.assertContains(response, "valid URL")

    def test_other_language_must_be_paired(self):
        response = self.client.post(reverse("library:phrase_create"), self.data(regional_translation="Diin ang klase?"))
        self.assertContains(response, "Enter the language name")

    def test_update(self):
        response = self.client.post(reverse("library:phrase_update", args=[self.p1.pk]),
                                    self.data(cebuano_text="Asa ang klasrum?"), follow=True)
        self.assertContains(response, "Phrase updated")
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.cebuano_text, "Asa ang klasrum?")

    def test_update_can_keep_own_text(self):
        response = self.client.post(reverse("library:phrase_update", args=[self.p1.pk]),
                                    self.data(cebuano_text="Asa ang classroom?", english_translation="Changed"))
        self.assertEqual(response.status_code, 302)

    def test_delete_asks_for_confirmation_then_deletes(self):
        url = reverse("library:phrase_delete", args=[self.p1.pk])
        self.assertContains(self.client.get(url), "Delete this phrase?")
        self.assertTrue(Phrase.objects.filter(pk=self.p1.pk).exists())
        self.client.post(url)
        self.assertFalse(Phrase.objects.filter(pk=self.p1.pk).exists())

    def test_toggle_active(self):
        self.client.post(reverse("library:phrase_toggle", args=[self.p1.pk]))
        self.p1.refresh_from_db()
        self.assertFalse(self.p1.is_active)

    def test_manage_list_shows_inactive_and_filters_status(self):
        response = self.client.get(reverse("library:manage_phrases"))
        self.assertContains(response, "Hidden phrase")
        only_inactive = self.client.get(reverse("library:manage_phrases"), {"status": "inactive"})
        self.assertContains(only_inactive, "Hidden phrase")
        self.assertNotContains(only_inactive, "Lami kaayo!")


class AdminCategoryCrudTests(LibraryTestBase):
    def setUp(self):
        super().setUp()
        self.login("admin")

    def test_create_update(self):
        self.client.post(reverse("library:category_create"), {"name": "Small talk", "description": "Greetings"})
        cat = Category.objects.get(name="Small talk")
        self.client.post(reverse("library:category_update", args=[cat.pk]), {"name": "Small Talk", "description": "Hi"})
        cat.refresh_from_db()
        self.assertEqual(cat.name, "Small Talk")

    def test_duplicate_name_rejected_case_insensitive(self):
        response = self.client.post(reverse("library:category_create"), {"name": "school", "description": ""})
        self.assertContains(response, "already exists")

    def test_cannot_delete_category_with_phrases(self):
        response = self.client.post(reverse("library:category_delete", args=[self.school.pk]), follow=True)
        self.assertContains(response, "still has phrases")
        self.assertTrue(Category.objects.filter(pk=self.school.pk).exists())

    def test_can_delete_empty_category(self):
        empty = Category.objects.create(name="Empty")
        self.client.post(reverse("library:category_delete", args=[empty.pk]))
        self.assertFalse(Category.objects.filter(pk=empty.pk).exists())


class DashboardTests(LibraryTestBase):
    def test_student_dashboard_links_to_library(self):
        self.login("student")
        response = self.client.get(reverse("accounts:student_dashboard"))
        self.assertContains(response, reverse("library:phrase_list"))
        self.assertNotContains(response, reverse("library:manage_phrases"))

    def test_admin_dashboard_shows_library_stats_and_link(self):
        self.login("admin")
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertContains(response, reverse("library:manage_phrases"))
        self.assertEqual(response.context["total_phrases"], 3)
        self.assertEqual(response.context["total_categories"], 2)
