# Jira subtask template (default)

The default summary and description shape for Jira subtasks created under a parent ticket. Created at sub-phase 1a of `/dev-execute` when the user opts in, per dev-assistant subtask. Override per-repo by running `dev-assistant strategies customize jira-subtask-template`.

## Summary (Jira "Summary" field)

`<imperative title from the dev-assistant subtask>`

Pulled directly from the subtask's `title:` field in `plan.md`. Capitalized, imperative, no trailing period. Examples:

- `Add OAuthProvider base class`
- `Wire OAuth callback into the auth router`
- `Add unit tests for OAuthProvider`

## Description (Jira "Description" field)

```
*Parent:* <TICKET>
*Branch:* feat/<TICKET>-<slug>
*Subtask:* 01 of N

h3. Objectives

* What done looks like for this subtask (from plan.md)

h3. What's affected

* path/to/file.py
* path/to/other.py

h3. Passing criteria

* (#) Mechanically verifiable item
* (#) Mechanically verifiable item

h3. Planned commits

* feat(scope): Description for first commit
* test(scope): Description for second commit
```

Jira uses its own markup (`h3.` for headings, `*` for italics, `(#)` for numbered list). Don't use Markdown headings or bold here.

## Style notes

- **Reference the parent ticket** so the subtask is obviously linked even if the Jira hierarchy is collapsed.
- **Reference the branch** so reviewers can locate the work without digging.
- **Keep passing criteria identical** to what's in `plan.md` — drift between Jira and dev-assistant artifacts causes confusion later.
- **No PR link yet.** The PR opens at wrap-up, after all subtasks merge into one PR. Subtask-level Jira entries link to commits at most, not PRs.

## What to avoid

- Pasting impl-plan content (lives in the local repo, not Jira)
- Long prose narratives (the subtask is a checklist, not a story)
- Marketing language and hedging
- Status updates ("done!", "in progress") — Jira's workflow handles state

## When this default doesn't fit

Customize the per-repo override for:

- Teams that require specific Jira custom fields (epic link, story points, sprint)
- Teams that prefer Atlassian Document Format (ADF) over wiki markup
- Repos where subtasks should mirror commits rather than dev-assistant subtasks (different decomposition unit)
