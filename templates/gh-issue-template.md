# GitHub issue template (default)

The default body shape for the GitHub issue that mirrors a Jira ticket, per the branching strategy's rule "1 Jira ticket = 1 GitHub issue". Created at sub-phase 1a of `/dev-execute` when the user opts in. Override per-repo by running `dev-assistant strategies customize gh-issue-template`.

## Title format

`[<TICKET>] <imperative description, no trailing period>`

Examples:
- `[VN-742] Add OAuth2 flow for SSO users`
- `[VN-456] Fix race condition in webhook handler`

Capitalized. Imperative verb up front. No trailing period. The bracketed ticket prefix makes the GH issue list scannable alongside the Jira board.

## Body structure

```markdown
## Jira

- [<TICKET>](<link to Jira ticket>)

## Context

<1–2 sentences drawn from gathering/objectives.md: the underlying goal in the user's own words. Not a paraphrase of the Jira ticket.>

## Objectives

<Pulled from gathering/objectives.md. Pasted as-is from the "Specific" list.>

- [ ] Specific objective 1
- [ ] Specific objective 2
- [ ] ...

## Planned subtasks

<From plan/plan.md. One bullet per subtask, with planned commit count.>

- Subtask 01 — <title> (~<n> commits)
- Subtask 02 — <title> (~<n> commits)
- ...

## Branch

`feat/<TICKET>-<slug>` (target: `version/<resolved x.y.z>`)
```

## Style notes

- **No marketing language.** Strip "powerful", "robust", "streamlined".
- **Keep it scannable.** Reviewers may land on this issue first; they should grasp scope in 15 seconds.
- **Reference, don't restate.** Link to the Jira ticket; don't paste its description.
- **Objectives are checkboxes** — they get ticked as subtasks merge in.

## What to avoid

- Pasting the full Jira description (it lives in Jira, not GitHub)
- Implementation details that belong in the impl-plan, not the issue
- Personal asides ("I think this approach is best") — save for review comments
- Filler ("This issue tracks...") — just say what it tracks

## When this default doesn't fit

Customize the per-repo override for:

- Repos with a strict `.github/ISSUE_TEMPLATE/` convention — prefer that template, fall back to this only when none exists.
- Repos that don't use Jira (drop the Jira section, keep the rest).
- Repos that require labels / milestones / assignees in the body — extend the structure.
