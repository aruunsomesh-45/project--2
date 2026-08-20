# Code Standards — Learning Profile & Teaching Intelligence Platform

## Relationship to Other Files

This file defines **how to write** the code that implements the structure in `architecture.md`, styled per `ui-context.md`, within the process rules of `ai-workflow-rules.md`. The **Function Behavior Blocks** section is the detailed spec for each core piece of logic, organized by stage — build and reference only the blocks for the current stage per `progress-tracker.md`.

---

## General

- Keep Django views small and delegate business logic to services/utils (`scoring.py`, `generator.py`, `prompts.py`) — a view should validate input, call a function, and render/redirect.
- Fix root causes, do not layer workarounds.
- Maintain a clean separation between Django backend rendering and frontend JS logic — JS handles DOM/UX only (auto-save triggers, timers, animations), never business rules.

## Python & Django

- Use PEP 8 standards and type hinting where applicable.
- Use Django ORM for queries, falling back to the Supabase client only for Supabase-specific features (e.g., Auth, RLS-aware queries where relevant).
- Keep URLs RESTful and intuitive, namespaced per app (`accounts:login`, `assessment:take`, `classroom:dashboard`, `study_plans:today`, `ai_engine:suggest`).
- Use CSRF protection on all forms.
- Every Django app listed in `architecture.md` owns its own `models.py`/`views.py`/`urls.py` — do not cross-import business logic between apps beyond what's necessary (e.g., `study_plans` reading a student's `learning_profiles` row is fine; `classroom` writing directly to `assessment` tables is not).

## Frontend (HTML/CSS/JS)

- Write semantic HTML5.
- Use vanilla CSS with custom properties (CSS variables) sourced from `ui-context.md`; avoid heavy CSS frameworks.
- Keep JavaScript modular — one small script per concern (`autosave.js`, `timer.js`, `progress-indicator.js`, `class-code.js`).
- Use data attributes (`data-*`) for passing context from Django templates to JavaScript (e.g., `data-question-id`, `data-plan-id`).
- No animation library — simple CSS transitions are sufficient for progress bars, streak counters, and state changes.

## Supabase

- Use Supabase Row Level Security to enforce the access model defined in `architecture.md`.
- Sync auth state between Supabase and Django sessions consistently — a logged-out Supabase session must not leave a Django view still treating the user as authenticated.
- Use Supabase Storage only if/when file uploads are actually introduced (not currently in scope).

## Styling

- Use CSS custom property tokens — no hardcoded hex values.
- Follow the design system defined in `ui-context.md`.

## Data and Storage

- Metadata and structured records (profiles, questions, responses, classes, plans, tasks) belong in the Supabase database.
- No large binary/generated content exists in the current scope — revisit storage conventions only if that changes.

## File Organization

- `<app>/models.py` — data models for that app's domain
- `<app>/views.py` — request handlers
- `<app>/urls.py` — app-specific routes
- `static/css/` — vanilla CSS files
- `static/js/` — vanilla JS scripts
- `templates/<app>/` — templates scoped to that app

---

## Function Behavior Blocks

Each block below is the authoritative spec for that piece of logic. Build only the blocks belonging to the current stage, per `progress-tracker.md`.

### STAGE 1 BLOCKS

#### Block: Auth (Registration & Login — Student, Teacher, Admin)

