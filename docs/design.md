# design

# Design

Visual system for the analyst dashboard. Default theme is **dark operations** (SOC / trading floor), not a consumer fintech pastel app. Light theme is optional (Phase 6).

## Character

- Calm chrome, loud signals. Most of the UI is muted; **risk is the only thing that glows**.
- Dense but not cramped: tabular numbers, short labels, few illustrations.
- Motion is functional: new rows ease in; critical alerts pulse once, not forever.

## Color

### Dark theme (default)

Use CSS variables on `:root` / `.dark`. Do not hardcode random hex in components.

| Token | Hex | Role |
| --- | --- | --- |
| `--bg` | `#0B0F14` | App background |
| `--bg-elevated` | `#121821` | Cards, sidebar, panels |
| `--bg-muted` | `#1A222D` | Table header, input fill |
| `--border` | `#2A3544` | Dividers, card outline |
| `--text` | `#E8EEF6` | Primary text |
| `--text-muted` | `#8B9BB0` | Labels, timestamps |
| `--text-faint` | `#5C6B7F` | Axis ticks, placeholders |
| `--accent` | `#3DDC97` | Safe / allow / live “on air” |
| `--accent-dim` | `#1F6F52` | Accent borders, charts (low) |
| `--info` | `#5B8CFF` | Links, focus ring, “investigating” |
| `--warn` | `#F5C542` | Medium severity |
| `--danger` | `#FF5C5C` | High / freeze / critical |
| `--critical` | `#FF2D55` | Critical only (use sparingly) |
| `--score-track` | `#2A3544` | Risk bar background |

**Risk mapping**

| Severity | Bar / badge | Text on badge |
| --- | --- | --- |
| low | `--accent` | `--bg` |
| medium | `--warn` | `#0B0F14` |
| high | `--danger` | `#FFFFFF` |
| critical | `--critical` | `#FFFFFF` |

**Do not** use red for primary buttons. Primary button = `--info` (Investigate) or `--danger` only for Freeze. Allow/Dismiss = ghost / muted.

**Charts:** series 1 `--info`, series 2 `--accent`, alerts overlay `--danger`. Grid lines `--border` at 40% opacity.

### Light theme (optional)

| Token | Hex |
| --- | --- |
| `--bg` | `#F4F6F9` |
| `--bg-elevated` | `#FFFFFF` |
| `--bg-muted` | `#EEF2F7` |
| `--border` | `#D5DEE8` |
| `--text` | `#0B0F14` |
| `--text-muted` | `#5C6B7F` |
| `--accent` | `#0F9F6E` |
| `--info` | `#2F6FED` |
| `--warn` | `#C48A00` |
| `--danger` | `#D92D20` |

Keep the same token names so components do not branch.

## Surfaces and layout

- **App shell:** left nav 240px (`-bg-elevated`), main canvas `-bg`, 24px page padding.
- **KPI strip:** 4 equal cards, 12px gap, 16px inner padding, hairline `-border`.
- **Feed vs alerts:** home is two columns on ≥1280px (feed 42% / alerts 58%); stack on smaller screens.
- **Radius:** 8px cards, 6px buttons/inputs, 999px pills/badges.
- **Shadow:** none on dark (rely on border + elevation color). Light theme: `0 1px 2px rgba(11,15,20,0.06)`.
- **Max content width:** none on ops views (use the screen); detail drawer 480px.

## Typography

### Fonts

Load from `next/font` (self-hosted Google fonts). No extra display typefaces.

| Role | Family | Weights | Notes |
| --- | --- | --- | --- |
| UI / body | **IBM Plex Sans** | 400, 500, 600 | Analyst chrome, labels, buttons |
| Numbers / IDs / scores | **IBM Plex Mono** | 400, 500 | Amounts, tokens, timestamps, `risk_score` |
| Marketing/hero only | none | — | This is an ops tool; no display serif |

Fallback: `ui-sans-serif, system-ui, sans-serif` and `ui-monospace, monospace`.

If IBM Plex is blocked, substitute **Source Sans 3** + **Source Code Pro** with the same weights — do not mix five families.

### Scale

| Name | Size | Line height | Weight | Use |
| --- | --- | --- | --- | --- |
| `display` | 28px | 1.2 | 600 | Page title only |
| `title` | 18px | 1.3 | 600 | Card / section headers |
| `body` | 14px | 1.5 | 400 | Descriptions, notes |
| `ui` | 13px | 1.4 | 500 | Nav, table cells, buttons |
| `caption` | 11px | 1.4 | 500 | KPI labels, badges, reasons |
| `mono-lg` | 20px | 1.2 | 500 | KPI values, score |
| `mono` | 12px | 1.4 | 400 | IDs, JSON snippets |

Tabular lining figures for all money and KPIs (`font-variant-numeric: tabular-nums`).

**Letter-spacing:** captions +0.04em uppercase KPI labels (`TRACKING`). Body: default.

## Components (visual rules)

- **Live pill:** 8px accent dot, label `LIVE`, caption size, `-accent`.
- **Reason chips:** `-bg-muted` fill, `-border`, caption; detector `code` in mono 11px.
- **Risk bar:** 4px height, rounded, fill by severity; show `0.00–1.00` in mono beside it.
- **Tables:** sticky header `-bg-muted`, row hover `-bg-muted` at 50%, critical row left 3px `-critical` stripe.
- **Focus:** 2px `-info` ring, offset 2px. Never remove outlines without a replacement.
- **Toasts:** one at a time, bottom-right, 4s, for freeze/dismiss confirmation only.

## Iconography

Lucide, 16px in tables, 20px in nav. Stroke 1.75. No emoji in the product UI (simulator attack buttons may use text labels only).

## Imagery

No hero photos, no stock “hacker in a hoodie.” Optional abstract grid in the empty feed state, 8% opacity, `--border`.

## Accessibility

- Contrast: body text on `-bg` must meet WCAG AA.
- Do not convey severity by color alone — include label text (`HIGH`, `CRITICAL`).
- Respect `prefers-reduced-motion`: skip pulse and row insert animation.

## Example tokens (CSS)

```css
:root {
  --font-sans: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, monospace;
  --bg: #0b0f14;
  --bg-elevated: #121821;
  --bg-muted: #1a222d;
  --border: #2a3544;
  --text: #e8eef6;
  --text-muted: #8b9bb0;
  --accent: #3ddc97;
  --info: #5b8cff;
  --warn: #f5c542;
  --danger: #ff5c5c;
  --critical: #ff2d55;
  --radius: 8px;
}
```