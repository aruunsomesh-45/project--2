# Architecture Context — Learning Profile & Teaching Intelligence Platform

## Relationship to Other Files

This is the **technical ground truth**. `ai-workflow-rules.md` tells the agent to check every change against the invariants and stage boundaries defined here. `code-standards.md` implements the function blocks against the schema and app structure defined here. `ui-context.md` styles the templates this file's folder structure lists. `project-overview.md` is the product reason this structure exists. `progress-tracker.md` logs work against the stages and units defined here.

---

## Stack

| Layer     | Technology                  | Role   |
| --------- | ---------------------------- | ------ |
| Backend   | Django (Python)               | Auth, business logic, views, scoring engine, study plan generation |
| Frontend  | HTML, CSS, Vanilla JavaScript  | Templates, forms, progress indicators, study timer, interactivity |
| Database  | Supabase (PostgreSQL)          | Primary data storage for all entities below |
| Auth      | Supabase Auth (integrated with Django) | Registration/login for students, teachers, and admin |
| AI (Stage 4 only) | External LLM provider (TBD) | AI teaching suggestions, AI study plan generation, adaptive learning |

## System Boundaries (File Structure)

```
/project_root
  manage.py
  requirements.txt
  /config                        → Django project settings (settings.py, urls.py, wsgi.py, asgi.py)

  /accounts                      → Stage 1: Django app — registration/login for student, teacher, admin; role management
    models.py
    views.py
    urls.py
    forms.py

  /assessment                    → Stage 1: Django app — question bank, assessment UI flow, auto-save, scoring engine, learning profiles
    models.py
    views.py
    urls.py
    scoring.py                   → Scoring engine logic, isolated from views

  /classroom                     → Stage 2: Django app — teacher dashboard, class creation, class codes, roster, student profile view (teacher-facing)
    models.py
    views.py
    urls.py

  /study_plans                   → Stage 3: Django app — study plan generator, tasks, completion tracking, progress dashboard, streaks, teacher notes
    models.py
    views.py
    urls.py
    generator.py                 → Rule-based plan generation logic, isolated from views

  /ai_engine                     → Stage 4: Django app — AI teacher assistant, AI study plan, adaptive learning, AI tutor. Not started until Stages 1–3 are complete.
    models.py
    views.py
    urls.py
    prompts.py                   → Documented prompt templates for each AI feature

  /static
    /css                         → Vanilla CSS, one file per major screen/component group
    /js                          → Vanilla JS: auto-save, progress indicator, study timer, class-code copy, etc.

  /templates
    base.html                    → Shared layout, header/nav per role
    /accounts
    /assessment
    /classroom
    /study_plans
    /ai_engine

  /supabase
    /migrations                  → SQL migration files (schema below), one file per stage
```

Django app boundaries above map **directly to roadmap stages** — `accounts` and `assessment` are Stage 1, `classroom` is Stage 2, `study_plans` is Stage 3, `ai_engine` is Stage 4. Do not put Stage 2+ logic inside `accounts` or `assessment` once those apps are considered complete for their stage.

## Storage Model

- **Supabase Database**: all relational data — user profiles, roles, class rosters, assessment questions/responses, learning profiles, study plans, tasks, progress, and (Stage 4) AI interaction logs.
- **Supabase Storage**: not required for v1–v3. If Stage 4 or later introduces file uploads (e.g., a student uploading work for review), that's the point to introduce it — do not add it speculatively now.

## Auth and Access Model

- Authentication is handled via **Supabase Auth**, integrated with Django. Django verifies the Supabase session/JWT on protected routes rather than reimplementing auth.
- Three roles: `student`, `teacher`, `admin`. Role is stored on the user's profile record (see schema) and checked server-side on every view — never inferred from which URL was hit or hidden purely via navigation/UI.
- **Row Level Security (RLS)** is applied in Supabase:
  - A student can only read/write their own assessment responses, learning profile, and study plan tasks.
  - A teacher can only read data for students enrolled in one of their classes (join through `class_students`).
  - Admin has broader read access for platform oversight; exact admin scope is defined when the admin app is actually built (not detailed further here since Stage 1 only requires admin auth to exist, not an admin feature set).
- Django backend re-validates role/ownership at the view layer even where RLS also applies — defense in depth, and necessary because some business logic (e.g., "can this teacher see this student") is easier to express clearly in Django than purely in SQL policies.

## Database Schema (Supabase / Postgres)

Tables are grouped and labeled by the stage that introduces them. Only build a table when its stage is reached, per `progress-tracker.md`.

### Stage 1 — Foundation + Student Assessment

