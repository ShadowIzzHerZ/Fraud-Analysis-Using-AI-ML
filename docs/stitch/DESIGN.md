---
name: Warm Civic Minimal
colors:
  surface: '#fbf9f5'
  surface-dim: '#dbdad6'
  surface-bright: '#fbf9f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3ef'
  surface-container: '#efeeea'
  surface-container-high: '#eae8e4'
  surface-container-highest: '#e4e2de'
  on-surface: '#1b1c1a'
  on-surface-variant: '#58423b'
  inverse-surface: '#30312e'
  inverse-on-surface: '#f2f0ed'
  outline: '#8c716a'
  outline-variant: '#dfc0b7'
  surface-tint: '#a83813'
  primary: '#972c06'
  on-primary: '#ffffff'
  primary-container: '#b8431e'
  on-primary-container: '#ffe5de'
  inverse-primary: '#ffb59f'
  secondary: '#5f5e61'
  on-secondary: '#ffffff'
  secondary-container: '#e4e1e6'
  on-secondary-container: '#656467'
  tertiary: '#545249'
  on-tertiary: '#ffffff'
  tertiary-container: '#6d6a61'
  on-tertiary-container: '#f0ebdf'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbd1'
  primary-fixed-dim: '#ffb59f'
  on-primary-fixed: '#3a0a00'
  on-primary-fixed-variant: '#862200'
  secondary-fixed: '#e4e1e6'
  secondary-fixed-dim: '#c8c5ca'
  on-secondary-fixed: '#1b1b1e'
  on-secondary-fixed-variant: '#47464a'
  tertiary-fixed: '#e7e2d7'
  tertiary-fixed-dim: '#cbc6bc'
  on-tertiary-fixed: '#1d1c15'
  on-tertiary-fixed-variant: '#49473f'
  background: '#fbf9f5'
  on-background: '#1b1c1a'
  surface-variant: '#e4e2de'
typography:
  headline-hero:
    fontFamily: Plus Jakarta Sans
    fontSize: 56px
    fontWeight: '800'
    lineHeight: 64px
    letterSpacing: -0.03em
  headline-hero-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 42px
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: '0'
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: '0'
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
  space-2xl: 4rem
---

## Brand & Style

This design system blends warm, human-centered minimalism with the quiet confidence of modern civic utility. It rejects the cold, sterile starkness of standard SaaS in favor of grounding, organic warmth—invoking trust, community accountability, and friction-free direct action. 

The aesthetic is characterized by:
- **Warm Canvas:** Subtly tinted bone/cream grounds that soften visual fatigue while maintaining immaculate contrast.
- **Earthy Direct Action:** A deliberate terracotta/rust brown primary accent that signals human agency, construction, and physical spaces rather than corporate tech.
- **Editorial Utility:** High-density, high-impact grotesque typography paired with generous, deliberate whitespace. Layouts are uncluttered, authoritative, and direct.
- **Tactile Softness:** Pill-shaped key touchpoints balanced against gently rounded structural cards with whisper-soft borders.

## Colors

The palette is tuned for high clarity and warmth under a light-mode default.

- **Primary (`#b8431e`):** Terracotta / Rust. Used for focal call-to-action buttons, key interactive pins, and focal interaction states. Hover states shift subtly darker to `#9e391b`, while active states compress to `#873016`.
- **Secondary (`#18181b`):** Deep carbon black. Anchors primary titles, headers, and essential structural text. Provides unyielding contrast against cream grounds.
- **Tertiary (`#e7e2d7`):** Warm stone. Serves as hairline borders, subtle dividers, badge surfaces, and muted hover states.
- **Neutral Canvas (`#fbf9f5`):** Warm bone off-white. The base background layer for pages and viewports. 
- **Surface Layer (`#ffffff`):** Pure white used exclusively for raised cards, input fields, and elevated panels to separate them softly from the background.
- **Body & Muted Text (`#52525b` & `#71717a`):** Soft neutral charcoals ensuring effortless legibility without harshness.

## Typography

Plus Jakarta Sans governs the entire typographic hierarchy. Its crisp grotesque geometry, rounded aperture stems, and sturdy vertical metrics communicate contemporary efficiency with approachable tactility.

- Headings demand tight tracking (`-0.02em` to `-0.03em`) and substantial weight (`700` to `800`) to present unambiguous statements of fact.
- Body copy is set comfortably at `15px` to `18px` with relaxed line-height (`1.5` to `1.6`) to provide a frictionless reading flow across public disclosures and civic reports.
- Links and inline calls to action reuse label weights (`600`) with terracotta coloring (`#b8431e`), avoiding underlines unless placed in dense prose blocks.

