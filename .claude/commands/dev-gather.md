---
description: Walk the gather phase for one issue — produces gathering/report.md (full context) and gathering/objectives.md (distilled objectives)
argument-hint: <issue-id>
model: opus
allowed-tools: Bash(dev-assistant:*), Read, Write, Edit, Grep, Glob
---

You are running the **gather information** phase for issue `$ARGUMENTS`.

## Current state of the issue

!`dev-assistant issue show --id $ARGUMENTS`

## Process objectives (resolved: per-repo override → source default)

!`dev-assistant strategies show process-objectives`

## Output style — how to write the artifacts this phase produces

!`dev-assistant strategies show output-style`

**Follow the output style above when writing `report.md` and `objectives.md` in sub-stage 5.** Frontmatter, headings, voice, quoting rules, length per section, what to avoid — all of it. The style applies to both files.

## Repo context — repo-specific rules to respect

!`dev-assistant repo-context show`

The above is the target repo's own guideline documents (workflows, naming, lifecycle constraints, PR checklists, etc.). Apply alongside the strategies. When gathering, look for hints in the issue that touch areas covered here — call them out in `report.md` and pull relevant constraints into `objectives.md` so later phases inherit them. If a repo-context rule conflicts with a strategy, the repo-context rule wins (it is repo-specific and authoritative).

---

## What this phase produces

Two artifacts in `.dev-assistant/issues/$ARGUMENTS/gathering/`:

1. **`report.md`** — the *thinking artifact*. Full record of what was gathered: raw findings from each source, analysis, assumptions called out, things considered but excluded. Preserves texture that gets lost in distillation.
2. **`objectives.md`** — the *decision artifact*. Distilled, tight, used by later phases. Contains the process objectives + issue objectives (general + specific) + constraints + open questions. Points at `report.md` for full context.

Two files, two purposes. Don't merge them.

## How to interact with the user

This phase requires real conversation. **Several sub-stages need user input — when one of them is reached, stop and wait for the user's actual response.** Do not synthesize answers on the user's behalf, even when running in autonomous / auto-accept modes. Ask one question at a time, give the user space to answer, and let their answer inform the next question.

The sub-stages requiring active user input are: **sub-stage 1** (which sources?), **sub-stage 2 / Meeting notes** (paste), **sub-stage 2 / Direct input** (conversation — see below), **sub-stage 3** (process objectives confirmation), **sub-stage 4** (draft review), and **sub-stage 5** (final validation).

## How to run this phase — five sub-stages

Announce which sub-stage you're entering before each one so the user knows where they are. Don't move on until the current sub-stage has a settled outcome.

### Sub-stage 1 — Source inventory

Ask the user which sources of information are available for this issue. The candidates are:

- **JIRA** — fetch issue details via the Atlassian MCP if you have access to those tools
- **Repo** — read files in the current working directory using Read, Grep, Glob
- **Meeting notes** — the user pastes them into the chat
- **Direct input** — the user just tells you in conversation

Confirm which subset will be consulted. Record the list.

### Sub-stage 2 — Information collection

Go through each source confirmed in sub-stage 1, in turn. Do **one source at a time**, don't interleave. After each, show the user a short summary of what you took away before moving on.

**Important: retain detail, don't compress too early.** You'll write a full report at the end, not just bullets. Keep the actual content (quoted comments, code snippets, paraphrased meeting points) — you'll need it for `report.md`. Summary-of-summary now means thin report later.

- **JIRA**: if available, look up the issue (`$ARGUMENTS` is likely the Jira key). Pull title, description, status, comments, linked issues. Keep the actual content of relevant fields, not just one-line summaries. Confirm with the user that this is the right ticket and flag anything missing.

- **Repo**: ask the user which files/areas are relevant, or grep for keywords from the issue title. Read the relevant files. Keep paths + a real summary of what each contains relative to this issue — not just "I read X." Note any existing patterns the issue touches.

- **Meeting notes**: ask the user to paste them. Extract the parts relevant to this issue and keep them in your working notes. Discard truly off-topic content but be generous about what's "relevant" — a comment about team availability might matter even if the meeting was about something else.

