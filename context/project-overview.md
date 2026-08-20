# Learning Profile & Teaching Intelligence Platform

*(Working title — replace once a final product name is chosen.)*

## Relationship to Other Files

This file is the PRD summary and product source of truth — the "what and why," organized by build stage. `architecture.md` and `code-standards.md` implement this; `ui-context.md` styles it; `progress-tracker.md` tracks progress against the stages defined here. Where any other file conflicts with this one on product scope, the original PRD (and this summary of it) wins.

---

## Overview

A learning platform that starts with a 16Personalities-style assessment to build each student a personalized "Learning Profile," then connects that profile to their teacher so the teacher understands how to teach them, then turns the profile into an actual personalized study plan with progress tracking, and finally layers AI-driven teaching suggestions and adaptive learning on top once real usage data exists. Built with Django (Python) on the backend, Supabase (PostgreSQL) as the database, and HTML/CSS/vanilla JavaScript on the frontend.

## Goals

1. Give every student a clear, useful Learning Profile (archetype + dimension scores + strengths + challenges + recommendations) from a single assessment.
2. Give every teacher a dashboard that answers "how does this student learn, and how should I teach them?" for each student in their class.
3. Turn each student's profile into a concrete, personalized study plan with visible day-by-day tasks and progress tracking.
4. Once Stages 1–3 are proven with real data, use AI to generate teaching suggestions, study plans, and adapt to a student's changing performance over time.

## Roadmap (Build in This Order — Do Not Skip Ahead)

| Stage | Main Focus                               | Main User         |
| ----- | ------------------------------------------ | ------------------ |
| 1     | Assessment + Learning Profile               | Student            |
| 2     | Teacher Dashboard + Student Intelligence     | Teacher            |
| 3     | Study Plans + Progress                       | Student + Teacher  |
| 4     | AI + Adaptive Learning                        | Student + Teacher  |

Each stage's deliverable must work end to end and be verified before the next stage starts — see `ai-workflow-rules.md` → "Before Moving to the Next Stage."

## Core User Flows

### Student Flow (Stage 1)

```
Landing Page → Register → Student Onboarding → Learning Assessment
   → Submit → Scoring Engine → Learning Profile
```

### Teacher–Student Flow (Stage 2)

```
Teacher → Create Class → Class Code → Student Joins
   → Teacher Gets Access → Views Student's Learning Profile
```

### Study Plan Flow (Stage 3)

```
Teacher selects Student + Subject + Goal + Exam Date + Available Time + Difficulty
   → System Generates Study Plan → Student Works Through Tasks
   → Progress Dashboard Updates → Teacher Adds Notes/Feedback
```

### AI-Assisted Flow (Stage 4)

```
Teacher asks "How should I teach X?" → AI uses Student Profile → Recommended Approach
Student Profile + Subject + Exam Date + Performance → AI → Personalized Study Plan
Ongoing Performance → Adaptive Adjustment → Updated Study Plan
```

## Features by Stage

### Stage 1 — Assessment + Learning Profile

- Django + Supabase project setup
- Student, teacher, and admin registration/login
- Student onboarding
- Assessment question bank, UI, progress indicator, auto-save
- Deterministic scoring engine → learning dimensions and archetype
- Learning Profile results screen (strengths, challenges, recommendations)

### Stage 2 — Teacher Dashboard + Student Intelligence

- Teacher registration/login and dashboard
- Class creation with a shareable class code
- Students join a class via code
- Teacher views each student's Learning Profile in a teacher-friendly format

### Stage 3 — Study Plans + Progress

- Teacher-driven study plan generator (subject, goal, exam date, available time, difficulty)
- Student view: today's tasks, mark complete, optional study timer
- Progress dashboard: tasks completed/remaining, study time, streak, weekly %
- Teacher can edit/assign plans and add notes/feedback

### Stage 4 — AI + Adaptive Learning

- AI Teacher Assistant: free-text teaching questions answered using the student's profile
- AI-generated study plans as an alternative to the Stage 3 rule-based generator
- Adaptive learning: re-scoring/adjustment based on performance over time
- AI Student Tutor: profile-shaped explanations and practice

## Scope

### In Scope (across all 4 stages)

- Three roles: student, teacher, admin (admin scope is minimal — auth only, unless expanded later)
- One assessment, deterministic scoring, archetype + dimension results
- Class-based teacher/student relationships via class codes (no school-wide admin hierarchy specified)
- One study plan generation flow (rule-based, then AI-assisted in Stage 4)
- Progress tracking tied to study plan task completion

### Explicitly Phased Out Until Stage 4

- Any AI/LLM involvement in scoring, plan generation, or teaching suggestions — Stages 1–3 are fully deterministic and rule-based by design (see `ai-workflow-rules.md`).

## Success Criteria

1. **Stage 1**: A student can register, complete the assessment, and receive a Learning Profile with an archetype, dimension scores, strengths, challenges, and recommendations — entirely from deterministic, documented scoring rules.
2. **Stage 2**: A teacher can create a class, get students to join via a code, and view any of their students' Learning Profiles in the teacher-facing format shown in the PRD.
3. **Stage 3**: A teacher can generate a study plan for a student, the student can complete tasks, and both teacher and student see an accurate, correctly-computed progress dashboard.
4. **Stage 4**: A teacher can get an AI teaching suggestion and an AI-generated study plan for a specific student, both clearly presented as advisory/editable rather than auto-applied, and the system can demonstrate an adaptive adjustment based on a before/after performance snapshot.
