# Branching strategy (default)

Sprint-driven, multi-branch, clean releases. This is the default branching strategy used by dev-assistant when creating branches, building commit messages, and reasoning about git workflow. Override per-repo by running `dev-assistant strategies customize branching-strategy` and editing `.dev-assistant/strategies/branching-strategy.md`.

The default assumes:

- `develop` is the long-lived integration branch.
- Each sprint cuts a `version/x.y.z` branch from `develop` with a Draft PR opened immediately.
- Feature branches (`feat/<TICKET>-<slug>`) branch off the **version branch**, not `develop`.
- Conventional Commits on every commit.
- Rebase, never merge, before opening a PR.

## Goals

- **Sprint clarity** — 1 Jira ticket = 1 GitHub issue. Always know what's in flight.
- **Multi-branch tickets** — Split large tickets into focused sub-branches. No giant PRs.
- **Clean releases** — Releases are deliberate, traceable, and always releasable.

## Branch structure

| Branch type | Naming pattern | Base | Notes |
|---|---|---|---|
| Integration (permanent) | `develop` | — | Never commit directly. |
| Sprint version (temporary) | `version/x.y.z` | `develop` | One per sprint. Draft PR → `develop` opened immediately with sprint checklist. Deleted after merge. |
| Feature (temporary) | `feat/<TICKET>-<slug>` | version branch | One per ticket. Rebased before review. Deleted after merge. |
| Sub-branch (optional, temporary) | `feat/<TICKET>-<slug>-sub-N` | parent feature branch | Use when a feature is too big for one PR. Suffix uses `-` (not `/`) to avoid Git ref hierarchy conflicts. |

## Conventional Commits

All commits follow the [Conventional Commits](https://www.conventionalcommits.org/) spec. The commit type must match the branch purpose.

**Format:** `<type>(scope): <description>`

| Type | When to use |
|---|---|
| `feat` | New capability |
| `fix` | Bug fix |
| `refactor` | Code change, no behavior change |
| `chore` | Build process, dependencies, tooling |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `perf` | Performance |
| `ci` | CI/CD configuration |

First-line description is capitalized, imperative, no trailing period. Body bullets use `- <keyword>: <very short summary>`. Reference the ticket in the footer:

```
feat(auth): Add OAuth2 flow for SSO users

- add: provider config
- add: callback handler
- refactor: extract token validation

refs <TICKET>
```

Pass via HEREDOC to preserve newlines.

## Rules

1. **Never commit directly to `develop` or to a sprint version branch.** All changes go through a PR. No exceptions.
2. **One Jira ticket = one GitHub issue = one `feat/` branch = one checklist item** on the sprint version PR.
3. **Rebase, not merge, before review.** Push with `--force-with-lease` after rebasing. Linear history is mandatory.
4. **Commit type must match branch purpose.** A `feat/` branch carries `feat | refactor | test | chore | docs` commits — and `fix` only when the branch is bug-driven.
5. **Delete branches after merge.** Stale branches are noise. Feature and version branches are deleted as soon as they're merged.
6. **Avoid long-lived feature branches.** A branch open more than a few days drifts. Use sub-branches to land work incrementally.

## Step-by-step workflow

### 1. Create the GitHub issue mirroring the Jira ticket

Title format: `<TICKET>: <imperative description, no period>`. Include the Jira link in the body.

### 2. Create or identify the sprint version branch

Check if a `version/x.y.z` branch exists for the current sprint. If not, create one from `develop`.

```bash
git checkout develop
git pull origin develop
git checkout -b version/x.y.z
```

Immediately open a Draft PR `version/x.y.z` → `develop` with a sprint checklist.

### 3. Branch off the version for the feature

```bash
git checkout version/x.y.z
git checkout -b feat/<TICKET>-<slug>
```

### 4. (Optional) Sub-branches for large features

If a feature is too large to review in one PR, split into sub-branches off the parent feature branch. Merge subs into the parent feature branch, **not** into the version branch.

```bash
git checkout feat/<TICKET>-<slug>
git checkout -b feat/<TICKET>-<slug>-sub-1
```

### 5. Commit using Conventional Commits

Every commit follows the format above. Reference the ticket in the footer.

### 6. Rebase, then open the PR

```bash
git fetch origin
git rebase origin/version/x.y.z
git push --force-with-lease origin feat/<TICKET>-<slug>
```

PR target = the sprint version branch. Requires at least 1 approval.

### 7. After approval, merge and delete

The feature branch is deleted after merge. The sprint version branch is marked Ready for Review when all features are merged into it; then merged into `develop`, tagged, and deleted at sprint end.

```bash
git tag v<x.y.z>
git push origin --tags
git push origin --delete version/<x.y.z>
```

## PR conventions

| PR type | Source → Target | Initial state | Notes |
|---|---|---|---|
| Sprint version PR | `version/x.y.z` → `develop` | Draft → Open | Opened at sprint start; sprint checklist; marked Ready when all features merged |
| Feature PR | `feat/<TICKET>-<slug>` → `version/x.y.z` | Open | One per ticket; rebased; 1+ approval |
| Sub PR | `feat/<TICKET>-<slug>-sub-N` → parent feature | Open | Sequentially merged (`sub-1` before `sub-2`) |

## Quick reference — "What do I do when…"

| Situation | What to do |
|---|---|
| New Jira ticket | Step 1 |
| Start coding a feature | Step 3 (ensure version branch exists — Step 2) |
| Feature too big for one PR | Use sub-branches — Step 4 |
| Ready to push | Rebase first, then push — Step 6 |
| All sprint features merged into version | Mark version PR ready, then Step 7 |
| Not sure which branch to branch from | Feature branches come from `version/x.y.z`. Sub-branches come from the parent feature branch. **Never** branch features directly from `develop`. |
| Fixing a bug | Same flow as a feature, but use `fix` as the commit type |

## When this default doesn't fit

Customize the per-repo override for:

- Trunk-based development (no sprint version branch; feature branches off `main`).
- Multiple long-lived release branches (`release/x.y`) needing separate hotfix flows.
- Monorepos with per-package branch conventions.
- Repos with branch protection patterns that block `feat/` or `version/` prefixes.