```sql
-- Extends Supabase's built-in auth.users with role + profile info
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role text not null check (role in ('student', 'teacher', 'admin')),
  full_name text not null,
  email text not null,
  created_at timestamptz not null default now()
);

create table assessment_questions (
  id uuid primary key default gen_random_uuid(),
  dimension text not null,             -- e.g. 'Analytical Thinking', 'Time Management'
  question_text text not null,
  question_type text not null check (question_type in ('likert', 'multiple_choice')),
  options jsonb,                        -- null for likert; array of choices for multiple_choice
  display_order integer not null,
  created_at timestamptz not null default now()
);

create table assessment_responses (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references profiles(id) on delete cascade,
  question_id uuid not null references assessment_questions(id) on delete cascade,
  answer_value jsonb not null,          -- numeric for likert, selected option for multiple_choice
  answered_at timestamptz not null default now(),

  constraint unique_student_question unique (student_id, question_id)  -- one answer per question, auto-save overwrites
);

create table learning_profiles (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null unique references profiles(id) on delete cascade,
  archetype text not null,              -- e.g. 'The Problem Solver'
  dimension_scores jsonb not null,      -- { "Analytical Thinking": 88, "Time Management": 52, ... }
  strengths jsonb not null,             -- array of strings
  challenges jsonb not null,            -- array of strings
  recommendations jsonb not null,       -- array of strings
  completed_at timestamptz not null default now()
);
```

### Stage 2 — Teacher Intelligence Platform

```sql
create table classes (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references profiles(id) on delete cascade,
  name text not null,
  class_code text not null unique,      -- short, shareable code students use to join
  created_at timestamptz not null default now()
);

create table class_students (
  class_id uuid not null references classes(id) on delete cascade,
  student_id uuid not null references profiles(id) on delete cascade,
  joined_at timestamptz not null default now(),

  primary key (class_id, student_id)
);
```

Teacher-facing student profile view (per PRD mockup) is computed by joining `learning_profiles` + `class_students` — no new table needed for it.

### Stage 3 — Personalized Study Plan + Progress

```sql
create table study_plans (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references profiles(id) on delete cascade,
  teacher_id uuid not null references profiles(id) on delete cascade,
  subject text not null,
  goal text not null,
  exam_date date,
  available_study_time text,            -- e.g. '30 min/day', kept as free text unless a structured format is needed later
  difficulty text not null check (difficulty in ('easy', 'medium', 'hard')),
  created_at timestamptz not null default now()
);

create table study_plan_tasks (
  id uuid primary key default gen_random_uuid(),
  study_plan_id uuid not null references study_plans(id) on delete cascade,
  scheduled_day date not null,
  title text not null,
  duration_minutes integer not null,
  display_order integer not null,
  is_completed boolean not null default false,
  completed_at timestamptz
);

create table teacher_notes (
  id uuid primary key default gen_random_uuid(),
  study_plan_id uuid not null references study_plans(id) on delete cascade,
  teacher_id uuid not null references profiles(id) on delete cascade,
  note_text text not null,
  created_at timestamptz not null default now()
);
```

**Progress dashboard values (tasks completed/remaining, study time, streak, weekly %) are computed from `study_plan_tasks` at read time — not stored redundantly.** Streak logic and the exact weekly-progress formula must be documented in `code-standards.md` once implemented, since the PRD doesn't fully specify them.

### Stage 4 — AI + Adaptive Learning

```sql
create table ai_teaching_suggestions (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references profiles(id) on delete cascade,
  student_id uuid not null references profiles(id) on delete cascade,
  topic text not null,                  -- e.g. 'Python loops'
  ai_response jsonb not null,           -- structured recommended approach
  created_at timestamptz not null default now()
);

create table profile_snapshots (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references profiles(id) on delete cascade,
  dimension_scores jsonb not null,      -- snapshot of scores at this point in time
  snapshot_date date not null,

  constraint unique_student_snapshot_date unique (student_id, snapshot_date)
);
```

`profile_snapshots` is what makes adaptive learning possible — periodic snapshots let the system compare "initial assessment" vs. "30 days later" as shown in the PRD. Exact snapshot cadence (e.g., weekly, on each re-assessment) is an open question to resolve when Stage 4 begins — do not decide it now.

## Invariants

1. No complex business logic in HTML templates — scoring, plan generation, and AI orchestration live in Python (`scoring.py`, `generator.py`, `prompts.py`), not in templates or inline JS.
2. Database schema changes are managed via versioned SQL migrations in `/supabase/migrations` — one migration file per stage/unit, never edited retroactively once applied.
3. Vanilla JS handles interactions (auto-save triggers, timer, progress indicator animation via CSS transitions); Django handles all business logic and data access. No frontend framework.
4. Backend strictly validates all incoming data (assessment answers, class codes, study plan inputs) before writing to Supabase.
5. Role checks happen server-side on every view, per the Auth and Access Model above — never client-side only.
6. Stage 4 tables/apps are not created until Stage 3 is marked complete in `progress-tracker.md`.
