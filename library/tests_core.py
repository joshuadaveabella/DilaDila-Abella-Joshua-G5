"""PD3 core-feature test suite (Phrase Library + Personal Phrasebook).

Covers: valid input, invalid input, login required, role checks, and blocked access to another user's record.
Run with:  python manage.py test
"""
from django.test import Client, TestCase
from django.urls import get_resolver, reverse

from accounts.tests import GOOD_PASSWORD, make_admin, make_student
from library.models import Category, Phrase
from phrasebook.models import PhrasebookEntry


class CoreBase(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.student = make_student()
        self.other = make_student(email="other@example.com")
        self.cat = Category.objects.create(name="School")
        self.phrase = Phrase.objects.create(
            category=self.cat, cebuano_text="Asa ang library?", english_translation="Where is the library?"
        )

    def login(self, email):
        self.client.login(username=email, password=GOOD_PASSWORD)


class CoreFeatureTests(CoreBase):
    # 1 valid input
    def test_01_admin_adds_phrase_with_valid_input(self):
        self.login("admin@example.com")
        r = self.client.post(reverse("library:phrase_create"), {
            "category": self.cat.pk, "cebuano_text": "Pila ni?", "english_translation": "How much is this?",
        })
        self.assertRedirects(r, reverse("library:manage_phrases"))
        self.assertTrue(Phrase.objects.filter(cebuano_text="Pila ni?").exists())

    # 2 invalid input
    def test_02_admin_phrase_with_blank_text_is_rejected(self):
        self.login("admin@example.com")
        r = self.client.post(reverse("library:phrase_create"), {
            "category": self.cat.pk, "cebuano_text": "   ", "english_translation": "x",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "This field is required")
        self.assertEqual(Phrase.objects.count(), 1)

    # 3 invalid input (business rule BR-05)
    def test_03_duplicate_phrase_in_same_category_is_rejected(self):
        self.login("admin@example.com")
        r = self.client.post(reverse("library:phrase_create"), {
            "category": self.cat.pk, "cebuano_text": "Asa ang library?", "english_translation": "dup",
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Phrase.objects.count(), 1)

    # 4 login required
    def test_04_anonymous_user_is_redirected_to_login(self):
        for name, args in [("library:phrase_list", []), ("phrasebook:my_phrasebook", []),
                           ("phrasebook:entry_create", []), ("library:phrase_create", []),
                           ("phrasebook:entry_update", [1]), ("library:phrase_delete", [1])]:
            url = reverse(name, args=args)
            self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}", msg_prefix=name)

    # 5 valid input (student)
    def test_05_student_saves_library_phrase(self):
        self.login("student@example.com")
        r = self.client.post(reverse("phrasebook:save_from_library", args=[self.phrase.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(PhrasebookEntry.objects.filter(user=self.student, phrase=self.phrase).exists())

    # 6 invalid input (empty entry)
    def test_06_empty_phrasebook_entry_is_rejected(self):
        self.login("student@example.com")
        r = self.client.post(reverse("phrasebook:entry_create"), {"phrase": "", "custom_text": "", "note": ""})
        self.assertContains(r, "Choose a library phrase or type your own phrase.")
        self.assertEqual(PhrasebookEntry.objects.count(), 0)

    # 7 blocked access to another user's record (edit / delete)
    def test_07_student_cannot_edit_or_delete_another_students_entry(self):
        entry = PhrasebookEntry.objects.create(user=self.other, custom_text="Salamat kaayo")
        self.login("student@example.com")
        self.assertEqual(self.client.get(reverse("phrasebook:entry_update", args=[entry.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("phrasebook:entry_update", args=[entry.pk]),
                                          {"custom_text": "hacked"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("phrasebook:entry_delete", args=[entry.pk])).status_code, 404)
        entry.refresh_from_db()
        self.assertEqual(entry.custom_text, "Salamat kaayo")

    # 8 blocked access: another student's entries never shown in my list
    def test_08_my_phrasebook_lists_only_my_entries(self):
        PhrasebookEntry.objects.create(user=self.other, custom_text="Secret other phrase")
        PhrasebookEntry.objects.create(user=self.student, custom_text="My own phrase")
        self.login("student@example.com")
        r = self.client.get(reverse("phrasebook:my_phrasebook"))
        self.assertContains(r, "My own phrase")
        self.assertNotContains(r, "Secret other phrase")

    # 9 role check
    def test_09_student_cannot_use_admin_pages(self):
        self.login("student@example.com")
        for name, args in [("library:manage_phrases", []), ("library:phrase_create", []),
                           ("library:manage_categories", []), ("phrasebook:all_phrasebooks", [])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 403, name)
        r = self.client.post(reverse("library:phrase_delete", args=[self.phrase.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Phrase.objects.filter(pk=self.phrase.pk).exists())

    # 10 role check the other way
    def test_10_admin_cannot_use_student_phrasebook(self):
        self.login("admin@example.com")
        self.assertEqual(self.client.get(reverse("phrasebook:my_phrasebook")).status_code, 403)

    # 11 invalid id
    def test_11_unknown_ids_return_404_not_500(self):
        self.login("admin@example.com")
        for name in ("library:phrase_update", "library:phrase_delete", "library:category_update"):
            self.assertEqual(self.client.get(reverse(name, args=[999999])).status_code, 404, name)

    # 12 delete via POST only
    def test_12_delete_needs_confirmation_and_post(self):
        self.login("admin@example.com")
        r = self.client.get(reverse("library:phrase_delete", args=[self.phrase.pk]))
        self.assertContains(r, "Cancel")  # confirmation page, nothing deleted
        self.assertTrue(Phrase.objects.filter(pk=self.phrase.pk).exists())
        self.assertEqual(self.client.get(reverse("library:phrase_toggle", args=[self.phrase.pk])).status_code, 405)

    # 13 CSRF
    def test_13_post_without_csrf_token_is_blocked(self):
        c = Client(enforce_csrf_checks=True)
        c.login(username="student@example.com", password=GOOD_PASSWORD)
        r = c.post(reverse("phrasebook:save_from_library", args=[self.phrase.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(PhrasebookEntry.objects.count(), 0)

    # 14 duplicate save is handled
    def test_14_saving_same_phrase_twice_creates_one_entry(self):
        self.login("student@example.com")
        url = reverse("phrasebook:save_from_library", args=[self.phrase.pk])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(PhrasebookEntry.objects.filter(user=self.student).count(), 1)

    # 15 deactivated phrases hidden from students
    def test_15_inactive_phrase_hidden_and_cannot_be_saved(self):
        self.phrase.is_active = False
        self.phrase.save()
        self.login("student@example.com")
        self.assertNotContains(self.client.get(reverse("library:phrase_list")), "Asa ang library?")
        self.assertEqual(self.client.post(reverse("phrasebook:save_from_library", args=[self.phrase.pk])).status_code, 404)


class EveryRouteIsProtectedTests(TestCase):
    """URL introspection: every route outside a small public list must send anonymous users away."""

    PUBLIC = {"home", "login", "register", "password_reset", "password_reset_done", "password_reset_confirm",
              "password_reset_complete"}

    def collect(self, patterns, ns=""):
        for p in patterns:
            if hasattr(p, "url_patterns"):
                new_ns = ns + (p.namespace + ":" if p.namespace else "")
                yield from self.collect(p.url_patterns, new_ns)
            elif p.name:
                yield ns + p.name, p

    def test_non_public_routes_do_not_serve_anonymous_users(self):
        checked = 0
        for full, pattern in self.collect(get_resolver().url_patterns):
            if full.startswith("admin:") or full.split(":")[-1] in self.PUBLIC:
                continue
            route = str(pattern.pattern)
            if "<" in route and "int:" not in route:
                continue
            args = [1] * route.count("<int:")
            url = reverse(full, args=args)
            r = self.client.get(url)
            self.assertIn(r.status_code, (302, 405), f"{full} gave {r.status_code} to an anonymous user")
            if r.status_code == 302:
                self.assertIn(reverse("accounts:login"), r["Location"], full)
            checked += 1
        self.assertGreater(checked, 15)
