from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.urls import reverse

from .models import User

GOOD_PASSWORD = "Bisaya-Learner-2026"


def make_student(email="student@example.com", password=GOOD_PASSWORD, **extra):
    return User.objects.create_user(email=email, password=password, full_name="Test Student", **extra)


def make_admin(email="admin@example.com", password=GOOD_PASSWORD):
    return User.objects.create_superuser(email=email, password=password, full_name="Test Admin")


class DatabaseTests(TestCase):
    def test_uses_postgresql(self):
        self.assertEqual(connection.vendor, "postgresql")

    def test_role_check_constraint_rejects_invalid_role(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(email="bad@example.com", password=GOOD_PASSWORD, full_name="Bad", role="HACKER")


class RegistrationTests(TestCase):
    def post(self, **overrides):
        data = {
            "full_name": "Maria Santos",
            "email": "maria@example.com",
            "home_region": "Hiligaynon",
            "password1": GOOD_PASSWORD,
            "password2": GOOD_PASSWORD,
        }
        data.update(overrides)
        return self.client.post(reverse("accounts:register"), data)

    def test_page_loads(self):
        self.assertEqual(self.client.get(reverse("accounts:register")).status_code, 200)

    def test_successful_registration_creates_student_with_hashed_password(self):
        response = self.post()
        self.assertRedirects(response, reverse("accounts:login"))
        user = User.objects.get(email="maria@example.com")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertNotEqual(user.password, GOOD_PASSWORD)
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertTrue(user.check_password(GOOD_PASSWORD))

    def test_success_message_shown(self):
        response = self.client.post(
            reverse("accounts:register"),
            {"full_name": "Maria", "email": "m@example.com", "password1": GOOD_PASSWORD, "password2": GOOD_PASSWORD},
            follow=True,
        )
        self.assertContains(response, "Account created")

    def test_required_fields(self):
        response = self.post(full_name="", email="")
        self.assertEqual(User.objects.count(), 0)
        self.assertContains(response, "This field is required")

    def test_invalid_email_format(self):
        response = self.post(email="not-an-email")
        self.assertEqual(User.objects.count(), 0)
        self.assertContains(response, "valid email")

    def test_duplicate_email_rejected_case_insensitive(self):
        make_student(email="maria@example.com")
        response = self.post(email="MARIA@Example.com")
        self.assertEqual(User.objects.count(), 1)
        self.assertContains(response, "already exists")

    def test_password_mismatch(self):
        response = self.post(password2="Different-Pass-2026")
        self.assertEqual(User.objects.count(), 0)
        self.assertContains(response, "do not match")

    def test_weak_password_rejected(self):
        response = self.post(password1="12345678", password2="12345678")
        self.assertEqual(User.objects.count(), 0)
        self.assertContains(response, "error")

    def test_cannot_self_register_as_admin(self):
        self.post(role="ADMIN")
        self.assertEqual(User.objects.get(email="maria@example.com").role, User.Role.STUDENT)


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.admin = make_admin()

    def login(self, email, password=GOOD_PASSWORD):
        return self.client.post(reverse("accounts:login"), {"username": email, "password": password})

    def test_valid_login_redirects_to_dashboard(self):
        response = self.login("student@example.com")
        self.assertRedirects(response, reverse("accounts:dashboard"), fetch_redirect_response=False)

    def test_login_is_case_insensitive_on_email(self):
        response = self.login("STUDENT@example.com")
        self.assertEqual(response.status_code, 302)

    def test_invalid_credentials_show_error(self):
        response = self.login("student@example.com", "wrong-password")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password")

    def test_logout_ends_session(self):
        self.login("student@example.com")
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))
        # Protected page now redirects to login
        again = self.client.get(reverse("accounts:profile"))
        self.assertEqual(again.status_code, 302)

    def test_logged_out_users_redirected_from_protected_pages(self):
        for name in ["dashboard", "student_dashboard", "admin_dashboard", "profile", "profile_edit"]:
            url = reverse(f"accounts:{name}")
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}", msg_prefix=name)


class RoleDashboardTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.admin = make_admin()

    def test_student_lands_on_student_dashboard(self):
        self.client.login(username="student@example.com", password=GOOD_PASSWORD)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertRedirects(response, reverse("accounts:student_dashboard"))

    def test_admin_lands_on_admin_dashboard(self):
        self.client.login(username="admin@example.com", password=GOOD_PASSWORD)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertRedirects(response, reverse("accounts:admin_dashboard"))

    def test_student_cannot_open_admin_dashboard(self):
        self.client.login(username="student@example.com", password=GOOD_PASSWORD)
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_open_student_dashboard(self):
        self.client.login(username="admin@example.com", password=GOOD_PASSWORD)
        response = self.client.get(reverse("accounts:student_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_each_dashboard_shows_role_content(self):
        self.client.login(username="student@example.com", password=GOOD_PASSWORD)
        self.assertContains(self.client.get(reverse("accounts:student_dashboard")), "Phrase library")
        self.client.logout()
        self.client.login(username="admin@example.com", password=GOOD_PASSWORD)
        self.assertContains(self.client.get(reverse("accounts:admin_dashboard")), "Total users")


class ProfileTests(TestCase):
    def setUp(self):
        self.user = make_student()
        self.other = make_student(email="other@example.com")
        self.client.login(username="student@example.com", password=GOOD_PASSWORD)

    def test_view_own_profile(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "student@example.com")
        self.assertNotContains(response, "other@example.com")

    def test_update_profile(self):
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {"full_name": "New Name", "email": "new@example.com", "home_region": "Waray"},
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "New Name")
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(self.user.home_region, "Waray")

    def test_cannot_take_another_users_email(self):
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {"full_name": "Test Student", "email": "OTHER@example.com", "home_region": ""},
        )
        self.assertContains(response, "already exists")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "student@example.com")

    def test_can_keep_own_email_when_editing(self):
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {"full_name": "Changed", "email": "student@example.com", "home_region": ""},
        )
        self.assertRedirects(response, reverse("accounts:profile"))

    def test_cannot_change_own_role_through_profile_form(self):
        self.client.post(
            reverse("accounts:profile_edit"),
            {"full_name": "Test Student", "email": "student@example.com", "home_region": "", "role": "ADMIN"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.STUDENT)

    def test_profile_urls_have_no_user_id(self):
        # Only the logged-in user's own record is ever used, so nobody else's profile can be reached.
        self.assertEqual(reverse("accounts:profile"), "/accounts/profile/")


# ---------------------------------------------------------------------------
# ISS-04: profile photo, change password, forgot password
# ---------------------------------------------------------------------------
import io
import os
import shutil
import tempfile

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image


def image_bytes(fmt="PNG", size=(40, 40), pad=0):
    buffer = io.BytesIO()
    Image.new("RGB", size, "green").save(buffer, fmt)
    return buffer.getvalue() + b"\x00" * pad


class ProfilePhotoTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.user = make_student()
        self.client.login(username="student@example.com", password=GOOD_PASSWORD)

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def post(self, upload, **extra):
        data = {"full_name": "Test Student", "email": "student@example.com", "home_region": ""}
        if upload is not None:
            data["profile_photo"] = upload
        data.update(extra)
        return self.client.post(reverse("accounts:profile_edit"), data)

    def test_valid_photo_saved_with_random_name(self):
        response = self.post(SimpleUploadedFile("my face.png", image_bytes(), content_type="image/png"))
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_photo.name.startswith("profile_photos/"))
        self.assertNotIn("my face", self.user.profile_photo.name)
        self.assertContains(self.client.get(reverse("accounts:profile")), self.user.profile_photo.url)

    def test_non_image_rejected(self):
        response = self.post(SimpleUploadedFile("evil.png", b"not an image at all", content_type="image/png"))
        self.assertContains(response, "valid image")
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_photo)

    def test_gif_rejected(self):
        response = self.post(SimpleUploadedFile("a.gif", image_bytes("GIF"), content_type="image/gif"))
        self.assertContains(response, "JPEG, PNG or WEBP")

    def test_oversized_photo_rejected(self):
        response = self.post(SimpleUploadedFile("big.png", image_bytes(pad=3 * 1024 * 1024), content_type="image/png"))
        self.assertContains(response, "too large")

    def test_replacing_photo_removes_old_file(self):
        self.post(SimpleUploadedFile("a.png", image_bytes(), content_type="image/png"))
        self.user.refresh_from_db()
        old = self.user.profile_photo.path
        with self.captureOnCommitCallbacks(execute=True):
            self.post(SimpleUploadedFile("b.png", image_bytes(size=(50, 50)), content_type="image/png"))
        self.user.refresh_from_db()
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(self.user.profile_photo.path))

    def test_photo_only_changes_own_account(self):
        other = make_student("other@example.com")
        self.post(SimpleUploadedFile("a.png", image_bytes(), content_type="image/png"))
        other.refresh_from_db()
        self.assertFalse(other.profile_photo)


