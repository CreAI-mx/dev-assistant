# Interaction map — every point where dev-assistant stops for you

Status: **current as of 0.6-unreleased. Part 1 is the inventory of `guided` behavior; part 2 documents the `autonomy` setting, which is implemented.**

Part 1 inventories every place in the lifecycle where a command stops and waits for the user, with file references — this is what `guided` (the pre-0.6 behavior) does. Part 2 documents the issue-level `autonomy` setting that controls how many of those stops fire.

## How to read this

Every stop is classified by **kind**, because only two of the four kinds are safe to remove:

| Kind | Name | What it is | Removable? |
|---|---|---|---|
| **C** | Content | Information only the user has — it cannot be derived from the repo, the ticket, or the artifacts. Refine's exploration, gather's direct-input questions, undocumented constraints. | No (compressible) |
| **A** | Approval | Approving a draft or a decision the assistant already made — a decomposition, an impl plan, a triage, a retro. | Yes |
| **G** | Gate | Confirmation before something leaves the machine — push, PR, comment, transition, merge. | Batchable, never fully removable |
| **E** | Escalation | Something failed or is ambiguous: conflicts, failing criteria, mechanical-check failures, readiness ✗. | No |

`×N` in the count column means the stop fires once per subtask / cluster / round / invocation.

---

## Part 1 — The inventory

### `/dev-refine` — 6 stops + one open conversation

| # | Where | What is asked | Kind | Count |
|---|---|---|---|---|
| R1 | 1 (`dev-refine.md:53`) | "Is this the right ticket?" after the Jira fetch | A | 1 |
| R2 | 1 | Paste title + description (only when the Atlassian MCP is unavailable) | C | 0–1 |
| R3 | 1 | "Is this experimental/sandbox work?" before `issue create` | C | 1 |
| R4 | 2 (`:70`) | **The exploration conversation** — 5 threads (real ask, feasibility, alternatives, scope edges, constraints), explicitly one question at a time | C | ~5–12 turns |
| R5 | 3 (`:82`) | Agree with the convergence summary — iterates until settled | A | 1+ |
| R6 | 4 (`:92`) | Approve the exact rewritten title + description | A | 1+ |
| R7 | 5 (`:101`) | "Anything from the conversation missing?" before the report is written | A | 1 |

The Jira title/description write in sub-stage 5 is gated on R6 rather than being its own confirmation.

### `/dev-gather` — 9 stops + one open conversation

| # | Where | What is asked | Kind | Count |
|---|---|---|---|---|
| G1 | 1 (`dev-gather.md:51`) | Which sources to consult | C | 1 |
| G2 | 2 (`:63`) | Jira: confirm the right ticket, flag what's missing | A | 1 |
| G3 | 2 | Repo: which files/areas are relevant | C | 1 |
| G4 | 2 | Meeting notes: paste them | C | 0–1 |
| G5 | 2 | **Direct input** — 5 guiding questions, explicitly one at a time | C | ~5 turns |
| G6 | 2 | Per-source takeaway summary shown before moving to the next source | A | 1×source |
| G7 | 3 (`:91`) | Which process objectives don't apply to this issue | C | 1 |
| G8 | 4 (`:97`) | Iterate on the draft general + specific objectives | A | 1+ |
| G9 | 5 (`:108`) | Four validation questions (missing? open questions? constraints? accurate?) then write | A | 1 |
| G10 | re-run | Which sections to revise | A | 0–1 |

### `/dev-plan` — ~17 stops for a 4-subtask issue (the heaviest phase)

The file states it outright: *"Every sub-stage has a user pause."*

| # | Where | What is asked | Kind | Count |
|---|---|---|---|---|
| P1 | 1 (`dev-plan.md:87`) | "Is this the right context to plan from?" | A | 1 |
| P2 | 2 (`:106`) | Iterate on the decomposition table (2–5 subtasks) | A | 1+ |
| P3 | 3 (`:124`) | Approve each subtask's full spec — walked one subtask at a time | A | ×N |
| P4 | 3 | "1, 2, or 3 commits for this subtask?" | A | ×N |
| P5 | 4 (`:144`) | Sequencing, flow (feature/hotfix), branch slug, branching mode, target branch, coverage map | A | 1+ |
| P6 | 5 (`:159`) | Four conversational viability questions, one at a time | C/A | 4 |
| P7 | 5 | Preview of both files → final confirmation | A | 1 |
| P8 | 5 | Post-write revision pass ("anything to revisit now it's on paper?") — up to 2 rounds | A | 1–2 |
| P9 | re-run | Which sections to revise | A | 0–1 |

