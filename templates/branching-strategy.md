# Branching strategy (default)

Sprint-driven, trunk-friendly, fast feedback. This is the default branching strategy used by dev-assistant when creating branches, building commit messages, and reasoning about git workflow. Override per-repo by running `dev-assistant strategies customize branching-strategy` and editing `.dev-assistant/strategies/branching-strategy.md`.

The default assumes:

- `develop` is the long-lived integration branch. **All feature work lands here directly** — there is no batch gate.
- `uat` is a second long-lived branch that mirrors what is deployed to UAT. Hotfixes target it.
- Feature branches (`feat/<TICKET>-<slug>`) branch off **`develop`** and merge back into `develop`.
- Work starts by opening a **Draft PR** before writing code — so an empty "open draft pr" commit is made first to give the PR a base.
- Conventional Commits on every commit.
- Rebase, never merge, before opening a PR.

## Goals

- **Sprint clarity** — 1 Jira ticket = 1 Draft PR. Always know what's in flight.
- **Fast feedback** — Features land in `develop` as soon as they're ready and reviewed. No batch gates.
- **Multi-repo safety** — Cross-repo features coordinate through a shared branch name before touching `develop`.
- **Clean releases** — Version tags are semantic, deliberate, and cut at the end of the sprint on `develop`.

## Branch structure

| Branch type | Naming pattern | Base | Notes |
|---|---|---|---|
| Integration (permanent) | `develop` | — | All feature work lands here. Never commit directly. |
| UAT mirror (permanent) | `uat` | — | Mirrors what is deployed to UAT. Hotfixes target it. Never commit directly. |
| Feature (temporary) | `feat/<TICKET>-<slug>` | `develop` | One per ticket. Rebased before review. Merges directly into `develop`. Deleted after merge. |
| Sub-branch (optional, temporary) | `feat/<TICKET>-<slug>-sub-N` | parent feature branch | Use when a feature is too big for one PR. Merges into the parent feature branch only — never directly into `develop`. Suffix uses `-` (not `/`) to avoid Git ref hierarchy conflicts. |
| Cross-repo (temporary) | `feat/<TICKET>-<slug>--xrepo` | `develop` | Cross-repo variant of any branch type. Same branch name across all affected repos. The `--xrepo` suffix signals multi-repo coordination is required. Deleted after all repos merge. |
| Hotfix (temporary) | `hotfix/<TICKET>-<slug>` | `uat` | Emergency fix that must reach UAT before the next normal deploy. **Two PRs:** one into `uat` (emergency deploy), one into `develop` (keeps them in sync). |

The `--xrepo` suffix keeps the change type first (how you scan branches) and is easy to grep: `git branch | grep -- --xrepo`. A separate prefix like `sync/` would lose the semantic type.

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

1. **Never commit directly to `develop` or `uat`.** All changes go through a PR. No exceptions.
2. **1 Jira ticket = 1 Draft PR.** Open it when you start, not when you finish. Link the Jira ticket in the description. This refers to the **parent** ticket: Jira subtasks live under it and never get their own GitHub issue or top-level PR — at most they get a sub-branch and sub-PR off the parent `feat/` branch, all referencing the same parent ticket.
3. **Pull from `develop` before branching.** Never start work from a stale base.
4. **Rebase, not merge, before review.** Push with `--force-with-lease` after rebasing. Linear history is mandatory.
5. **Commit type must match branch purpose.** A `feat/` branch carries `feat | refactor | test | chore | docs` commits — and `fix` only when the branch is bug-driven.
6. **Single-repo features go straight to `develop`.** No version branch needed.
7. **Multi-repo features use the `--xrepo` suffix.** Same branch name across repos; the feature owner coordinates merge timing and keeps the partial-state window short.
8. **Hotfixes branch off `uat`, not `develop`** (develop may have unreleased work). **Every hotfix needs two PRs** — one into `uat`, one into `develop` — or the branches drift out of sync.
9. **Delete branches after merge.** Stale branches are noise.
10. **Version tags carry semantic meaning.** Cut the tag that's semantically accurate (PATCH for a fixes-only sprint), not the convenient one.
11. **Infrastructure changes require a Slack tag.** Any PR touching infrastructure — secrets, env vars, service config — must tag the infra owner in the Slack PR review channel before deployment.

## Step-by-step workflow

### 1. Create the GitHub issue mirroring the Jira ticket

Title format: `<TICKET>: <imperative description, no period>`. Include the Jira link in the body.

### 2. Branch off `develop`, then open the Draft PR

Pull from `develop` first so you're not branching off a stale base:

```bash
git checkout develop
git pull origin develop
git checkout -b feat/<TICKET>-<slug>
```

Before you can open a PR, the branch needs at least one commit that diverges from `develop`. Make an **empty "open draft pr" commit** so the Draft PR has a base — *before* writing any feature code:

```bash
git commit --allow-empty -m "chore: open draft pr feat/<TICKET>-<slug>"
git push -u origin feat/<TICKET>-<slug>
```

Then open the Draft PR `feat/<TICKET>-<slug>` → `develop`:

