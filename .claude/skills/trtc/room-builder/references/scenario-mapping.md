# Scenario → Template Mapping

> **Internal asset.** Consumed by `topic/SKILL.md` when `ui_mode = full-ui`.
> Users never read this file directly — topic reads it to pick the visual
> reference template for a given onboarding scenario.

## Mapping table

| Onboarding scenario | Path | Scene / template | Reference HTML | Notes |
|---|---|---|---|---|
| `general-meeting` | standard | `meeting` | `uikit/assets/themes/meeting-classic/index.html` | Most generic; gallery + focus modes both supported |
| `online-classroom` | standard | `classroom` | *(TODO: add classroom reference HTML)* | Teacher large tile + student small tiles + raise-hand |
| `telemedicine` | standard | `one-on-one` | *(TODO: add one-on-one reference HTML)* | Defaults to 1v1; multi-party consultation deferred (see pending_todos) |
| `webinar-large` | standard | `meeting` | `uikit/assets/themes/meeting-classic/index.html` | Gallery mode, 9+ participants on screen |

## Fallback

If topic receives a scenario not in this table, it falls back to `ui_mode = null`
behavior for that run (see `topic/SKILL.md` § Step 3.5) and warns the user that
no UI template exists.

## Styled path note

All mappings above point to the Standard path (uikit components, visually
aligned with AtomicXCore). The 12 Styled templates (Tailwind + custom CSS) are
not used for fused code generation in this release — see pending_todos for the
future fusion target.

## Missing reference HTML

Entries marked *(TODO)* need a classroom-specific or 1v1-specific `index.html`
added under `uikit/assets/themes/meeting-classic/` (or a sibling theme). Until
those files exist, topic will hit the fallback above for those scenarios.
