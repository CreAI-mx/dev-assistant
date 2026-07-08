# PR template (default)

This is the default structure for a PR body and title. Repos may override per-repo by running `dev-assistant strategies customize pr-template`. If the target repo has its own `.github/PULL_REQUEST_TEMPLATE.md`, prefer that as the body shape — fall back to this when there's no repo-level template.

## Title format

`[<TICKET>] <imperative summary, no trailing period>`

Examples:
- `[VN-123] Add OAuth2 flow for SSO users`
- `[VN-456] Fix race in webhook handler`
- `[INFRA-7] Migrate CI runners to ubuntu-24.04`

The title should be specific enough that a reviewer skimming the PR list knows what to expect. Don't reuse the ticket title verbatim if it's vague — sharpen it. Capitalized, no period.

## Body structure

```markdown
## Ticket

- [<TICKET>](<link to ticket tracker>)

## Description

<2–3 bullets derived from the ticket description and the actual changes.
Focus on WHY and WHAT, not HOW. The diff shows the HOW.>

## Type of change

- [ ] Feature
- [ ] Bug fix
- [ ] Hotfix
- [ ] Docs
- [ ] Refactor
- [ ] CI/build

## Checklist

- [ ] Tests added/updated and passing
- [ ] Docs updated if needed
- [ ] No new security or performance concerns
- [ ] Conventional commits used

## Security and testing notes

<Deployment, security, or testing considerations the reviewer should know.
Leave blank if there are none — don't fill with "N/A".>

## Commit map

<Reviewer aid, appended at execute wrap-up: one row per commit, grouped by
subtask, linking each commit to its Jira subtask so the PR can be reviewed
commit-by-commit. /dev-feedback appends a row per review-fix commit.>

| Commit | Subtask | Jira | What it does |
|---|---|---|---|
| <short-sha> | 01 — <subtask title> | <JIRA-KEY or —> | <commit subject> |
```

## Style for the description bullets

- **Lead with the verb.** "Add X", "Fix Y", "Refactor Z". Not "X was added".
- **Two to three bullets is the sweet spot.** One is too thin; five is too many — split the PR via sub-branches.
- **Mention behavior changes a reviewer would otherwise miss** — defaults changed, public APIs altered, env vars added.
- **Don't paraphrase the diff.** Describe the outcome, not the mechanism. "Replaced the regex-based parser with an AST parser" → "Parse markdown via AST so nested fences round-trip correctly."

## Checking the boxes

- **Type of change**: derive from the dominant commit type on the branch (`feat` → Feature, `fix` → Bug fix, etc.). Tick exactly one — if you can't, the PR is doing too much.
- **Tests added/updated and passing**: tick only if both halves are true. If the repo has no test suite, leave unchecked and explain in Security and testing notes.
- **Docs updated if needed**: tick if docs were updated *or* if no docs needed updating. Don't tick if docs needed an update but didn't get one.
- **Conventional commits used**: should always be true — see `branching-strategy.md`.

## When to break a PR into smaller ones

Split via sub-branches (`feat/<TICKET>-<slug>-sub-N`) when:

- You'd need more than three "Description" bullets to explain it.
- The diff exceeds ~400 lines across unrelated files.
- The work has natural sequencing (must merge X before Y).
- Reviewers would need to context-switch between unrelated concerns to review one PR.

## Don't

- Paste the raw ticket markup as the description. Summarize.
- Use marketing language ("powerful", "robust", "streamlined"). Strip it.
- Include personal asides ("I think this is the right approach"). Save those for review comments.
- Self-review or auto-approve. Even tiny PRs need a second pair of eyes.