## Layout & Spacing

The layout is built upon an intentional, structured grid with generous vertical pacing.

- **Desktop Layout:** 12-column grid inside a maximum container width of `1200px` (or `1440px` for map viewports). Outer margins sit at `2rem` (`32px`) to preserve breathing space.
- **Mobile Layout:** 4-column fluid grid with `1.25rem` (`20px`) margins and `1rem` (`16px`) gutters. Stacked content flows top-to-bottom with cards spanning full width.
- **Section Rhythm:** Hero and major narrative blocks use `space-2xl` (`4rem`) to `5rem` spacing, letting typographic messaging command the center of the user's field of view without clutter.
- **Component Gap Consistency:** Action clusters (such as button pairings and inline metadata) maintain a strict `space-sm` (`8px`) or `space-md` (`16px`) proximity.

## Elevation & Depth

This design system avoids heavy shadows, artificial skeuomorphic layering, and glossy effects. Elevation is achieved through **tonal separation and soft ambient diffusion**:

- **Ground (Base):** `#fbf9f5` provides the warm baseline plane.
- **Level 1 (Cards & Inputs):** Crisp `#ffffff` elevated purely by color contrast against the `#fbf9f5` field, reinforced by a 1px boundary of `rgba(24, 24, 27, 0.06)` or `#e7e2d7`.
- **Level 2 (Popovers, Dropdowns, Hovered Cards):** `#ffffff` with a warm ambient drop shadow: `0 8px 24px -4px rgba(40, 25, 20, 0.06), 0 2px 6px -2px rgba(40, 25, 20, 0.04)`.
- **Modals & Drawers:** Grounded by a backdrop scrim with soft warmth: `rgba(24, 24, 27, 0.35)` with an optional `blur(3px)`.

## Shapes

The design balances structured containment with fluid interaction:

- **Cards and Containers:** Standardized at `rounded-lg` (`1rem` / `16px`) to `rounded-xl` (`1.5rem` / `24px`). This delivers soft, modern enclosure without appearing cartoonish.
- **Action Elements (Buttons, Chips, Pill Selectors):** Fully rounded pill geometry (`9999px`). The pill shape signals immediate tactile pushability and guides the eye straight to action centers.
- **Inputs & Field Enclosures:** Standard `0.5rem` (`8px`) to `0.75rem` (`12px`) corners to differentiate data entry zones from CTA triggers.
- **Badges and Indicators:** Scaled down with `9999px` capsule radii for status tags and count markers.

## Components

### Buttons
- **Primary Action:** Pill-shaped (`rounded-full`), `#b8431e` background, pure white text (`#ffffff`), `fontWeight: 600`. Padding: `0.75rem 1.75rem` (`12px 28px`). Hover: transitions to `#9e391b`.
- **Secondary Action:** Pill-shaped, pure white `#ffffff` background, `1px` border in `#e7e2d7`, `#18181b` text. Hover: `#f7f5f0` fill and border tinting.
- **Ghost / Link Action:** Zero border, transparent fill, `#b8431e` or `#18181b` text with subtle hover opacity change (`0.8`).

### Input Fields & Controls
- **Text Inputs:** `#ffffff` surface, `1px solid #e7e2d7`, `0.625rem` (`10px`) rounded radius, `0.75rem 1rem` inner padding. Placeholder text uses `#a1a1aa`. Focus ring: `2px solid #b8431e` with a `2px` offset.
- **Checkboxes & Radios:** Native size `18px`, `1.5px solid #d4cfc5`, checked state filled with `#b8431e` displaying a crisp white glyph.
- **Selectors / Dropdowns:** Pill or soft-square enclosing pill indicator with chevron icon, `#ffffff` fill, `#18181b` label text.

### Cards & Surfaces
- **Feature & Report Cards:** `#ffffff` background, `1px solid #ede8de` border, `1.25rem` (`20px`) border radius, `1.5rem` (`24px`) internal padding. Subtle translation on hover: `-2px` with ambient shadow level 2.
- **Hero Containers:** Background matches base canvas `#fbf9f5` or soft white tint, center-aligned typography with pill CTA grouping.

### Chips & Badges
- **Status Pills:** Height `24px` to `28px`, capsule radius (`9999px`), `0.25rem 0.75rem` padding. Warm muted backgrounds (e.g., `#f4ede4` for pending, `#e6f4ea` for resolved) paired with high-contrast text.

### Navigation & Headers
- **Top Bar:** Floating or edge-to-edge transparent-to-frosted `#fbf9f5` background. Houses brand emblem (rounded square with initial), language pill selector, and secondary/primary button group.