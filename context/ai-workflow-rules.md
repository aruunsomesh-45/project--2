# AI Workflow Rules — Learning Profile & Teaching Intelligence Platform

## Relationship to Other Files

This file governs **how** the AI agent behaves while building this project. It does not define **what** to build (`project-overview.md`), **how the system is structured** (`architecture.md`), **how code should look** (`code-standards.md`), or **the design system** (`ui-context.md`). It reads all four before writing code, and writes to `progress-tracker.md` after every unit of work. Where these files are silent, the original PRD's 4-stage roadmap is authoritative — **do not build features from a later stage before the current stage is complete.**

---

## Approach

Build this project incrementally, one stage at a time, using a spec-driven workflow. `project-overview.md`, `architecture.md`, `code-standards.md`, and `ui-context.md` define what to build, how to build it, and what it should look like. `progress-tracker.md` defines what has already been built and what's next. Always implement against these specs — do not infer or invent product behavior, scoring logic, or AI prompts not described in them.

Stack: **Django (Python) backend, Supabase (PostgreSQL) database, HTML/CSS/JavaScript frontend.**

This is a large, multi-stage product. It is explicitly **not** meant to be built all at once:

1. **Stage 1 — Foundation + Student Assessment**
2. **Stage 2 — Teacher Intelligence Platform**
3. **Stage 3 — Personalized Study Plan + Progress**
4. **Stage 4 — AI + Adaptive Learning**

Stage 4 (AI features) must not be started until Stages 1–3 are functionally complete and verified. AI-generated study plans, AI teaching suggestions, and adaptive learning all depend on having real assessment, teacher, and progress data to work against — building them earlier produces speculative, unverifiable behavior.

---

## Scoping Rules

- Work on one feature unit at a time (one Django app, one view, one model, or one template per step — see `progress-tracker.md` → Next Up for the exact unit breakdown).
- Prefer small, verifiable increments over large speculative changes.
- Do not combine unrelated system boundaries in a single step — for example:
  - Do not combine authentication changes with assessment-scoring changes.
  - Do not combine a teacher-dashboard UI change with a database schema change.
  - Do not combine any Stage 3 (study plan) work with any Stage 4 (AI) work.
  - Do not combine complex frontend interactivity (e.g., the assessment progress indicator, study timer) with backend model changes in the same step.

## When to Split Work

Split an implementation step if it combines:

- UI/template changes and Django model or Supabase schema changes
- Multiple unrelated Django apps (e.g., `accounts` and `assessment` in the same step)
- Behavior not clearly defined in `project-overview.md`, `architecture.md`, or the original PRD
- Work from two different stages of the roadmap
- The scoring engine and the assessment UI — these are separate concerns (data collection vs. interpretation) and must be independently testable

If a change cannot be verified end to end quickly (e.g., "a student can log in, answer one assessment question, and have it auto-save"), the scope is too broad — split it.

## Handling Missing Requirements

- Do not invent product behavior, scoring weights, archetype definitions, or AI prompt behavior not defined in the context files or PRD.
- If a requirement is ambiguous (e.g., exact scoring formula for a learning dimension, exact archetype thresholds), resolve it by proposing a specific, documented rule in `architecture.md` or `code-standards.md` before implementing — don't silently guess and bury the decision in code.
- If a requirement is genuinely missing, add it as an open question in `progress-tracker.md` under **Open Questions** before continuing, and pick the smallest reasonable default so the unit can still ship.
- Stage 4 AI behaviors (recommended teaching approach, AI study plan, adaptive learning adjustments) are inherently generative — document the exact prompt/logic used for each in `code-standards.md` once implemented, so behavior is reproducible and reviewable, not a black box.

## Protected Files

Do not modify the following unless explicitly instructed:

- Any third-party library internals or vendor files in `static/`
- Django framework core files
- `.env` / any file containing real Supabase credentials or AI provider API keys
- Any already-applied Supabase migration — create a new migration instead of editing history
- Existing assessment question data once real students have started taking the assessment (changing questions/scoring retroactively invalidates existing results — flag this in `progress-tracker.md` instead of editing silently)

## Non-Negotiable Rules

1. **Role separation is enforced server-side.** A student must never be able to access teacher-only views (class roster, other students' profiles) or admin views, and vice versa. This is checked in every view, not just hidden in the UI.
2. **A teacher can only see students who have joined one of their classes via a class code** — not all students in the system.
3. **Assessment answers auto-save** as the student progresses — a student must never lose progress by closing the tab mid-assessment.
4. **The scoring engine is deterministic and rule-based in Stages 1–3.** No AI/LLM involvement in scoring until Stage 4 explicitly introduces adaptive re-scoring — keep the initial engine simple, auditable, and documented in `architecture.md`.
5. **Stage 4 AI outputs are advisory, not authoritative** — an AI teaching suggestion or AI-generated study plan is a proposal the teacher can review/edit, never an auto-applied silent change to a student's plan.

## Keeping Docs in Sync

Update the relevant context file whenever implementation changes:

- `architecture.md` — if system boundaries, the file structure, the schema, or an invariant changes
- `code-standards.md` — if a coding convention changes, or a function block (auth, scoring, class creation, study plan generation, AI blocks) is implemented differently than specified
- `ui-context.md` — if a design token, component pattern, or layout decision changes
- `project-overview.md` — if scope changes within or across stages

## Before Moving to the Next Unit

A unit is done only when all of the following are true:

1. The current unit works end to end within its defined scope.
2. No invariant defined in `architecture.md` was violated.
3. No non-negotiable rule above was violated.
4. `progress-tracker.md` reflects the completed work (moved from **Next Up** → **Completed**, with a one-line note on any decision made).
5. `python manage.py test` (or the relevant test command for that unit) passes, where tests exist for that unit.

## Before Moving to the Next Stage

In addition to the per-unit checklist above, before starting Stage 2, 3, or 4:

1. Every unit listed under the previous stage in `progress-tracker.md` is marked Completed.
2. The previous stage's deliverable (as defined in `project-overview.md`) has been manually verified end to end.
3. Any open questions raised during the previous stage have been resolved or explicitly deferred with a reason.