### `/dev-execute` — ~7 on the first subtask, ~2 on later ones, ~5 at wrap-up (+5 per subtask in `sub-branches`)

| # | Where | What is asked | Kind | Count |
|---|---|---|---|---|
| E1 | 1a (`dev-execute.md:113`) | "Create the GitHub issue now? (y/n)" | G | 1 (first) |
| E2 | 1a | Confirm the GH issue title + body | G | 1 (first) |
| E3 | 1a | "Create Jira subtask for subtask N? (y/n)" | G | ×N |
| E4 | 1a | Confirm the Jira summary + description + assignee | G | ×N |
| E5 | 1b (`:135`) | `sub-branches`: previous sub-PR unmerged → wait or stack | E | ×N |
| E6 | 1c (`:173`) | Push the feature branch | G | 1 (first) |
| E7 | 1c | Open the draft PR (title + body shown) | G | 1 (first) |
| E8 | 1c | Comment on the Jira parent | G | 1 (first) |
| E9 | 2.2 (`:232`) | Mechanical checks still failing after 2 re-drafts → approve / abandon / edit | E | rare |
| E10 | 2.3 (`:247`) | **Impl plan: approve / refine / abandon** | A | ×N |
| E11 | 3.2 (`:290`) | Files touched outside the plan → surfaced to the user | E | rare |
| E11b | 3.2 | **Still over the size budget after the automatic trim pass** → trim more / accept / re-plan / split | E | occasional |
| E12 | 3.3 (`:299`) | Commit failed (hook, conflict) → stop | E | rare |
| E13 | 3.6 (`:335`) | Passing criteria still failing after one auto-fix → retry / reset / abandon | E | rare |
| E14 | 3.8 (`:382`) | `sub-branches`: push parent, push sub-branch, open sub-PR, Jira subtask comment | G | 4×N |
| E15 | 4.2 (`:429`) | "Handle deferred external prep now?" + one prompt per item | G | 1 |
| E15b | 4.2b | Reduction pass — proposed removals over the issue's whole diff (`guided` only; applied and reported at `balanced` / `auto`, since a verified deletion needs no approval) | A | 1 |
| E16 | 4.3 (`:442`) | Rebase conflicts → hard stop | E | rare |
| E17 | 4.4 (`:453`) | Push (force-with-lease, post-rebase) | G | 1 |
| E18 | 4.5 (`:464`) | Update PR body + mark ready for review | G | 1 |
| E19 | 4.5b (`:498`) | Hotfix: open the `develop` sync PR | G | 0–1 |
| E20 | 4.6 (`:507`) | Post the Jira parent comment | G | 1 |
| E21 | re-run | Re-running a `status: done` subtask → confirm | E | rare |

### `/dev-feedback` — ~9 per round

| # | Where | What is asked | Kind | Count |
|---|---|---|---|---|
| F1 | args (`dev-feedback.md:19`) | `sub-branches` with no subtask arg → which sub-PR? | A | 0–1 |
| F2 | 2.3 (`:241`) | **Triage checkpoint** — approve / reclassify / defer / abandon | A | 1+ |
| F3 | 4.1 (`:377`) | Per-cluster impl plan — approve / refine / skip (nit clusters can be batch-approved) | A | ×clusters |
| F4 | 5.1 (`:444`) | **Reply batch** — all drafted replies as one set, before any post | A | 1+ |
| F5 | 5.2 (`:506`) | Push (force-with-lease) | G | 1 |
| F6 | 5.4 (`:528`) | Resolve threads — all / per cluster / skip | G | 1 |
| F7 | 5.5 (`:550`) | Update the PR body's commit map | G | 1 |
| F8 | 5.6 (`:562`) | Remote-state ✗ (reply missing, branch out of sync, thread unresolved) → user decides | E | rare |

### `/dev-merge` — 3–4 (feature), up to 7 (hotfix)

