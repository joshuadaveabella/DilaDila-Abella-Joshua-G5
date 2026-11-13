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
