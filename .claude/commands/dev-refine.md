---
description: Walk the refine phase (phase 0) for one issue — turn a thin ticket into a well-specified one through an intense feasibility/alternatives conversation, update the Jira title + description after approval, and write refinement/report.md
argument-hint: <issue-id>
model: opus
allowed-tools: Bash(dev-assistant:*), Read, Write, Edit, Grep, Glob
---

You are running the **refine** phase (phase 0) for issue `$ARGUMENTS`.

## Current state of the issue (may not exist yet — that's normal)

!`dev-assistant issue show --id $ARGUMENTS`

If the command above errored with "not found", the workspace doesn't exist yet — refine is usually the *first* phase to touch a ticket, so you will create it in sub-stage 1. If it errored with "run `dev-assistant init` first", stop and ask the user to run init.

## Output style — how to write the artifact this phase produces

!`dev-assistant strategies show output-style`

**Follow the output style above when writing `report.md` in sub-stage 5** — with one sanctioned exception: this report is *allowed to be extensive*. The refinement conversation is the most information-dense moment of the whole lifecycle and the report is its only record. Prefer completeness over brevity; keep the style rules for structure, voice, and quoting.

## Repo context — repo-specific rules to respect

!`dev-assistant repo-context show`

Use the repo context during the feasibility discussion: if an explored direction collides with a repo rule (data workflow, naming, lifecycle constraints), surface that as a feasibility constraint, not as an afterthought.

---

## Why this phase exists

Tickets usually arrive thin: a one-line title and a vague description. Refine is where the ticket *becomes a real task*: you and the user think it through together — what is actually being asked, whether it's feasible, what alternative approaches/algorithms/ideas exist — and converge on a direction. The output is twofold:

1. **The Jira ticket itself gets better** — rewritten title + description, applied only after the user approves. This benefits the whole team, not just dev-assistant.
2. **`refinement/report.md`** — an extensive record of the exploration: alternatives considered, why they were rejected, feasibility findings, the decision rationale. `/dev-gather` consumes this as a source, so nothing from this conversation has to be repeated there.

This phase is **optional** in the lifecycle: well-specified tickets can go straight to `/dev-gather`. Nothing downstream requires a refinement artifact to exist.

## External side effects — exactly one, gated

The ONLY external write this phase may perform is the Jira title/description update in sub-stage 5, and only after the user has explicitly approved the exact text. No GitHub operations (the GH issue is created later, by `/dev-execute`), no Jira comments, no transitions, no other field edits.

If the issue is marked `experimental: true` in its frontmatter, skip the Jira update too — record the refined title/description locally only.

## Autonomy level — how many checkpoints this phase fires

The `## Autonomy` block in the `dev-assistant issue show` output above resolves this issue's level (`guided` | `balanced` | `auto`). Issues created before the field existed resolve to `guided`. A trailing `--guided` / `--balanced` / `--auto` token in `$ARGUMENTS` overrides the issue's level for this invocation only — strip it before treating the rest as the issue ID.

The level moves only two of the four kinds of stop:

| Kind of stop | `guided` | `balanced` | `auto` |
|---|---|---|---|
| **Content** — only the user knows it | asked one at a time | opening context asked as one block | same as balanced |
| **Approval** — approving a draft you produced | every sub-stage | **one checkpoint, in sub-stage 5** | same one checkpoint (it is also the Jira gate) |
| **External** — anything leaving the machine | confirmed per operation | one confirmation | one confirmation |
| **Escalation** — conflict, failure, ambiguity | stops | stops | stops |

**Never removed at any level in this phase:**

- **The sub-stage 2 exploration conversation.** A ticket cannot be refined against silence. It runs identically at every level — one question at a time, back and forth, for as long as it takes.
- **The Jira write.** The rewritten title/description is an external write; it fires only after the user approves the exact text.

At `balanced` / `auto`, add `autonomy: <level>` to `report.md`'s frontmatter and a **`## Decided without review`** section listing what you settled alone (which alternative won and why, what the report chose to record). Fewer checkpoints only stay safe if the artifact says what the user did not see.

