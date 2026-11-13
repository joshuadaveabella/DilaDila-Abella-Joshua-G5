# Dila-Dila: A Cebuano Phrase-Learning and Practice System for CIT-U Transferee Students

CSIT327 – Information Management 2 · Abella, Joshua Dave G. · Section G5

Full-stack Django (templates) + PostgreSQL/Supabase.

## Phase 1 – Account Feature
- Registration with validation (required fields, email format, unique email, password confirmation, Django password rules) and hashed passwords
- Login (by email) / Logout, with error and success messages
- Role-based dashboards: **Student** and **Admin** (opening the other role's URL returns 403)
- Profile: view and edit your own name, email and home region
- Protected pages use `@login_required` / `@role_required`

## Setup
```bash
git clone <repo-url>
cd DilaDila-Abella-Joshua-G5
python -m venv venv
venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt

copy .env.example .env         # macOS/Linux: cp .env.example .env
# edit .env: set SECRET_KEY and DATABASE_URL (local PostgreSQL or Supabase)

python manage.py migrate
python manage.py createsuperuser   # creates an ADMIN account
python manage.py runserver
```
Open http://127.0.0.1:8000/ . Students register themselves at `/accounts/register/`; admins are created with `createsuperuser`.

## Tests
```bash
python manage.py test accounts
```

## Database
The custom user model maps to the `users` table from the SDD (`user_id`, `email`, `password_hash`, `full_name`, `home_region`, `role`, `created_at`) with a CHECK constraint on `role` (BR-02) and a UNIQUE `email` (BR-01).
