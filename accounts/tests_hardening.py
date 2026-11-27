"""Tests for access control, safe redirects, error pages and settings (PD3 hardening)."""

import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from library.models import Category, Phrase

from .tests import GOOD_PASSWORD, make_admin, make_student


class SafeRedirectTests(TestCase):
    def setUp(self):
        make_admin()
        self.phrase = Phrase.objects.create(
            category=Category.objects.create(name="School"), cebuano_text="Asa?", english_translation="Where?"
        )
        self.client.login(username="admin@example.com", password=GOOD_PASSWORD)
        self.url = reverse("library:phrase_toggle", args=[self.phrase.pk])
        self.fallback = reverse("library:manage_phrases")

    def test_external_next_is_ignored(self):
        for bad in ["https://evil.example/", "//evil.example", "http://evil.example", "javascript:alert(1)", "/\\evil.example"]:
            response = self.client.post(self.url, {"next": bad})
            self.assertRedirects(response, self.fallback, fetch_redirect_response=False, msg_prefix=bad)

    def test_internal_next_is_followed(self):
        response = self.client.post(self.url, {"next": "/library/manage/?status=inactive"})
        self.assertRedirects(response, "/library/manage/?status=inactive", fetch_redirect_response=False)


class CsrfTests(TestCase):
    def setUp(self):
        make_student()
        make_admin()
        self.phrase = Phrase.objects.create(
            category=Category.objects.create(name="School"), cebuano_text="Asa?", english_translation="Where?"
        )

    def test_post_without_token_is_rejected_with_friendly_page(self):
        client = Client(enforce_csrf_checks=True)
        client.login(username="admin@example.com", password=GOOD_PASSWORD)
        for url in [reverse("library:phrase_toggle", args=[self.phrase.pk]),
                    reverse("library:phrase_delete", args=[self.phrase.pk]),
                    reverse("phrasebook:save_from_library", args=[self.phrase.pk]),
                    reverse("accounts:profile_edit"), reverse("accounts:logout")]:
            response = client.post(url)
            self.assertEqual(response.status_code, 403, url)
            self.assertContains(response, "This page expired", status_code=403)
        self.assertTrue(Phrase.objects.filter(pk=self.phrase.pk).exists())

    def test_every_post_form_in_templates_has_a_token(self):
        import re
        for path in Path(settings.BASE_DIR, "templates").rglob("*.html"):
            for attrs, body in re.findall(r"<form([^>]*)>(.*?)</form>", path.read_text(), re.S):
                if 'method="post"' in attrs:
                    self.assertIn("csrf_token", body, f"{path} has a POST form without {{% csrf_token %}}")


class MethodTests(TestCase):
    def setUp(self):
        make_admin()
        self.phrase = Phrase.objects.create(
            category=Category.objects.create(name="School"), cebuano_text="Asa?", english_translation="Where?"
        )
        self.client.login(username="admin@example.com", password=GOOD_PASSWORD)

    def test_changing_actions_refuse_get(self):
        self.assertEqual(self.client.get(reverse("library:phrase_toggle", args=[self.phrase.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertTrue(Phrase.objects.filter(pk=self.phrase.pk).exists())

    def test_get_on_delete_url_only_shows_confirmation(self):
        response = self.client.get(reverse("library:phrase_delete", args=[self.phrase.pk]))
        self.assertContains(response, "Delete this phrase?")
        self.assertTrue(Phrase.objects.filter(pk=self.phrase.pk).exists())

    def test_logout_shows_message(self):
        response = self.client.post(reverse("accounts:logout"), follow=True)
        self.assertContains(response, "You have been logged out")


class ErrorPageTests(TestCase):
    def setUp(self):
        make_student()

    def test_custom_404_for_unknown_url(self):
        response = self.client.get("/this/does/not/exist/")
        self.assertContains(response, "Page not found", status_code=404)
        self.assertNotContains(response, "Traceback", status_code=404)

    def test_unknown_ids_give_404_not_a_crash(self):
        self.client.login(username="student@example.com", password=GOOD_PASSWORD)
        for url in [reverse("phrasebook:entry_update", args=[999999]), reverse("phrasebook:entry_delete", args=[999999])]:
            self.assertEqual(self.client.get(url).status_code, 404, url)
        self.assertEqual(self.client.post(reverse("phrasebook:save_from_library", args=[999999])).status_code, 404)

    def test_non_numeric_id_is_404(self):
        self.client.login(username="student@example.com", password=GOOD_PASSWORD)
        self.assertEqual(self.client.get("/phrasebook/abc/edit/").status_code, 404)

    def test_bad_page_and_filter_values_do_not_crash(self):
        self.client.login(username="student@example.com", password=GOOD_PASSWORD)
        for query in ["?page=abc", "?page=99999", "?category=abc", "?category=-1", "?q=%00", "?q=" + "x" * 5000]:
            self.assertEqual(self.client.get(reverse("library:phrase_list") + query).status_code, 200, query)

    def test_custom_500_page_has_no_traceback(self):
        client = Client(raise_request_exception=False)
        client.login(username="student@example.com", password=GOOD_PASSWORD)
        with mock.patch("library.views._page", side_effect=RuntimeError("secret internal detail")):
            response = client.get(reverse("library:phrase_list"))
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "Something went wrong", status_code=500)
        self.assertNotContains(response, "secret internal detail", status_code=500)
        self.assertNotContains(response, "Traceback", status_code=500)

    def test_wrong_role_gets_403_page(self):
        self.client.login(username="student@example.com", password=GOOD_PASSWORD)
        response = self.client.get(reverse("library:manage_phrases"))
        self.assertContains(response, "Access denied", status_code=403)


class SettingsTests(TestCase):
    """Run settings in a fresh Python process so we can control the environment."""

    def run_settings(self, **env_changes):
        env = {**os.environ, **env_changes}
        code = "import django, os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; from django.conf import settings; print('DEBUG=' + str(settings.DEBUG))"
        return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=settings.BASE_DIR, env=env)

    def test_missing_secret_key_is_refused(self):
        result = self.run_settings(SECRET_KEY="")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY is not set", result.stderr)

    def test_placeholder_secret_key_is_refused(self):
        result = self.run_settings(SECRET_KEY="change-me-please")
        self.assertNotEqual(result.returncode, 0)

    def test_debug_follows_env_file(self):
        self.assertIn("DEBUG=True", self.run_settings(SECRET_KEY="x" * 50, DEBUG="True").stdout)
        self.assertIn("DEBUG=False", self.run_settings(SECRET_KEY="x" * 50, DEBUG="False").stdout)
        self.assertIn("DEBUG=False", self.run_settings(SECRET_KEY="x" * 50, DEBUG="yes").stdout)  # anything but True is off

    def test_security_headers_present(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_double_submit_script_is_loaded(self):
        self.assertContains(self.client.get(reverse("accounts:login")), "js/forms.js")