- Title it so someone can tell what you're working on without asking.
- Link the Jira ticket in the description.
- Note scope: which repos, services, or flows are affected — especially in a multi-repo setup where a change in one service can quietly break another.

The Draft PR is the start-of-work signal: it shows what's in flight and forces the right questions early.

### 3. (Optional) Sub-branches for large features

If a feature is too large to review in one PR, split into sub-branches off the parent feature branch. Merge subs into the parent feature branch, **not** into `develop`.

In dev-assistant, this choice is made at plan time: `/dev-plan` records `branching_mode: sub-branches` in `plan.md`, and `/dev-execute` then creates one sub-branch + sub-PR per subtask (sub-PR opens at subtask completion, targeting the parent feature branch; the parent Draft PR was already opened in step 2 and is marked Ready at wrap-up once all subs are merged).

```bash
git checkout feat/<TICKET>-<slug>
git checkout -b feat/<TICKET>-<slug>-sub-1
```

Merge sub-branches sequentially (`sub-1` before `sub-2`).

### 4. Commit using Conventional Commits

Every commit follows the format above. Reference the ticket in the footer.

### 5. Rebase, then mark the PR Ready

```bash
git fetch origin
git rebase origin/develop
git push --force-with-lease origin feat/<TICKET>-<slug>
```

Convert the Draft PR to Ready once CI is green and the work is complete. Don't open a draft and forget to convert it. Feature PR target = `develop`. Requires at least 1 approval + CI green.

### 6. After approval, merge and delete

The feature branch is deleted after merge. The PO can review the feature in `develop` as soon as the PR merges.

## Cross-repo features (`--xrepo`)

When a feature requires coordinated changes across 2+ repos, use the `--xrepo` suffix with the **same branch name** in every affected repo. In each repo: branch off `develop`, follow the same draft-PR + empty-commit flow, and open one PR per repo into `develop`. The feature owner coordinates: all PRs must be approved before any is merged, and they merge close together so `develop` doesn't sit in a partial state.

## Hotfixes

Use when something is broken in UAT and can't wait for the next normal deploy. A hotfix bypasses `develop` to reach UAT immediately, but **must also land in `develop`** or the fix is lost on the next promotion.

```bash
git checkout uat
git pull origin uat
git checkout -b hotfix/<TICKET>-<slug>
# fix + commit
git push origin hotfix/<TICKET>-<slug>
# PR 1: hotfix/<TICKET>-<slug> → uat   (expedited review; deploys to UAT on merge)
# PR 2: hotfix/<TICKET>-<slug> → develop   (or cherry-pick into a fix/ branch if uat and develop diverged)
```

## Version tags

Version tags are cut on `develop` at the end of the sprint, based on the semantic impact of what landed.

```bash
git checkout develop
git pull origin develop
git tag v<x.y.z>
git push origin --tags
```

The tag is the release artifact; the branch is just the delivery mechanism. Not every sprint needs a MINOR bump — a fixes-only sprint is a PATCH.

## PR conventions

| PR type | Source → Target | Initial state | Notes |
|---|---|---|---|
| Feature PR | `feat/<TICKET>-<slug>` → `develop` | Draft → Ready | Opened at start (empty commit gives it a base); marked Ready when complete + CI green; rebased; 1+ approval |
| Cross-repo PR | `feat/<TICKET>-<slug>--xrepo` → `develop` | Draft → Ready | One per repo; feature owner coordinates timing across all repos |
| Sub PR | `feat/<TICKET>-<slug>-sub-N` → parent feature | Open | Sequentially merged (`sub-1` before `sub-2`) |
| Hotfix PR (UAT) | `hotfix/<TICKET>-<slug>` → `uat` | Open | Expedited review; deploys to UAT immediately on merge |
| Hotfix PR (develop) | `hotfix/<TICKET>-<slug>` → `develop` | Open | Must accompany the UAT PR — keeps branches in sync |

## Quick reference — "What do I do when…"

| Situation | What to do |
|---|---|
| New Jira ticket | Step 1 |
| Start coding a feature | Step 2 — pull `develop`, branch, empty commit, open Draft PR before writing code |
| Feature too big for one PR | Use sub-branches — Step 3 |
| Ready to push | Rebase first, then push — Step 5 |
| Work complete + CI green | Mark the Draft PR Ready — Step 5 |
| Not sure which branch to branch from | Feature branches come from `develop`. Sub-branches come from the parent feature branch. Hotfixes from `uat`. |
| Fixing a bug | Same flow as a feature, but use `fix` as the commit type |
| Emergency fix broken in UAT | Hotfix flow — branch off `uat`, two PRs (`uat` + `develop`) |
| Change spans multiple repos | `--xrepo` suffix, same branch name across repos, coordinate the merge |

## When this default doesn't fit

Customize the per-repo override for:

- Repos that still use a `version/x.y.z` sprint branch as a batch gate (the older v1.x model).
- Multiple long-lived release branches (`release/x.y`) needing separate hotfix flows.
- Monorepos with per-package branch conventions.
- Repos with branch protection patterns that block `feat/`, `hotfix/`, or `--xrepo` suffixes.