| # | Where | What is asked | Kind | Count |
|---|---|---|---|---|
| M1 | pre-flight (`dev-merge.md:64`) | Hotfix with no `develop_pr_url` → open the sync PR now? | G | 0–1 |
| M2 | 1 (`:68`) | Readiness ✗ → stop; per-item override is possible but explicit | E | 0–1 |
| M3 | 2 (`:94`) | Merge-commit subject + body → "Merge into `<target>`? Proceed?" | G | 1–2 |
| M4 | 3 (`:114`) | Delete the remote branch | G | 1 |
| M5 | 4 (`:123`) | Post the Jira merge comment | G | 1 |

### `/dev-evaluate` — 3

| # | Where | What is asked | Kind | Count |
|---|---|---|---|---|
| V1 | 3.3 (`dev-evaluate.md:234`) | Retro + lessons — approve / edit retro / edit lessons / abandon | A | 1+ |
| V2 | 4.5 (`:352`) | **External batch** — GH comment, Jira subtask transitions, Jira parent transition, GH issue close | G | 1+ |
| V3 | 5.4 (`:551`) | Archive the workspace or leave it in place | A | 1 |

### `/dev-review` — 3 + one open conversation (separate track: reviewing someone else's PR)

| # | Where | What is asked | Kind | Count |
|---|---|---|---|---|
| W1 | 1.1 (`dev-review.md:88`) | Jira key found but no MCP → paste the ticket, or skip | C | 0–1 |
| W2 | 2.3 (`:135`) | **Q&A** — open-ended working conversation; ends when the user says "done" | C | N turns |
| W3 | 4 (`:201`) | **Finding selection** — nothing posts unless explicitly selected | A | 1+ |
| W4 | 5.1 (`:233`) | Batch + verdict approval — the single checkpoint before anything leaves the machine | G | 1+ |

### Totals

For a representative issue — 4 subtasks, `single-branch`, feature flow, 2 feedback rounds:

| Phase | Discrete stops | Open-conversation turns |
|---|---|---|
| refine | 6 | ~5–12 |
| gather | 9 | ~5 |
| plan | ~17 | — |
| execute | ~18 | — |
| feedback | ~18 (2 rounds) | — |
| merge | 4 | — |
| evaluate | 3 | — |
| **Total** | **~75** | **~10–17** |

`sub-branches` mode adds ~5 per subtask. The hotfix flow adds ~3. Every additional feedback round adds ~9.

By kind: roughly 45% A (approvals), 35% G (external gates), 12% C (content), 8% E (escalations). **The approvals are the bulk, and they are the removable ones.**

---

## Part 2 — The `autonomy` setting

### The setting

`autonomy: guided | balanced | auto` in `issue.md` frontmatter, **defaulting to `balanced`** at creation:

```
dev-assistant issue create --id VN-742 --title "..." --autonomy balanced
dev-assistant issue set-flag --id VN-742 --autonomy auto     # change mid-flight
```

It reaches every command through the `!dev-assistant issue show --id $1` block each one already runs — that command prints an `## Autonomy` block with the resolved level. A missing field reads as `guided`, so issues created before this change behave exactly as they did. A per-invocation override (`/dev-plan VN-742 --guided`) lets one phase be walked in full without changing the issue's setting.

### What each level does

| | **guided** | **balanced** | **auto** |
|---|---|---|---|
| **C** — content | as today, one question at a time | as today for refine; other phases ask their questions as **one block** | one block, once per phase |
| **A** — approvals | every one | **collapsed to one per phase** | dropped; the decision is made and **recorded in the phase report as unreviewed** |
| **G** — external gates | one per operation | **one batch per phase** | one batch per phase (unchanged from balanced) |
| **E** — escalations | always stop | always stop | always stop |

### Per-phase shape under `balanced`

Each phase command carries its own `## Autonomy level` section with this table filled in for its own stops; what follows is the summary.