## How to interact with the user

This phase is the most conversation-heavy of all. **Sub-stage 2 is real back-and-forth — stop and wait for the user's actual responses at every autonomy level.** Do not synthesize answers on the user's behalf, and never under Claude Code's auto-accept mode either. Ask one question at a time, give the user space to answer, and let their answer inform the next question. Push back when something seems infeasible or under-thought — the user wants a thinking partner here, not a stenographer.

At `guided`, sub-stages 3 and 4 are also back-and-forth. At `balanced` / `auto` they are drafted straight through and land in the single sub-stage 5 checkpoint.

Announce which sub-stage you're entering before each one. Don't move on until the current sub-stage has a settled outcome.

## How to run this phase — five sub-stages

### Sub-stage 1 — Load the ticket and scaffold the workspace

Get the ticket as it exists today:

- **Jira via the Atlassian MCP** (preferred): look up `$ARGUMENTS` (likely the Jira key). Pull title, description, status, comments, linked issues. Keep the actual content verbatim — the original ticket text goes into the report.
- **Fallback** (no MCP access): ask the user to paste the ticket's title and description.

Show the user what you got.

- At `guided`: confirm it's the right ticket before going further.
- At `balanced` / `auto`: state what you loaded and move on. The user will correct you in sub-stage 2 if it's the wrong ticket — don't spend a turn on an acknowledgement.

If the workspace doesn't exist yet, create it now:

```
dev-assistant issue create --id $ARGUMENTS --title "<current Jira title>" --description "<current Jira description>" --autonomy <level>
```

Two things only the user knows, so ask them — but at `balanced` / `auto` ask them **together, in one message**, alongside the first exploration question:

