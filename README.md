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
python manage.py test
```
Runs against PostgreSQL (Django creates a temporary `test_` database, so your `DATABASE_URL` user needs permission to create databases; use a local PostgreSQL for this).

## Branching
`main` (stable) ← `develop` (integration) ← `feature/phrase-library`, `feature/personal-phrasebook`. Work is merged through Pull Requests.

## Database design
Tables follow the SDD (`docs/` holds the PD2 completion report). Small differences from the SDD are listed in the report under Outstanding Issues.
