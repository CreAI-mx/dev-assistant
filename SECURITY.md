# Security policy

dev-assistant is **alpha** software and has not been hardened or audited. It is intended for local use by individual developers in trusted environments. Do not deploy it to multi-tenant systems, expose it over a network, or run it against repositories whose contents you do not trust.

## Supported versions

Only the latest `0.x` release receives fixes while the project is in alpha. Older `0.x` versions are not maintained.

## Reporting a vulnerability

Please report suspected vulnerabilities **privately** rather than opening a public issue.

Email: **juangonzalez@creai.mx**

Please include:

- A clear description of the issue and its impact.
- Steps to reproduce or a minimal proof of concept.
- The dev-assistant version (`dev-assistant --version` if available, otherwise the commit SHA).
- Your environment (OS, Python version).

While the project is in alpha, response times are best-effort. Expect an acknowledgement within a few business days. There is no formal bug-bounty program.

## Out of scope

- Issues that require local write access to the user's machine (this is a local developer tool by design).
- Behavior of third-party services the CLI calls into (Jira, GitHub) — report those to the respective vendors.
- Issues in slash commands' generated content (these are AI-generated and reviewed by the user before commit).