- **Direct input**: this is your conversation with the user — they will tell you context you can't get from any other source. **STOP here and wait for the user's responses.** Don't synthesize answers on their behalf, even in auto modes.

  Use these guiding questions to draw out useful information. Ask in order, **one at a time**, and let each answer inform the next. If the user already covered something in earlier sub-stages, skip or adapt the question:

  1. *"In your own words, what's the problem this issue is trying to solve, or the outcome you want?"* — Get the underlying goal in their words, not the ticket's.
  2. *"What's the background the ticket doesn't capture? (Prior attempts, related work, decisions already made.)"* — Surfaces history.
  3. *"Who else has context here that matters? (Stakeholders, reviewers, people blocking or being blocked.)"* — Hidden human dependencies.
  4. *"What constraints have come up that aren't documented anywhere? (Deadlines, team availability, technical limits, policy.)"* — Only the user has these.
  5. *"What's the most uncertain or worrying part of this for you?"* — Surfaces open questions and risk.

  Take the answers verbatim into your working notes. Don't paraphrase aggressively — quotes from the user become the most useful part of `report.md`.

Keep a running summary of "what we know so far" as you go. If something looks inconsistent across sources, flag it — that contradiction belongs in the report's Analysis section.

### Sub-stage 3 — Process objectives confirmation

The process objectives are already loaded at the top of this prompt. Show that list to the user and ask: are there any that don't apply to this specific issue and should be excluded? (Example: a docs-only change probably doesn't need "tests pass before merge.")

Record the final list (kept or excluded) for `objectives.md`.

### Sub-stage 4 — Draft issue objectives (synthesis)

Based on everything collected in sub-stage 2, propose:

- A **general objective**: one sentence describing the high-level outcome this issue should achieve. Concrete enough that you could tell whether it was achieved.
- **Specific objectives**: 3–7 concrete, testable items that together fulfill the general one. Each one should be something a person could mark done or not done.

Show your draft. Iterate with the user — they redirect, you re-derive. This is the quality-critical step; don't accept hand-wavy objectives ("improve the system"). Push for ones tied to the collected sources.

If you can't ground an objective in something from sub-stage 2, flag it as speculation and either drop it or convert it to an open question.

### Sub-stage 5 — Validation and write

Show the user a preview of both files (don't write yet). Ask:

- Anything missing from the report?
- Any open questions we should record (things we don't know that may block progress)?
- Any constraints we should record (deadlines, dependencies, technical limits)?
- Does the objectives file accurately reflect what we decided?

When the user confirms, write **two files** in this order.

**First**: `.dev-assistant/issues/$ARGUMENTS/gathering/report.md`

```markdown
---
issue: $ARGUMENTS
phase: gathering
status: complete
sources: [list of sources actually consulted]
---

# Gathering report — $ARGUMENTS

## Summary

One paragraph: what we set out to understand, what we learned overall, the main insight or tension that emerged.

## Sources

### JIRA
- Ticket title, description, status (quote the actual content)
- Key comments / discussion threads (quote what matters)
- Linked issues and what they imply
- Anything else relevant from the ticket

### Repository
- Files examined and why each was relevant
- Real summary of what each file contains relative to this issue
- Existing patterns this issue touches

### Meeting notes
- Relevant excerpts in their original context
- Decisions referenced, who said what mattered

### Direct input
- The user's own answers to the guiding questions, quoted or near-quoted
- Anything they emphasized

(Only include sections for sources actually consulted.)

## Analysis

- Patterns or themes that emerged across sources
- Tensions or contradictions noticed
- Assumptions being made (call them out as assumptions)
- Things discussed but deliberately excluded from objectives (with why)

## How this maps to objectives

Brief mapping: each gathered point → which objective it informed. So later phases can trace objectives back to evidence.

## What's missing

Things we knew we couldn't get (no access to X, didn't have time for Y, person not available). Honesty about gaps prevents later confusion.
```

**Second**: `.dev-assistant/issues/$ARGUMENTS/gathering/objectives.md`

```markdown
---
issue: $ARGUMENTS
phase: gathering
status: complete
---

# Objectives — $ARGUMENTS

See [report.md](./report.md) for the full gathering context, sources, and analysis.

## Process objectives

- [ ] (item from strategies/process-objectives.md, if kept)
- [ ] ...

## Issue objectives

### General

> One sentence: the high-level outcome.

### Specific

- [ ] Specific objective 1
- [ ] Specific objective 2
- [ ] Specific objective 3

## Constraints

- Deadlines, dependencies, technical or policy limits

## Open questions

- Things we don't know that may block progress
```

After writing both files, give the user a one-paragraph summary of what was captured and remind them the next step will be `/dev-plan $ARGUMENTS` (not yet implemented).

## If the files already exist

The user is re-running gather. Show them the current contents of both files, ask which sections they want to revise, and only edit those sections rather than starting over. Keep both files in sync if changes affect both.