- **refine** — the exploration conversation is untouched (this is the part that works). R1, R5, R6, R7 collapse into **one checkpoint**: chosen direction + rewritten title/description + report preview, approved together; approval releases the Jira write. **6 → 1.**
- **gather** — G1 (sources) and G5 (direct input, asked as one block of 5 questions) stay. G2, G6, G7, G8, G9 collapse into **one checkpoint**: the drafted `objectives.md` + `report.md` preview + the process-objective exclusions, approved together. **9 → 3** (two of them the irreducible content stops; `auto` drops the checkpoint, leaving 2).
- **plan** — the whole plan is drafted end to end and shown **once**: decomposition, per-subtask specs, commit counts, sequencing, flow, branching mode, coverage map, and the assistant's own answers to the four viability questions (marked as self-answered). Approve / revise / restart. **17 → 1.**
- **execute** — the reduction pass at wrap-up (4.2b) is an approval at `guided` only: at `balanced` / `auto` its removals are applied and reported, because a deletion that keeps every passing criterion green is the one edit that needs no sign-off. A size overshoot that survives the automatic trim is an escalation and stops at every level. Otherwise, per invocation: **one approval** (the impl plan) and **one external batch** (GH issue, Jira subtask, push, PR, Jira comment — everything 1a/1c/4.x would ask separately, shown as one list of ops with their payloads). **7 → 2 on the first subtask, 2 → 2 later, 5 → 1 at wrap-up.**
- **feedback** — **one approval** after sub-phase 3 (triage + every cluster impl-plan + every drafted reply in a single view) and **one external batch** after the fixes commit (final replies with their SHAs + push + post + resolve + commit map). The batch-reply rule survives intact: no reply posts before the whole set is reviewed. **9 → 2 per round.**
- **merge** — readiness ✗ still stops. The merge-commit message, branch deletion, and Jira comment become **one confirmation**. A hotfix still confirms twice (two merges = two irreversible acts). **4 → 2.**
- **evaluate** — retro + lessons + the external batch in **one view**, approved together; archiving becomes the default (reversible, recorded). **3 → 1.**
- **review** — unchanged at every level. The selection gate and the batch approval are the product.

Estimated total for the same representative issue: **~75 → ~20** under `balanced`, **~12** under `auto` — and at `auto` nearly all of the remainder are external-write gates.

### Hard floors (no level removes these)

1. **The merge confirmation.** Least reversible operation in the lifecycle.
2. **At least one explicit approval before any batch of external writes fires**, per phase. `auto` means *fewer prompts*, not *unattended publishing*.
3. **`/dev-review`'s selection gate and batch approval.** No finding reaches GitHub unattested.
4. **Escalations** — conflicts, failing criteria after auto-fix, readiness ✗, remote-state mismatches.
5. **Refine's exploration conversation**, when refine is run at all. A ticket cannot be refined against silence.

### The honesty requirement

Fewer approvals means the artifacts have to carry what the user no longer saw. Every phase report gains an `autonomy: <level>` frontmatter field and a **`## Decided without review`** section listing what the assistant settled alone — commit counts, the viability rubric answers, triage classifications, cluster skips. The audit trail is what makes a lower level safe to use.

### Where it lives in the code

- `src/dev_assistant/cli.py` — the `Autonomy` enum, `AUTONOMY_DEFAULT`, `--autonomy` on `issue create` and `issue set-flag`, `_set_frontmatter_field`, and `_resolve_autonomy` (which `issue show` prints as the `## Autonomy` block).
- `.claude/commands/dev-{refine,gather,plan,execute,feedback,merge,evaluate}.md` — an `## Autonomy level` section in each, plus a level annotation on each stop in part 1. `/dev-review` carries a section explaining why it does not vary.
- `src/dev_assistant/tui/{model,render}.py` — `Issue.autonomy`, resolved by `model._autonomy`, shown as a badge beside `experimental`.
- `docs/user-guide.md` (§6 Autonomy), `README.md`, `CHANGELOG.md`.

### Open questions

- **Is `balanced`'s single checkpoint placed right in every phase?** In plan it lands before the write, in gather before the write, in feedback after drafting but before applying, in evaluate inside the external batch. Those are judgment calls that only real use will validate.
- **Does `auto` produce plans worth executing?** The sub-stage 5 rubric is answered by the same model that wrote the plan. `IDEAS.md` has a deferred design for an independent evaluator subagent — if `auto` plans turn out to need refinement often, that is the idea to revisit.
- **Should the level be settable per phase** (`autonomy: {plan: guided, execute: auto}`) rather than per issue? The per-invocation override token covers the common case for now.
