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

## Autonomy level — how many checkpoints this phase fires

The `## Autonomy` block in the `dev-assistant issue show` output above resolves this issue's level (`guided` | `balanced` | `auto`). Issues created before the field existed resolve to `guided`. A trailing `--guided` / `--balanced` / `--auto` token in `$ARGUMENTS` overrides it for this invocation only — strip it before treating the rest as the issue ID.

| Kind of stop | `guided` | `balanced` | `auto` |
|---|---|---|---|
| **Content** — only the user knows it | sub-stages 1, 2, 3 asked one question at a time | sources asked once; the direct-input questions asked as **one block** | same as balanced, and the block is asked once — no follow-ups unless an answer contradicts a source |
| **Approval** — approving a draft you produced | sub-stages 2, 3, 4, 5 | **one checkpoint, in sub-stage 5** | none — write the files and report what you decided |
| **External** | none in this phase | none | none |
| **Escalation** — contradictions between sources, a source you cannot access | stops | stops | stops |

**Never removed at any level in this phase:** the source inventory (sub-stage 1) and the direct-input questions (sub-stage 2). This is the phase whose entire job is to collect what only the user has — an unanswered gather produces objectives grounded in nothing. `auto` compresses *how* it is asked, never *whether*.

At `balanced` / `auto`, add `autonomy: <level>` to the frontmatter of both artifacts and a **`## Decided without review`** section to `report.md` listing what you settled alone (which process objectives you excluded, which draft objectives the user never saw, which contradictions you resolved by judgment).

## How to interact with the user

This phase requires real conversation. **When a stop is reached, stop and wait for the user's actual response.** Do not synthesize answers on the user's behalf, and never under Claude Code's auto-accept mode either.

- At `guided`: ask one question at a time, give the user space to answer, and let their answer inform the next. Stops: **sub-stage 1** (which sources?), **sub-stage 2 / Meeting notes** (paste), **sub-stage 2 / Direct input** (conversation), **sub-stage 3** (process objectives), **sub-stage 4** (draft review), **sub-stage 5** (final validation).
- At `balanced`: three stops — the source inventory, the direct-input block (which absorbs the meeting-notes paste and the process-objective exclusions), and the single checkpoint in sub-stage 5. At `auto`: the first two only.

## How to run this phase — five sub-stages

Announce which sub-stage you're entering before each one so the user knows where they are. Don't move on until the current sub-stage has a settled outcome.

### Sub-stage 1 — Source inventory

Ask the user which sources of information are available for this issue. The candidates are:

- **Refinement report** — `refinement/report.md` written by `/dev-refine`, if the phase progress above shows one. When present, propose it as the *first* source by default — it records the exploration that shaped the ticket.
- **JIRA** — fetch issue details via the Atlassian MCP if you have access to those tools
- **Repo** — read files in the current working directory using Read, Grep, Glob
- **Meeting notes** — the user pastes them into the chat
- **Direct input** — the user just tells you in conversation

Confirm which subset will be consulted. Record the list.

At `balanced` / `auto`, ask this as **one message** — the candidate list with your recommendation marked, plus (if meeting notes are a candidate) "paste them in the same reply if you have them". One answer should be enough to start.

### Sub-stage 2 — Information collection

Go through each source confirmed in sub-stage 1, in turn. Do **one source at a time**, don't interleave. After each, show the user a short summary of what you took away before moving on.

**Important: retain detail, don't compress too early.** You'll write a full report at the end, not just bullets. Keep the actual content (quoted comments, code snippets, paraphrased meeting points) — you'll need it for `report.md`. Summary-of-summary now means thin report later.

- **Refinement report**: read `.dev-assistant/issues/$ARGUMENTS/refinement/report.md` in full. It carries the chosen direction, the alternatives that were set aside (and why), feasibility findings, and open questions — treat its decisions as settled unless the user reopens them, and seed your open-questions list from its "Open questions for gathering" section. Many of the Direct input guiding questions below will already be answered here; skip or adapt those rather than re-asking.

- **JIRA**: if available, look up the issue (`$ARGUMENTS` is likely the Jira key). Pull title, description, status, comments, linked issues. Keep the actual content of relevant fields, not just one-line summaries. At `guided`, confirm with the user that this is the right ticket and flag anything missing. At `balanced` / `auto`, state the ticket you loaded and flag anything missing without waiting for an acknowledgement. If a refinement report exists, the ticket text was already rewritten by `/dev-refine` — focus on what's *new* since then (comments, status changes, links).

- **Repo**: ask the user which files/areas are relevant, or grep for keywords from the issue title. Read the relevant files. Keep paths + a real summary of what each contains relative to this issue — not just "I read X." Note any existing patterns the issue touches.

- **Meeting notes**: ask the user to paste them. Extract the parts relevant to this issue and keep them in your working notes. Discard truly off-topic content but be generous about what's "relevant" — a comment about team availability might matter even if the meeting was about something else.

