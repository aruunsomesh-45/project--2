# Progress Tracker — Learning Profile & Teaching Intelligence Platform

## Relationship to Other Files

This file is the project's memory across sessions. Update it after every meaningful implementation change, per `ai-workflow-rules.md`. Units below correspond exactly to the Django apps in `architecture.md` and the function blocks in `code-standards.md`, grouped by roadmap stage. **Do not start a unit from a later stage until every unit in the current stage is marked Completed.**

---

## Current Phase

- Stage 2 Complete (Teacher Intelligence Platform)

## Current Goal

- Begin Stage 3 — Personalized Study Plan + Progress.

## Completed

- Stage 1 — Foundation + Student Assessment (Auth, Onboarding, Question Flow, Auto-Save, Scoring Engine, Learning Profile).
- Stage 2 — Teacher Intelligence Platform (`classroom` app, Class creation with unique class codes, Student joining flow, Teacher Dashboard & student roster, Teacher-facing Student Intelligence Profile view with strict server-side access control).

## In Progress

- Stage 3 — Personalized Study Plan + Progress.

## Next Up

### Stage 1 — Foundation + Student Assessment

1. Django project setup (`/config`) + Supabase PostgreSQL connection.
2. `profiles` table migration + Supabase Auth integration with Django sessions.
3. `accounts` app — Block: Auth (student/teacher/admin registration & login, role-based redirect, server-side role enforcement).
4. `accounts` app — Block: Student Onboarding screen.
5. `assessment_questions` table migration + seed initial question set (dimensions, question text, type, options).
6. `assessment` app — Block: Assessment Question Flow (question UI, progress indicator, auto-save to `assessment_responses`).
7. `assessment` app — Block: Scoring Engine (`scoring.py`) — dimension aggregation rules, archetype mapping, strengths/challenges/recommendations logic, all explicitly documented in `code-standards.md` as implemented.
8. Student-facing Learning Profile results screen.
9. End-to-end manual verification of the full Stage 1 flow: Landing → Register → Onboarding → Assessment → Submit → Scoring → Profile.

### Stage 2 — Teacher Intelligence Platform

1. `classes` and `class_students` table migrations.
2. `classroom` app — Block: Class Creation & Class Code.
3. `classroom` app — Block: Student Joins a Class.
4. `classroom` app — Block: Teacher Dashboard (class list, student roster).
5. `classroom` app — Block: Teacher-facing Student Profile View (archetype, scores, strengths, challenges, recommended teaching approach).
6. Access-control verification: confirm a teacher cannot view another teacher's students.
7. End-to-end manual verification of the full Stage 2 flow: Teacher creates class → shares code → student joins → teacher views student's learning profile.

### Stage 3 — Personalized Study Plan + Progress

1. `study_plans`, `study_plan_tasks`, `teacher_notes` table migrations.
2. `study_plans` app — Block: Study Plan Generator (`generator.py`) — rule-based distribution logic, explicitly documented once implemented.
3. `study_plans` app — Teacher-facing plan creation/edit/assign UI.
4. `study_plans` app — Block: Student Study Plan View (today's tasks, mark complete, optional timer).
5. `study_plans` app — Block: Progress Dashboard (tasks completed/remaining, study time, streak, weekly %) — streak edge-case rule explicitly documented once implemented.
6. Teacher notes/feedback UI on a student's plan.
7. End-to-end manual verification of the full Stage 3 flow: Teacher generates plan → student completes tasks → progress dashboard reflects reality → teacher adds a note.

### Stage 4 — AI + Adaptive Learning (do not start until Stages 1–3 are fully complete)

1. Choose and configure an LLM provider; add API key handling per protected-files rules in `ai-workflow-rules.md`.
2. `profile_snapshots` table migration + decide/document snapshot cadence.
3. `ai_engine` app — Block: AI Teacher Assistant, with documented prompt template.
4. `ai_engine` app — Block: AI Study Plan Generation, with documented prompt template.
5. `ai_engine` app — Block: Adaptive Learning — documented "meaningful change" threshold and adjustment logic.
6. `ai_engine` app — Block: AI Student Tutor, with documented per-archetype prompt templates and defined feedback loop.
7. End-to-end manual verification of each Stage 4 block independently (these are advisory features — verify they never silently overwrite teacher- or student-set data).

## Open Questions

- None yet — log here as they arise during implementation, per `ai-workflow-rules.md` → Handling Missing Requirements.

## Architecture Decisions

- None yet — log here as decisions are made during implementation, including the reasoning (e.g., choosing a specific scoring formula, streak edge-case rule, or AI snapshot cadence).

## Session Notes

- No implementation work has started. Next session should begin at Stage 1, Unit 1 (Django project setup + Supabase connection).