- Is this experimental/sandbox work? (→ `--experimental`, which skips every external operation for this issue's whole lifecycle)
- Which autonomy level should this issue run at? (→ `--autonomy`; default `balanced`. If the invocation carried an override token, use it and don't ask.)

### Sub-stage 2 — Exploration conversation

This is the heart of the phase: an intense, open discussion of the task. The goal is to *expand* before narrowing — feasibility, new ideas, alternative algorithms or approaches, hidden scope. Work through these threads, one at a time, adapting to the user's answers:

1. **The real ask.** *"In your own words — what is this ticket actually asking for, and what would 'done' look like?"* The ticket's text and the real intent often differ; find the gap.
2. **Feasibility.** Ground it in reality: read the relevant parts of the repo (Read/Grep/Glob) to check whether the obvious approach fits the existing code, data flow, and repo-context rules. Surface technical risks and unknowns *now*, while the ticket can still change shape.
3. **Alternatives.** Generate and discuss genuinely different ways to attack the problem — different approaches, algorithms, libraries, scope cuts, "do nothing / do less" options. Aim for 2–4 candidate directions where the problem allows it. For each: what it would take, what it buys, what it risks. Contribute your own ideas — this is the sub-stage where you're expected to bring options the user hasn't thought of.
4. **Scope edges.** What is explicitly *out*? What adjacent problems is this ticket tempted to absorb but shouldn't?
5. **Constraints.** Deadlines, dependencies on people or other tickets, performance/compatibility requirements, anything undocumented.

Keep a running set of working notes with real content — verbatim user quotes, file paths examined, concrete pros/cons per alternative. You will need all of it for the report; summary-of-summary now means a thin report later.

### Sub-stage 3 — Narrowing down

Converge. Propose, based on the exploration:

- The **chosen direction** — one short paragraph, concrete.
- **Alternatives set aside** — each with the actual reason it lost (not "out of scope" boilerplate).
- **Open questions** that survive refinement — things gather/plan must resolve, listed honestly.

**At `guided`:** show this convergence summary and iterate until the user agrees with the direction.

**At `balanced` / `auto`:** don't stop here. Commit to the direction the exploration pointed at, note the call in your working notes, and carry the convergence summary into the sub-stage 5 checkpoint where the user sees it alongside the rewritten ticket and the report. If the exploration left two directions genuinely tied, that is an escalation, not an approval — surface it and ask, at any level.

If the conversation revealed the ticket should be split or abandoned, say so — recommending "this should be two tickets" or "this isn't worth doing" is a valid outcome of this phase; record it and stop after writing the report.

### Sub-stage 4 — Ticket rewrite proposal

Draft the improved ticket and show it **side-by-side with the original**:

- **Title** — original vs. proposed. The proposed title should name the chosen direction, not the vague symptom.
- **Description** — original vs. proposed. The proposed description must carry enough for `/dev-gather` and a teammate reading cold: the problem, the chosen approach (one paragraph), explicit non-goals, known constraints, and open questions. Write it for the team, in the ticket's language conventions — it lives in Jira, not in dev-assistant.

**At `guided`:** iterate until the user explicitly approves the exact final text.

**At `balanced` / `auto`:** draft it and carry it into the sub-stage 5 checkpoint — that checkpoint is where the exact text gets approved. Either way: **do not touch Jira yet.**

### Sub-stage 5 — Apply and write the report

**At `balanced` / `auto`, this sub-stage opens with the phase's single checkpoint.** Show, in one view:

1. **The chosen direction** and the alternatives set aside, each with its reason (from sub-stage 3).
2. **The rewritten title + description**, side by side with the originals (from sub-stage 4).
3. **A preview of `report.md`**, plus the open questions being handed to gather.
4. **The external write about to fire:** *"Approving this updates the Jira ticket's title and description. Nothing else on Jira is touched."*

```
Approve all / revise the direction / revise the ticket text / revise the report / abandon
```

Wait for the answer. On a revision request, redraft the affected piece and re-show the whole view. On approve, run the three steps below. At `guided` the pieces were already approved individually — go straight to the steps.

Three steps, in order:

**First — update Jira** (skip entirely if experimental, or if MCP is unavailable — then show the final text for the user to paste manually):

- Update the ticket's title (summary) and description to the approved text via the Atlassian MCP. Nothing else — no comments, no transitions.

**Second — sync the local workspace**: edit `issue.md`'s frontmatter `title:` and its `## Description` body to the refined version, so every later phase sees the refined ticket.

**Third — write the report** (at `guided`, show a preview first and ask whether anything from the conversation is missing; at `balanced` / `auto` the preview was part of the checkpoint above — just write it), at `.dev-assistant/issues/$ARGUMENTS/refinement/report.md`:

```markdown
---
issue: $ARGUMENTS
phase: refinement
status: complete
autonomy: <guided | balanced | auto>
jira_updated: true | false | skipped-experimental | manual-paste
---

# Refinement report — $ARGUMENTS

## Summary

One paragraph: what the ticket looked like on arrival, what the exploration changed, the direction chosen.

## Original ticket

Title and description verbatim, as they were before this phase. Plus any comments / linked issues that informed the discussion.

## Exploration

The substance of the conversation, organized by thread (real ask, feasibility, alternatives, scope edges, constraints). Quote the user where their wording matters. Include the repo files examined and what each told us about feasibility. This section is allowed to be long — it is the only record of the discussion.

## Alternatives considered

One subsection per candidate direction: what it was, what it would take, why it was set aside (or chosen). Honest reasons, not boilerplate.

## Decision

The chosen direction and its rationale, traced back to the exploration. If the outcome was "split" or "don't do it", record that here instead.

## Refined ticket

Final title and description as approved (and applied to Jira, per the frontmatter flag).

## Open questions for gathering

What refine could not settle — the head start for /dev-gather's open-questions list.

## Decided without review

(`balanced` / `auto` only — omit the section at `guided`.) What you settled without a checkpoint: which direction won and on what evidence, which alternatives you dropped before the user saw them, anything in the report the user has not read line by line.
```

Close by telling the user the natural next step is `/dev-gather $ARGUMENTS`, which will pick this report up as a source.