- **Direct input**: this is your conversation with the user — they will tell you context you can't get from any other source. **STOP here and wait for the user's responses at every autonomy level.** Don't synthesize answers on their behalf, and never under Claude Code's auto-accept mode either.

  Use these guiding questions to draw out useful information. If the user already covered something in earlier sub-stages or in the refinement report, skip or adapt the question.

  - At `guided`: ask in order, **one at a time**, and let each answer inform the next.
  - At `balanced` / `auto`: ask **all of them in one message**, numbered, with a line saying partial answers are fine and "skip" is a valid answer to any of them. Follow up only where an answer contradicts another source or is too thin to ground an objective — that is an escalation, not a checkpoint. At `balanced` you may also fold in the sub-stage 3 process-objective question here as a sixth item.

  1. *"In your own words, what's the problem this issue is trying to solve, or the outcome you want?"* — Get the underlying goal in their words, not the ticket's.
  2. *"What's the background the ticket doesn't capture? (Prior attempts, related work, decisions already made.)"* — Surfaces history.
  3. *"Who else has context here that matters? (Stakeholders, reviewers, people blocking or being blocked.)"* — Hidden human dependencies.
  4. *"What constraints have come up that aren't documented anywhere? (Deadlines, team availability, technical limits, policy.)"* — Only the user has these.
  5. *"What's the most uncertain or worrying part of this for you?"* — Surfaces open questions and risk.

  Take the answers verbatim into your working notes. Don't paraphrase aggressively — quotes from the user become the most useful part of `report.md`.

Keep a running summary of "what we know so far" as you go. If something looks inconsistent across sources, flag it — that contradiction belongs in the report's Analysis section.

### Sub-stage 3 — Process objectives confirmation

The process objectives are already loaded at the top of this prompt.

- At `guided`: show that list to the user and ask — are there any that don't apply to this specific issue and should be excluded? (Example: a docs-only change probably doesn't need "tests pass before merge.")
- At `balanced`: fold the same question into the direct-input block in sub-stage 2 rather than spending a separate turn on it.
- At `auto`: decide it yourself. Exclude only what is *clearly* inapplicable and say why; when in doubt, keep the objective. Record every exclusion in the sub-stage 5 checkpoint's `## Decided without review` list.

Record the final list (kept or excluded) for `objectives.md`.

### Sub-stage 4 — Draft issue objectives (synthesis)

Based on everything collected in sub-stage 2, propose:

- A **general objective**: one sentence describing the high-level outcome this issue should achieve. Concrete enough that you could tell whether it was achieved.
- **Specific objectives**: 3–7 concrete, testable items that together fulfill the general one. Each one should be something a person could mark done or not done.

**At `guided`:** show your draft and iterate with the user — they redirect, you re-derive.

**At `balanced` / `auto`:** don't stop here. Draft the objectives and carry them into sub-stage 5, where the user sees them in the single checkpoint alongside both file previews.

Either way this is the quality-critical step; don't accept hand-wavy objectives ("improve the system"). Push for ones tied to the collected sources — and push back on your own drafts just as hard when nobody else is going to.

If you can't ground an objective in something from sub-stage 2, flag it as speculation and either drop it or convert it to an open question.

### Sub-stage 5 — Validation and write

**At `guided`:** show the user a preview of both files (don't write yet) and ask, one at a time:

- Anything missing from the report?
- Any open questions we should record (things we don't know that may block progress)?
- Any constraints we should record (deadlines, dependencies, technical limits)?
- Does the objectives file accurately reflect what we decided?

**At `balanced`:** this is the phase's single checkpoint. Show one view containing the drafted general + specific objectives, the constraints and open questions you extracted, the process objectives you kept or excluded, and a preview of `report.md`. Then ask once:

```
Approve and write / revise the objectives / revise the report / add something I know that's missing / abandon
```

On a revision request, redraft and re-show the whole view.

**At `auto`:** no checkpoint. Write both files, then show the same view as a *report* of what was written, with the `## Decided without review` list front and centre so the user can react to anything that looks wrong. `/dev-plan` opens with the objectives anyway — a bad objective gets caught there.

When the user confirms (or immediately, at `auto`), write **two files** in this order.

**First**: `.dev-assistant/issues/$ARGUMENTS/gathering/report.md`

```markdown
---
issue: $ARGUMENTS
phase: gathering
status: complete
autonomy: <guided | balanced | auto>
sources: [list of sources actually consulted]
---

# Gathering report — $ARGUMENTS

## Summary

One paragraph: what we set out to understand, what we learned overall, the main insight or tension that emerged.

## Sources

### Refinement report
- Chosen direction and decision rationale (from /dev-refine)
- Alternatives set aside, with reasons
- Open questions inherited from refinement

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

## Decided without review

(`balanced` / `auto` only — omit the section at `guided`.) What you settled without a checkpoint: process objectives you excluded and why, objectives the user never redirected, contradictions between sources you resolved by judgment, anything you chose not to pursue.
```

**Second**: `.dev-assistant/issues/$ARGUMENTS/gathering/objectives.md`

```markdown
---
issue: $ARGUMENTS
phase: gathering
status: complete
autonomy: <guided | balanced | auto>
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
