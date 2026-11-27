# Dila-Dila: A Cebuano Phrase-Learning and Practice System for CIT-U Transferee Students

CSIT327 – Information Management 2 · Abella, Joshua Dave G. · Section G5

Full-stack Django (templates) + PostgreSQL/Supabase.

## Core feature (Project Development 2): Phrase Library and Personal Phrasebook

**Admins** build the library: they add, edit, deactivate and delete categories and phrases (Cebuano text, English translation, optional other-language translation and audio link).

**Students** browse the library, search by Cebuano or English text, filter by category, and save phrases to their **personal phrasebook**. They can also add their own phrases with a note (for example, something heard in the canteen), edit them, and delete them. Students only see and change their own entries; admins get a read-only overview of all phrasebooks.

| Part | Where |
|---|---|
| Tables | `categories`, `phrases`, `phrasebook_entries` (linked to `users`) |
| Library app | `library/` (models, forms, views, URLs, tests) |
| Phrasebook app | `phrasebook/` (models, forms, views, URLs, tests) |
| Pages | `/library/`, `/library/manage/`, `/phrasebook/`, `/phrasebook/all/` (admin) |

Database rules: unique Cebuano text per category, a CHECK that every phrasebook entry has a library phrase or custom text, a unique (user, phrase) pair, and PROTECT on foreign keys so used phrases and non-empty categories cannot be deleted.

### Standard features (Project Development 1)
Registration, login/logout, role-based dashboards (Student / Admin) and user profile. Still working.

## Setup
```bash
git clone https://github.com/joshuadaveabella/DilaDila-Abella-Joshua-G5.git
cd DilaDila-Abella-Joshua-G5
python -m venv venv
venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt

copy .env.example .env         # macOS/Linux: cp .env.example .env
# edit .env: set SECRET_KEY and DATABASE_URL (local PostgreSQL or the Supabase *Session pooler* string)

python manage.py migrate
python manage.py seed_demo         # test accounts + sample phrases (optional)
python manage.py runserver
```
Open http://127.0.0.1:8000/

### Test accounts (created by `seed_demo`)
| Role | Email | Password |
|---|---|---|
| Admin | admin@dila.test | DilaDila#Test2026 |
| Student | student@dila.test | DilaDila#Test2026 |

New students can also register at `/accounts/register/`. Extra admins: `python manage.py createsuperuser`.

## Tests
```bash
python manage.py test                        # whole suite (about 160 tests)
python manage.py test library                # one app
python manage.py test library.tests_core     # the core-feature suite (valid/invalid input, login, access control)
```
Tests run against PostgreSQL. Django creates a temporary `test_` database, so the database user in `DATABASE_URL` must be allowed to create databases. Supabase usually does not allow this, so for tests use a local PostgreSQL by putting these two lines in `.env`:
```
USE_LOCAL_TEST_DB=True
LOCAL_TEST_DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/dila_dila_test
```

| Test file | What it checks |
|---|---|
| `library/tests.py`, `phrasebook/tests.py` | PD2 feature behaviour, audio upload |
| `library/tests_core.py` | Core-feature suite, route protection of every URL |
| `library/tests_integrity.py` | DB constraints, on_delete, atomic saves, query counts |
| `accounts/tests.py`, `accounts/tests_hardening.py` | Standard features, safe redirects, CSRF, error pages, settings |

## Configuration (`.env`, never committed)
| Variable | Meaning |
|---|---|
| `SECRET_KEY` | **Required.** The app refuses to start without a real value. |
| `DEBUG` | `False` unless set to `True` (use `True` only on your own computer). |
| `ALLOWED_HOSTS` | Comma-separated hosts, default `localhost,127.0.0.1`. |
| `DATABASE_URL` | PostgreSQL / Supabase *Session pooler* string. |
| `SECURE_COOKIES` | `True` on HTTPS hosting. |
| `EMAIL_*` | Optional SMTP settings. By default password-reset emails print in the terminal. |

Generate a key: `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`

## Branching
`main` (stable) ← `develop` (integration) ← work branches (`feature/...` in PD2; `fix/...`, `hardening/...`, `test/...` in PD3). Work is merged through Pull Requests; merged branches are kept.

## Database design
Tables follow the SDD (`docs/` holds the PD2 and PD3 reports and `SDD-Addendum-PD3.md`). Small differences from the SDD are listed in the report under Outstanding Issues.
