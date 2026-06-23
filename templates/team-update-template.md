# Team update template (default)

The default shape for the message you copy-paste into your team's chat (Slack / Discord / Teams) when a PR is marked Ready for review via `/dev-execute` wrap-up. Default language is **Spanish**. Override per-repo by running `dev-assistant strategies customize team-update-template`.

Generated at sub-phase 4 of `/dev-execute`, after the PR is marked Ready (the draft PR itself opened at execute start). Shown in chat for easy copy and saved to `execution/team-message.txt` for the record.

## Format (Spanish, default)

```
PR listo para [<TICKET>] <título imperativo>: <PR URL>

Cambios principales:
- <bullet 1: qué cambió, derivado de los commits>
- <bullet 2>
- <bullet 3 si aplica>

Targeting: develop. Cualquier feedback bienvenido.
```

Three sections, in order:

1. **Lead line:** PR title with ticket prefix + URL. Make it clickable.
2. **Cambios principales:** 2–3 bullets drawn from the subtask titles and commit messages. Describe outcomes, not mechanics.
3. **Cierre:** target branch (`develop`) + open invitation for feedback. Keep it short.

## Style notes

- **Conversacional pero directo.** Sin salutaciones largas ("Hola equipo!"). Sin despedidas formales.
- **Sin emojis** por default. Si el repo los usa, personalizar el override.
- **Sin "porfa" ni "graciás".** El mensaje es informativo, no una petición.
- **Two to three bullets max** — más de eso es señal de que el PR cubre demasiado.
- **Idioma del repo manda.** Default es español; repos angloparlantes deben sobreescribir con un template en inglés.

## Examples

Good:

> PR listo para [VN-742] Add OAuth2 flow for SSO users: https://github.com/org/repo/pull/42
>
> Cambios principales:
> - Provider OAuth nuevo, registrado vía entry points
> - Callback handler en el auth router
> - Tests unitarios cubriendo el flujo completo
>
> Targeting: develop. Cualquier feedback bienvenido.

Bad:

> Hola equipo! 👋 Quería compartirles que acabo de subir un nuevo PR muy importante que resuelve el ticket VN-742. Este PR es bastante grande y robusto, e implementa un montón de cosas relacionadas con OAuth. Por favor revisen cuando puedan y déjenme sus comentarios. ¡Gracias!

The bad version: filler greeting, hedging ("muy importante"), no link visible up front, marketing language ("robusto"), trailing thanks. Strip all of that.

## What to avoid

- **Restating the PR description.** Reviewers will read the PR; the team message just points them there.
- **Marketing adjectives** ("robusto", "potente", "completo", "ambicioso").
- **Apologetic framing** ("Sé que está largo, pero..."). State the scope and trust the team to assess it.
- **Asking specific reviewers in the chat message** — assign them on the PR itself. The chat message is broadcast, not @-ping.
- **Listing every commit.** The bullets describe outcomes, not the commit log.

## When this default doesn't fit

Customize the per-repo override for:

- Teams that work in English (rewrite in English, same structure)
- Teams that require a specific format (e.g., includes ticket ID, links to Confluence, mentions sprint)
- Teams that prefer emojis or markdown formatting native to their chat platform
- Repos where this message gets posted automatically (in v1, you copy-paste — but a future integration could send it directly)
