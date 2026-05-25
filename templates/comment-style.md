# Comment style — GitHub and Jira

Style for comments dev-assistant posts on GitHub issues, GitHub PRs, and Jira tickets. Goal: short, easy to scan, action-oriented. Reviewers and reporters skim — write for skimming.

## Principles

1. **Lead with the verb or outcome.** "Opened PR <url>" — not "I'd like to inform you that a PR has been opened."
2. **Include the link.** Always. Reviewers and reporters need to click through.
3. **Two sentences max for routine status updates.** Long comments are for substantive discussion only.
4. **No filler.** Cut "just", "wanted to", "quick note that", "FYI", "Hi all".
5. **No emojis** unless the repo customizes this rule.
6. **English** (unless the repo override specifies otherwise).

## Format by purpose

### Status update on a Jira ticket (PR opened, transitioned, blocked, etc.)

```
PR opened: <PR URL>
```

With context if the PR isn't self-explanatory:

```
PR opened: <PR URL>
Targets <branch>. Awaiting review.
```

### Linking a Jira ticket from its GitHub issue

```
Jira: [<TICKET>](<jira URL>)
```

### Linking a GitHub issue from its Jira ticket

```
GitHub issue: <issue URL>
```

### Status comment on a long-running issue

Two short sentences: where things stand, what's next.

```
Implemented the parser; tests passing locally. Next: integrate with the orchestrator and open the PR.
```

### Resolution comment when closing an issue

```
Resolved in <PR URL>.
```

### Blocking / waiting

```
Blocked on <other ticket or person>. Will resume when <unblock condition>.
```

## What to avoid

- **Restating the issue description.** "So as we discussed in this issue, the problem is…" — the issue is right there.
- **Salutations.** "Hi team!" / "Hey all!" — comments don't need them.
- **"Please find attached"** — link directly.
- **Bulleted status reports for routine updates.** Use prose. Reserve bullets for substantive trade-offs or decisions.
- **Multi-paragraph thanks.** "Thanks!" on its own line is fine.
- **Hedging.** "I think maybe" → state it or don't say it.

## Examples

Good:

> PR opened: https://github.com/org/repo/pull/42. Rebased on `version/1.2.0`, 1 approval needed.

Bad:

> Hi team! I wanted to give you all a quick update. I've gone ahead and opened a pull request for this ticket which you can find at the following URL: https://github.com/org/repo/pull/42. It targets the version 1.2.0 branch and is rebased and ready for review whenever you have a chance!

Good:

> Blocked on VN-700 (parent ticket awaiting product sign-off). Will resume once it transitions to In Progress.

Bad:

> Just wanted to send a quick FYI — this ticket is currently blocked because I'm waiting on some product sign-off for the parent ticket (VN-700). As soon as that goes through and the ticket moves to In Progress, I'll pick this back up. Let me know if you have any questions!
