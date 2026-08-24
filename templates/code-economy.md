# Code economy — the smallest change that fully solves the problem

Applies whenever a phase writes, plans, or reviews code: `/dev-plan` (sizing the work), `/dev-execute` (writing it), `/dev-feedback` (fixing review comments), `/dev-review` (judging someone else's diff).

## The rule

**Write the least code that satisfies the objectives and stays obvious to the next reader.** Not the fewest characters — the fewest *concepts*. A reader should be able to hold the change in their head.

The objectives in `gathering/objectives.md` are the floor. Economy never buys smallness by dropping something the issue promised.

## The tie-breaker

**When the shorter version takes longer to explain, take the longer one.**

Short and obvious beats short and clever, every time. Concretely, these are not economy — they are debt:

- Comprehensions with more than two clauses, or nested inside each other
- Chained ternaries; boolean arithmetic standing in for an `if`
- One-letter names outside a tight loop or an established idiom (`i`, `f`, `_`)
- Metaprogramming, dynamic attribute access, or decorators nobody asked for
- Single-use lambdas bound to a name (that's a function — give it a `def`)
- Collapsing two unrelated operations into one line because they fit

If you cannot say what a line does in one sentence to someone who hasn't read the ticket, it is too clever. Rewrite it longer.

## Where the lines actually come from

Most oversized diffs are not one big mistake — they are ten small ones. Check each before writing:

1. **A new file where an existing one would do.** Extend the module that already owns this concern. A new file is a new place someone has to look. Create one only when the objective names a genuinely new component.
2. **Abstraction ahead of need.** Rule of three: don't factor until the third occurrence. Two similar blocks are cheaper than one wrong abstraction.
3. **Configurability nobody asked for.** No flags, options, env vars, hooks, or extension points that aren't in `objectives.md`. "Someone might want to…" is a follow-up ticket.
4. **Defensive code for impossible states.** Validate at the trust boundary; trust the inside. Don't re-check what the caller, the type, or the prior line already guarantees.
5. **Wrapper layers.** No adapter, manager, handler, or helper class that only forwards to something else.
6. **Tests that repeat each other.** One test per behavior, plus the failure modes the plan names. Don't test the language or the framework. Don't parametrize combinatorially. Don't assert on incidental formatting.
7. **Comments and docstrings that restate the code.** Comment the *why*, and only where the why isn't visible. A comment explaining *what* a line does is a signal to rename something, not to add a line.
8. **Speculative error handling and logging.** Handle the failures the objective names. A bare `try/except` that re-raises is noise.
9. **Copy-paste of a pattern that could be a call.** The inverse of rule 2 — the third occurrence *should* be factored.
10. **Back-compat shims for callers that don't exist.** Nothing in this repo calls it yet; change it and move on.

## Deletion is progress

A change that removes more than it adds is a good change. When the objective can be met by deleting, delete. Sizes below count added lines only — **removals are never charged against a change**, and a `+40 / -90` diff is reported as the win it is.

## Size bands

Every subtask carries a planned band; every landed diff is measured against it with `dev-assistant issue size --id <issue-id>`.

| Band | Added lines | What it usually is |
|---|---|---|
| **S** | ≤ 50 | A focused change to existing code, with its test |
| **M** | 51–150 | A new function or small class plus wiring and tests |
| **L** | 151–400 | A new component the objective explicitly asks for |
| **XL** | > 400 | Not a size — a signal. Split the subtask. |

Counting rules:

- **Added lines only**, from `git diff --numstat` against the target branch.
- **Not counted:** lockfiles, generated output, vendored trees, snapshots, migrations, and anything else listed in `sizing.DEFAULT_EXCLUDES`. Add repo-specific exclusions with `--exclude`.
- **Reported separately, not exempt:** tests and docs. They are real lines someone maintains. A subtask whose tests are three times its source is over-tested, not thorough.
- **Tolerance:** a landed diff may run 25% over its band's ceiling before it counts as an overshoot. Bands are estimates, not contracts.

Issue-level budget: **a normal issue lands S or M.** One L subtask needs a written reason in the plan. More than one L, or a total past ~400 added lines, means the issue should be split — say so in `/dev-plan` rather than absorbing it.

## When bigger is right

Economy is a default, not a mandate. These are exempt, and saying so in the plan is enough:

- **Correctness and the objectives.** Never trade either for a smaller diff.
- **The repo's own conventions.** Repo context wins over this document — if the repo mandates a docstring format, a MANIFEST entry, or a specific error-handling pattern, that is not bloat.
- **Validation at trust boundaries.** User input, external APIs, and file formats get checked properly.
- **Tests for the failure modes the plan names.** Those are the tests that earn their lines.
- **Generated code, migrations, and fixtures.** Not hand-written, not read line by line.
- **Documentation the process objectives require.**

A justified L reads like *"L because the objective needs a new provider class, its registration, and round-trip tests"*. An unjustified one reads like *"L because I added a config system"*.

## Before you commit — the one-sentence test

For each function, class, file, and test the change introduces:

> What does this exist for, and which objective requires it?

If the answer needs two sentences, or names no objective, it goes. This is the whole strategy in one question.