- **Trigger**: user visits registration or login page from the landing page.
- **Registration**: collects name, email, password, and role (student/teacher — admin accounts are provisioned separately, not self-registered, since there's no public "sign up as admin" path). Creates a Supabase Auth user, then a corresponding row in `profiles` with the chosen role.
- **Login**: authenticates against Supabase Auth; on success, Django establishes a session tied to the Supabase user, and every subsequent view reads `profiles.role` to determine access.
- **Role-based redirect after login**: student → onboarding/assessment; teacher → teacher dashboard; admin → admin area (scope TBD, out of detailed spec for Stage 1 beyond "can log in").
- **Server-side enforcement**: every view in every app checks `request.user`'s role via `profiles` before rendering — a student hitting a teacher URL gets redirected/denied, not shown a broken page.
- **Verification**: manually test registering as each of the three roles, logging in/out, and confirming role-based redirect and access denial across roles.

#### Block: Student Onboarding

- **Trigger**: first login as a student, before the assessment begins.
- **Behavior**: a short intro screen (per PRD's landing → register → onboarding → assessment flow) — collects any minimal context needed before the assessment (exact fields TBD if not in PRD; if none are specified, this can be a simple "here's what to expect" screen with a "Start Assessment" button — do not invent extra data collection not called for).

#### Block: Assessment Question Flow

- **Trigger**: student starts or resumes the assessment.
- **Behavior**:
  1. Questions are served from `assessment_questions`, ordered by `display_order`.
  2. One question (or a small group) is shown at a time, with a **progress indicator** reflecting `answered questions / total questions`.
  3. Each answer is **auto-saved** immediately on selection/input (JS triggers a save call per answer, not only on final submit) — writes to `assessment_responses`, upserting on `(student_id, question_id)` so re-answering overwrites cleanly.
  4. If a student leaves and returns, previously answered questions are pre-filled from `assessment_responses` and they resume where they left off.
  5. On the final question, a "Submit" action triggers the scoring engine.
- **Verification**: manually test answering a few questions, closing the tab, returning, and confirming answers persisted and progress resumed correctly.

#### Block: Scoring Engine (`assessment/scoring.py`)

- **Trigger**: student submits the completed assessment.
- **Behavior**:
  1. Read all of the student's `assessment_responses`.
  2. Aggregate answers per `dimension` (e.g., Analytical Thinking, Practical Learning, Focus, Motivation, Time Management) into a 0–100 score per dimension. The exact aggregation formula (e.g., normalized average of likert responses) must be explicitly written and documented here once implemented — this is a deterministic, rule-based calculation in Stages 1–3, not AI-driven.
  3. Map the resulting dimension-score profile to a defined **archetype** (e.g., "The Problem Solver") using a documented rule set (e.g., highest-scoring dimension(s) determine archetype, with defined thresholds/tie-breaks).
  4. Derive `strengths` (highest-scoring dimensions), `challenges` (lowest-scoring dimensions), and `recommendations` (static text mapped per archetype/dimension combination — not generated dynamically in Stage 1).
  5. Write the result to `learning_profiles` (one row per student, upserted if retaken).
- **Output shown to student**: archetype name, dimension scores, strengths, challenges, recommendations — per the PRD's example "Learning Profile" screen.
- **Verification**: manually test with a few different answer patterns and confirm the resulting archetype/scores are consistent and explainable from the documented rules — no black-box scoring.

### STAGE 2 BLOCKS

#### Block: Class Creation & Class Code

- **Trigger**: teacher clicks "Create Class" on their dashboard.
- **Behavior**: teacher provides a class name; system generates a short, unique, human-shareable `class_code` (e.g., 6 characters, uppercase alphanumeric, checked for uniqueness against existing `classes` rows before saving) and creates the `classes` row with `teacher_id` set to the current teacher.
- **Verification**: create two classes and confirm codes never collide; confirm the class only appears on its creating teacher's dashboard.

#### Block: Student Joins a Class

- **Trigger**: student enters a class code (location in the student UI TBD if not specified — reasonable default is a "Join a Class" field on the student dashboard).
- **Behavior**: validate the code exists in `classes`; if valid, insert into `class_students` (idempotent — joining twice should not error or duplicate). If invalid, show a clear "Class code not found" error.
- **Verification**: join with a valid code, an invalid code, and attempt to join the same class twice.

#### Block: Teacher Dashboard — Student List & Profile View

- **Trigger**: teacher opens a class from their dashboard.
- **Behavior**: list students via `class_students` joined to `profiles`; clicking a student shows their `learning_profiles` row rendered as the PRD's mockup (archetype, dimension scores as percentages, strengths, challenges, recommended teaching approaches).
- **Access rule**: a teacher can only view students who are in `class_students` for a class where `classes.teacher_id` = the current teacher. Enforced server-side, not just by not showing a link.
- **Verification**: confirm Teacher A cannot view Teacher B's students' profiles even by guessing a URL/ID.

### STAGE 3 BLOCKS

#### Block: Study Plan Generator (`study_plans/generator.py`)

- **Trigger**: teacher selects a student, subject, goal, exam date, available study time, and difficulty, then generates a plan.
- **Behavior**: a **rule-based** generator (no AI in Stage 3) that distributes study tasks across the available days between now and the exam date, respecting the stated available study time and difficulty, producing a day-by-day list of tasks (title + duration) similar to the PRD's Monday–Friday example. The exact distribution algorithm (how tasks are split, how difficulty affects task count/length) must be explicitly written and documented here once implemented.
- **Output**: a `study_plans` row plus its `study_plan_tasks` rows.
- **Teacher can then**: edit individual tasks, assign the plan (making it visible to the student), and later add `teacher_notes`.
- **Verification**: generate a plan for a few different date ranges/difficulties and confirm the task distribution is sensible and reproducible from the documented rules.

#### Block: Student Study Plan View — Today's Tasks, Timer, Completion

- **Trigger**: student opens their study plan.
- **Behavior**: shows today's tasks from `study_plan_tasks` filtered by `scheduled_day = today`; each task can be marked complete (`is_completed = true`, `completed_at = now()`); an optional study timer (client-side JS) can be started per task for the student's own reference — the timer does not gate completion (a student can mark complete without using the timer).
- **Verification**: mark a task complete and confirm it reflects immediately in the progress dashboard block below.

#### Block: Progress Dashboard

- **Trigger**: student or teacher views progress for a plan.
- **Behavior**: computed (not stored) from `study_plan_tasks`:
  - Tasks Completed / Tasks Remaining: simple counts of `is_completed`.
  - Study Time: sum of `duration_minutes` for completed tasks.
  - Weekly Progress %: completed tasks in the current week ÷ total tasks scheduled in the current week.
  - Current Streak: consecutive days (up to today) with at least one task marked complete. Exact edge-case behavior (e.g., does a day with zero scheduled tasks break the streak?) must be explicitly decided and documented here once implemented — default assumption: only days with at least one *scheduled* task count toward streak continuity.
- **Verification**: manually walk through a week of test completions and confirm each displayed number matches manual calculation.

### STAGE 4 BLOCKS (do not build until Stages 1–3 are complete)

#### Block: AI Teacher Assistant (`ai_engine/prompts.py`)

- **Trigger**: teacher asks a free-text question like "How should I teach this student Python loops?"
- **Behavior**: the request is combined with the student's `learning_profiles` data (archetype, dimension scores, strengths, challenges) into a documented prompt template, sent to the configured LLM provider, and the structured response (numbered recommended approach, per the PRD example) is shown to the teacher and optionally saved to `ai_teaching_suggestions`.
- **Advisory only**: this suggestion is never auto-applied to a study plan — the teacher must explicitly act on it (e.g., by manually creating/editing a plan).

#### Block: AI Study Plan Generation

- **Trigger**: teacher opts to generate a plan "with AI" instead of (or in addition to) the rule-based generator from Stage 3.
- **Behavior**: combines student profile + subject + exam date + current performance data into a prompt, producing a proposed plan the teacher reviews and can edit before assigning — using the same `study_plans`/`study_plan_tasks` tables as Stage 3, just a different generation path.

#### Block: Adaptive Learning

- **Trigger**: periodic snapshot (cadence TBD — see `architecture.md` note on `profile_snapshots`) or teacher-initiated re-assessment.
- **Behavior**: compares the current dimension scores to a prior `profile_snapshots` row for the same student; if a meaningful change is detected (threshold TBD), the next generated study plan is adjusted accordingly. Exact "meaningful change" threshold and adjustment logic must be explicitly documented here once this block is actually built — do not leave this as an implicit AI judgment call.

#### Block: AI Student Tutor

- **Trigger**: student asks a question or requests practice within a subject.
- **Behavior**: uses the student's learning profile to shape the explanation style (e.g., diagrams + short exercises for one archetype, theory + detailed explanations for another), per the PRD's example. Requires a documented prompt template per archetype/style, and a defined feedback loop (how the student's response quality feeds back into their profile, if at all — TBD when this block is reached).
