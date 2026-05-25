# Output style — how dev-assistant writes artifacts

Apply this guidance whenever a slash command writes a file (gather report, objectives, plan, execution notes, evaluation, etc.). Consistency across phases makes the artifacts feel like one coherent system.

## Frontmatter

Every artifact file starts with YAML frontmatter capturing identity and state:

```yaml
---
issue: <issue-id>
phase: <gathering | plan | execution | evaluation>
status: <draft | complete>
[extra fields per phase, e.g., sources, finalized]
---
```

No frontmatter, no exceptions. Later phases parse it.

## Headings

- **H1 (`#`)**: the artifact's title. One per file. Includes the issue ID for grep-ability — e.g., `# Objectives — VN-742`.
- **H2 (`##`)**: top-level sections (e.g., `## Issue objectives`, `## Sources`).
- **H3 (`###`)**: subsections.
- Skip H4+. If you need a fourth level, restructure.

## Voice

- **Concise.** No preamble. No "in this document we will…" sentences. Just say it.
- **No marketing language.** Strip "robust", "enhanced", "leverage", "drive value", "seamless".
- **Active voice.** "Add X" not "X has been added".
- **Refer to the user explicitly** ("the user said…") rather than using "I" or "we" inside the artifact text.

## Quoting vs paraphrasing

- **Quote verbatim** when the source's exact words matter: the user's stated goal, a comment from the JIRA ticket, an error message, a code line.
- **Paraphrase** when summarizing — but keep the original meaning. If you catch yourself adding interpretive words ("apparently", "it seems"), pull back: that's editorializing.
- When in doubt, quote.

## Length per section

- **Summary sections**: one paragraph, 3–5 sentences max. If you need more, split into subsections.
- **List sections**: 3–10 items. More than 10 → group into subcategories. Fewer than 3 → consider whether the section is needed at all.
- **Body sections**: as long as needed for clarity, no longer.

## Checkboxes

Use `- [ ]` for items with a done/not-done state that later phases will flip:

- Objectives (process and issue)
- Deliverables
- Acceptance criteria
- Action items

Use plain bullets `-` for non-state content: sources consulted, constraints, observations, analysis.

## Cross-references

Link between artifacts using relative paths:

```markdown
See [report.md](./report.md) for full context.
```

Don't restate content across files. Link instead.

## What to avoid

- **Emoji headers** (🚀 etc.). Use plain markdown.
- **Code fences for non-code content.** Use markdown formatting (lists, tables) instead.
- **Tables that could be lists.** Lists are easier to edit and diff cleanly.
- **Filler phrases** ("It is worth noting that…", "Of course,…", "It should be mentioned that…"). Cut them.
- **ALL CAPS for emphasis.** Use bold sparingly. If everything is emphasized, nothing is.
- **Hedging** ("perhaps", "maybe", "it might be that"). State the claim and call out the uncertainty separately if real.

## Examples

Bad:

> # Gathering Report
>
> In this document, we will outline the various pieces of information that have been gathered during the course of our investigation into the issue. It is worth noting that we have leveraged multiple sources to ensure a robust and comprehensive understanding.

Good:

> # Gathering report — VN-742
>
> ## Summary
>
> The user wants to add OAuth2 SSO. Background from JIRA: an enterprise customer requested it last quarter. Two open questions remain — see "What's missing" below.