class ChangePasswordTests(TestCase):
    def setUp(self):
        self.user = make_student()

    def post(self, **extra):
        data = {"old_password": GOOD_PASSWORD, "new_password1": "Another-Strong-Pass-77", "new_password2": "Another-Strong-Pass-77"}
        data.update(extra)
        return self.client.post(reverse("accounts:password_change"), data)

    def test_requires_login(self):
        url = reverse("accounts:password_change")
        self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}")

    def test_success_changes_password_and_keeps_session(self):
        self.client.login(username="student@example.com", password=GOOD_PASSWORD)
        response = self.post()
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Another-Strong-Pass-77"))
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)

    def test_wrong_old_password_rejected(self):
        self.client.login(username="student@example.com", password=GOOD_PASSWORD)
        response = self.post(old_password="wrong")
        self.assertContains(response, "old password was entered incorrectly")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(GOOD_PASSWORD))

    def test_weak_or_mismatched_new_password_rejected(self):
        self.client.login(username="student@example.com", password=GOOD_PASSWORD)
        self.assertContains(self.post(new_password1="12345678", new_password2="12345678"), "error")
        self.assertContains(self.post(new_password2="Different-Pass-1"), "did")


class ForgotPasswordTests(TestCase):
    def setUp(self):
        self.user = make_student()

    def test_known_email_sends_one_reset_email(self):
        response = self.client.post(reverse("accounts:password_reset"), {"email": "student@example.com"})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/password/reset/", mail.outbox[0].body)

    def test_unknown_email_gets_same_response_and_no_email(self):
        response = self.client.post(reverse("accounts:password_reset"), {"email": "nobody@example.com"})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))  # does not reveal if the account exists
        self.assertEqual(len(mail.outbox), 0)

    def test_full_reset_flow(self):
        self.client.post(reverse("accounts:password_reset"), {"email": "student@example.com"})
        link = [line for line in mail.outbox[0].body.splitlines() if "/accounts/password/reset/" in line][0]
        path = "/" + link.split("://", 1)[1].split("/", 1)[1]
        page = self.client.get(path, follow=True)  # Django swaps the token for a session URL
        self.assertContains(page, "Choose a new password")
        response = self.client.post(page.request["PATH_INFO"],
                                    {"new_password1": "Brand-New-Pass-2026", "new_password2": "Brand-New-Pass-2026"})
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Brand-New-Pass-2026"))

    def test_invalid_link_shows_error_page(self):
        response = self.client.get(reverse("accounts:password_reset_confirm", args=["bad", "token"]))
        self.assertContains(response, "Link not valid")

    def test_login_page_links_to_forgot_password(self):
        self.assertContains(self.client.get(reverse("accounts:login")), reverse("accounts:password_reset"))
