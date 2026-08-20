# UI Context — Learning Profile & Teaching Intelligence Platform

## Relationship to Other Files

This is the design system referenced by `code-standards.md` (styling rules) and implemented across the templates listed in `architecture.md`. **The PRD does not specify branding, colors, or typography** — everything below is a sensible, documented default for an education/assessment product. Treat it as a placeholder to be replaced once real branding exists, and log that swap as a session note in `progress-tracker.md` when it happens.

---

## Theme

Clean, trustworthy, encouraging — closer to an assessment/reporting tool (like 16Personalities) than a marketing site. Should feel calm and readable for the assessment itself, and clear/scannable for the teacher dashboard and progress views, which show a lot of data (scores, percentages, lists) at once.

## Colors

Define these as CSS custom properties in a shared stylesheet — never hardcode hex values in templates.

| Role            | CSS Variable       | Value     | Notes |
| ---------------- | ------------------- | --------- | ----- |
| Page background    | `--bg-base`         | `#FFFFFF` | |
| Surface (cards)      | `--bg-surface`       | `#F8FAFC` | Used for profile cards, dashboard panels |
| Primary text          | `--text-primary`     | `#0F172A` | |
| Muted text              | `--text-muted`       | `#64748B` | |
| Primary accent            | `--accent-primary`   | `#4F46E5` | *Placeholder — swap for real brand color* |
| Border                      | `--border-default`   | `#E2E8F0` | |
| Success (strengths, completed tasks) | `--state-success` | `#16A34A` | |
| Warning (challenges)                   | `--state-warning` | `#D97706` | Used for the ⚠ challenge markers in the PRD mockups |
| Error                                     | `--state-error`   | `#DC2626` | |
| Dimension bar fill (default)                | `--bar-fill`      | `--accent-primary` | For the percentage bars in learning profile / progress views |

## Typography

| Role      | Font                          | Variable      | Notes |
| ---------- | ------------------------------ | -------------- | ----- |
| UI text     | Inter (or system-ui fallback)    | `--font-sans`   | Body text, forms, dashboards |
| Numerals/scores | Same as UI text, tabular-nums    | `--font-sans`   | Use `font-variant-numeric: tabular-nums` for score/percentage alignment in tables and bars |

No dedicated monospace font is needed — this app doesn't display code (Stage 4's "Python loops" example is teaching content, not rendered code).

## Border Radius

| Context               | Value        |
| ----------------------- | ------------- |
| Inline / small UI (inputs, buttons) | `6px` |
| Cards / panels (profile card, plan card) | `10px` |
| Modals / overlays (if used)                | `12px` |

## Component Architecture

Since this is Django + vanilla HTML/CSS/JS, components are structured as reusable Django template partials (`templates/<app>/includes/`) with scoped CSS classes, initialized via modular JavaScript files in `static/js/` (one script per concern — auto-save, timer, progress indicator, class-code copy-to-clipboard).

## Layout Patterns

- **Overall layout**: `base.html` provides a shared header (role-aware nav: student/teacher/admin see different links) and a centered content area.
- **Assessment flow**: single-question-at-a-time, large touch-friendly answer targets, progress bar pinned near the top.
- **Teacher dashboard**: sidebar or top-level class list, main panel showing the selected class's student roster as a table/card list.
- **Student profile card (teacher view)**: matches the PRD mockup — archetype name as the header, dimension scores as horizontal percentage bars, strengths as a checkmark list, challenges as a warning-marker list, recommended teaching approaches as an arrow list.
- **Study plan view**: day-by-day list (Monday–Friday style, per PRD), each task as a row with duration and a completion checkbox.
- **Progress dashboard**: a horizontal progress bar for weekly %, plus a small stat grid (tasks completed, tasks remaining, study time, streak).

## Component States

- **Dimension score bar**: filled proportionally to the percentage, `--bar-fill` color, with the percentage labeled at the end of the bar (per the PRD's `Analytical Thinking 88%` style).
- **Strength item**: `✓` icon in `--state-success`.
- **Challenge item**: `⚠` icon in `--state-warning`.
- **Task row — incomplete**: default surface styling, checkbox unchecked.
- **Task row — complete**: subtle `--state-success` accent (e.g., left border or checkbox fill), text may be de-emphasized (muted, not strikethrough, to keep it readable).
- **Class code display**: monospace-style emphasis (letter-spacing, larger size) since it's meant to be read aloud or typed by a student, with a copy-to-clipboard affordance for the teacher.
- **AI-suggested content (Stage 4)**: visually distinguished from teacher-authored content (e.g., a small "AI suggested" label/badge) so it's always clear which parts of a plan or note were AI-generated vs. teacher-written, consistent with the non-negotiable rule in `ai-workflow-rules.md` that AI output is advisory, not authoritative.

## Responsiveness

Must work well on both desktop (primary for teacher dashboard use) and mobile (likely for students taking the assessment or checking today's tasks). Assessment and student study-plan views should be mobile-first; teacher dashboard and class roster can assume more width is usually available but must not break below ~375px.
