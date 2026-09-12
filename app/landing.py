"""Public marketing landing page — what a signed-out visitor sees at "/"
instead of being bounced straight to /login. Desktop-focused by request
(no phone breakpoints here); the actual console is still gated behind auth
in app/ui_dashboard.py's dashboard_page(), which calls render_landing_page()
when there's no session instead of navigating away.

Animation stack: anime.js (timeline reveals, the pulse/radar loop, the
count-up stats, scroll-triggered stagger-ins) plus Typed.js for the
rotating headline of things Zen catches. Both loaded from cdnjs; nothing
here needs a build step since this whole app already runs on Tailwind's
Play CDN the same way.
"""
from __future__ import annotations

from nicegui import ui

from app.ui_dashboard import C, bd, bg, icon, raw_html, tx

FEATURES = [
    ("stream", "Live Ingestion Stream",
     "Every transaction lands on the console the instant it happens — no batch "
     "windows, no overnight reconciliation. Watch the feed the way an analyst "
     "actually works."),
    ("diamond", "Four Live Detectors",
     "Velocity spikes, amount outliers, impossible travel, mule-burst patterns — "
     "each transaction is scored against all four the moment it arrives."),
    ("lock_clock", "Auto-Freeze Policies",
     "Set a risk threshold once. Cards that cross it get frozen automatically, "
     "before the next transaction can clear — no analyst has to be watching."),
    ("receipt_long", "Audit-Ready Trail",
     "Every score, freeze, and override is timestamped and exportable, so a "
     "decision made at 3am survives being questioned at a quarterly review."),
]

STEPS = [
    ("cable", "Connect your stream",
     "Point Zen at your transaction feed. Everything else in the console reacts to "
     "it live — no polling, no delay."),
    ("tune", "Set your policies",
     "Pick an auto-freeze threshold and let the four detectors run underneath it. "
     "Tune it from the Policies screen any time."),
    ("verified_user", "Freeze automatically",
     "Compromised cards get stopped before the damage compounds, and every "
     "decision lands in the audit log on its own."),
]

STATS = [
    ("2.4", "Cr+", "Prevented in this simulation", 1),
    ("40", "ms", "Avg. decision latency", 0),
    ("99.7", "%", "Detector precision (demo)", 1),
    ("24", "/7", "Autonomous monitoring", 0),
]


def render_landing_page() -> None:
    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">'
        '<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">'
        f'<link rel="stylesheet" href="/static/theme.css">'
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/animejs/3.2.1/anime.min.js"></script>'
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/typed.js/2.0.16/typed.umd.js"></script>'
        '<style>'
        'body,.font-sans{font-family:"Plus Jakarta Sans",ui-sans-serif,sans-serif}'
        + LANDING_CSS +
        '</style>'
    )
    ui.page_title("Zen — Fraud Ops, Built for Speed")

    with ui.element("div").classes("landing-root w-full max-w-[100vw] overflow-x-hidden"):
        _nav()
        _hero()
        _logos_strip()
        _stats()
        _features()
        _how_it_works()
        _cta_banner()
        _footer()

    ui.add_body_html(f'<script>{LANDING_JS}</script>')


def _nav() -> None:
    raw_html(
        '<nav class="landing-nav">'
        '<div class="landing-nav-inner">'
        f'<a href="/" class="landing-logo"><span class="landing-logo-badge">Z</span>'
        '<span class="landing-logo-text">Zen</span></a>'
        '<div class="landing-nav-links">'
        '<a href="#features">Product</a>'
        '<a href="#how-it-works" id="how-it-works-link">How it works</a>'
        '<a href="#stats">Results</a>'
        '</div>'
        '<div class="landing-nav-cta">'
        '<a href="/login" class="landing-link-btn">Log in</a>'
        '<a href="/signup" class="landing-primary-btn landing-primary-btn-sm">Get Started</a>'
        '</div>'
        '</div>'
        '</nav>'
    )


def _hero() -> None:
    raw_html(
        '<section class="landing-hero">'
        '<div class="landing-hero-copy">'
        '<div class="landing-badge"><span class="landing-badge-dot"></span>AI/ML Fraud Detection · Real-Time</div>'
        '<h1 class="landing-h1">'
        '<span class="hero-word">Fraud</span> <span class="hero-word">caught</span> '
        '<span class="hero-word">in</span> <span class="hero-word">milliseconds,</span><br>'
        '<span class="hero-word landing-accent">not</span> <span class="hero-word landing-accent">months.</span>'
        '</h1>'
        '<p class="landing-sub hero-sub">Zen watches every transaction live and '
        '<span id="typed-target" class="landing-typed"></span></p>'
        '<div class="landing-hero-cta hero-cta">'
        '<a href="/signup" class="landing-primary-btn">Get Started Free'
        f'{icon("arrow_forward", "text-[18px]")}</a>'
        '<a href="#how-it-works" class="landing-ghost-btn">'
        f'{icon("play_circle", "text-[18px]")}Watch how it works</a>'
        '</div>'
        '<p class="landing-hero-note">No credit card. This is a simulation environment — no real funds ever move.</p>'
        '</div>'
        '<div class="landing-hero-visual hero-visual">'
        '<div class="radar-ring radar-ring-1 pulse-ring"></div>'
        '<div class="radar-ring radar-ring-2 pulse-ring"></div>'
        '<div class="radar-ring radar-ring-3 pulse-ring"></div>'
        f'<div class="radar-core">{icon("shield", "text-[34px]")}</div>'
        '<div class="radar-orbit radar-orbit-1"><div class="radar-dot radar-dot-safe"></div></div>'
        '<div class="radar-orbit radar-orbit-2"><div class="radar-dot radar-dot-watch"></div></div>'
        '<div class="radar-orbit radar-orbit-3"><div class="radar-dot radar-dot-stop"></div></div>'
        '<div class="radar-chip radar-chip-1">'
        f'{icon("bolt", "text-[14px]")}<span>Velocity spike flagged</span></div>'
        '<div class="radar-chip radar-chip-2">'
        f'{icon("lock_clock", "text-[14px]")}<span>Card frozen · 41ms</span></div>'
        '</div>'
        '</section>'
    )


def _logos_strip() -> None:
    raw_html(
        '<div class="landing-strip">'
        '<span class="landing-strip-label">Built on the same detectors running the live console</span>'
        '<div class="landing-strip-chips">'
        + "".join(
            f'<span class="landing-strip-chip">{icon(ic, "text-[15px]")}{label}</span>'
            for ic, label in [
                ("bolt", "Velocity"), ("diamond", "Amount Outlier"),
                ("flight", "Impossible Travel"), ("hub", "Mule Burst"),
            ]
        )
        + '</div></div>'
    )


def _stats() -> None:
    with ui.element("section").props('id="stats"').classes("landing-stats"):
        raw_html(
            '<div class="landing-stats-grid">'
            + "".join(
                f'<div class="landing-stat-card">'
                f'<div class="landing-stat-num stat-num" data-target="{val}" data-suffix="{suf}" data-round="{rnd}">0{suf}</div>'
                f'<div class="landing-stat-label">{label}</div></div>'
                for val, suf, label, rnd in STATS
            )
            + "</div>"
        )


def _features() -> None:
    with ui.element("section").props('id="features"').classes("landing-features"):
        raw_html(
            '<div class="landing-section-head">'
            '<div class="landing-eyebrow">Product</div>'
            '<h2 class="landing-h2">Built for fraud ops teams, not spreadsheets.</h2>'
            '<p class="landing-section-sub">Everything in Zen exists to shorten the gap between '
            '"something looks wrong" and "it\'s already handled."</p>'
            '</div>'
            '<div class="landing-features-grid">'
            + "".join(
                f'<div class="landing-feature-card feature-card">'
                f'<div class="landing-feature-icon">{icon(ic, "text-[22px]")}</div>'
                f'<h3>{title}</h3><p>{desc}</p></div>'
                for ic, title, desc in FEATURES
            )
            + "</div>"
        )


def _how_it_works() -> None:
    with ui.element("section").props('id="how-it-works"').classes("landing-how"):
        raw_html(
            '<div class="landing-section-head">'
            '<div class="landing-eyebrow">How it works</div>'
            '<h2 class="landing-h2">Three steps. No integration marathon.</h2>'
            '</div>'
            '<div class="landing-steps">'
            '<div class="landing-steps-line"><div class="landing-steps-line-fill progress-line-fill"></div></div>'
            + "".join(
                f'<div class="landing-step step-card">'
                f'<div class="landing-step-num">{i + 1}</div>'
                f'<div class="landing-step-icon">{icon(ic, "text-[24px]")}</div>'
                f'<h3>{title}</h3><p>{desc}</p></div>'
                for i, (ic, title, desc) in enumerate(STEPS)
            )
            + "</div>"
        )


def _cta_banner() -> None:
    raw_html(
        '<section class="landing-cta-banner">'
        '<h2>Ready to see it catch something?</h2>'
        '<p>Spin up an analyst account and inject a fraud scenario in under a minute.</p>'
        '<div class="landing-hero-cta">'
        f'<a href="/signup" class="landing-primary-btn landing-primary-btn-light">Create free account{icon("arrow_forward", "text-[18px]")}</a>'
        '<a href="/login" class="landing-ghost-btn landing-ghost-btn-light">Log in</a>'
        '</div>'
        '</section>'
    )


def _footer() -> None:
    raw_html(
        '<footer class="landing-footer">'
        '<div class="landing-footer-inner">'
        '<div class="landing-logo"><span class="landing-logo-badge">Z</span><span class="landing-logo-text">Zen</span></div>'
        '<p>© 2026 Zen. A simulation environment built for demonstration — no real funds ever move.</p>'
        '</div>'
        '</footer>'
    )


LANDING_CSS = f"""
*, *::before, *::after {{
  box-sizing: border-box;
}}

html, body {{
  width: 100% !important;
  max-width: 100vw !important;
  overflow-x: hidden !important;
}}

.nicegui-content {{
  width: 100% !important;
  max-width: 100vw !important;
  align-items: stretch !important;
  overflow-x: hidden !important;
}}

.landing-root {{
  background:{C["background"]};
  color:{C["on_surface"]};
  width: 100% !important;
  max-width: 100vw !important;
  height: 100vh;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  display: flex;
  flex-direction: column;
}}
.landing-root a {{ text-decoration:none; color:inherit; }}
html {{ scroll-behavior:smooth; }}

/* -- nav -- */
.landing-nav {{
  position:sticky; top:0; z-index:50; width:100%;
  background:{C["background"]}cc; backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
  border-bottom:1px solid transparent; transition:border-color .2s ease, box-shadow .2s ease;
  flex-shrink: 0;
}}
.landing-nav.scrolled {{ border-bottom-color:{C["outline_variant"]}; box-shadow:0 2px 16px rgba(0,0,0,.04); }}
.landing-nav-inner {{
  max-width:1180px; width:100%; margin:0 auto; padding:14px 32px; display:flex; align-items:center; gap:32px;
}}
.landing-nav-links {{ display:flex; gap:28px; margin-right:auto; margin-left:48px; font-size:14px; font-weight:600; color:{C["muted_dark"]}; }}
.landing-nav-links a:hover {{ color:{C["primary"]}; }}
.landing-nav-cta {{ display:flex; align-items:center; gap:18px; margin-left: auto; }}
.landing-link-btn {{ font-size:14px; font-weight:700; color:{C["on_surface"]}; }}
.landing-link-btn:hover {{ color:{C["primary"]}; }}

.landing-logo {{ display:flex; align-items:center; gap:10px; flex-shrink: 0; }}
.landing-logo-badge {{
  width:32px; height:32px; border-radius:10px; background:{C["primary"]}; color:#fff;
  display:flex; align-items:center; justify-content:center; font-weight:800; font-size:14px; box-shadow:0 2px 6px rgba(184,67,30,.25);
  flex-shrink: 0;
}}
.landing-logo-text {{ font-weight:800; font-size:17px; letter-spacing:-0.01em; }}

/* -- buttons -- */
.landing-primary-btn {{
  display:inline-flex; align-items:center; gap:8px; background:{C["primary"]}; color:#fff !important;
  font-weight:700; font-size:15px; padding:13px 24px; border-radius:999px; box-shadow:0 6px 16px rgba(184,67,30,.28);
  transition:transform .15s ease, box-shadow .15s ease, background .15s ease;
}}
.landing-primary-btn:hover {{ background:{C["primary_hover"]}; transform:translateY(-2px); box-shadow:0 10px 22px rgba(184,67,30,.35); }}
.landing-primary-btn:active {{ transform:translateY(0) scale(.98); }}
.landing-primary-btn-sm {{ padding:9px 18px; font-size:13.5px; box-shadow:none; }}
.landing-primary-btn-light {{ background:#fff; color:{C["primary"]} !important; box-shadow:0 6px 16px rgba(0,0,0,.15); }}
.landing-primary-btn-light:hover {{ background:#fff; opacity:.92; }}

.landing-ghost-btn {{
  display:inline-flex; align-items:center; gap:8px; background:{C["surface_lowest"]}; color:{C["on_surface"]} !important;
  font-weight:700; font-size:15px; padding:13px 22px; border-radius:999px; border:1px solid {C["outline_variant"]};
  transition:transform .15s ease, border-color .15s ease, background .15s ease;
}}
.landing-ghost-btn:hover {{ border-color:{C["primary"]}; transform:translateY(-2px); }}
.landing-ghost-btn-light {{ background:transparent; color:#fff !important; border-color:rgba(255,255,255,.4); }}
.landing-ghost-btn-light:hover {{ border-color:#fff; }}

/* -- badge -- */
.landing-badge {{
  display:inline-flex; align-items:center; gap:8px; background:{C["surface_low"]}; border:1px solid {C["outline_variant"]};
  color:{C["muted_dark"]}; font-size:12.5px; font-weight:700; letter-spacing:.02em; padding:7px 14px; border-radius:999px; margin-bottom:22px;
}}
.landing-badge-dot {{ width:7px; height:7px; border-radius:999px; background:#16a34a; box-shadow:0 0 0 3px rgba(22,163,74,.18); }}

/* -- hero -- */
.landing-hero {{
  max-width:1180px; width:100%; margin:0 auto; padding:56px 32px 100px; display:grid; grid-template-columns:1.05fr .95fr;
  gap:56px; align-items:center; min-height:560px;
}}
.landing-hero-copy {{ min-width: 0; }}
.landing-h1 {{
  font-size:53px; line-height:1.08; font-weight:800; letter-spacing:-0.02em; margin:0 0 22px;
  word-break: break-word; overflow-wrap: break-word;
}}
.hero-word {{ display:inline-block; }}
.landing-accent {{ color:{C["primary"]}; }}
.landing-sub {{ font-size:18px; line-height:1.55; color:{C["muted_dark"]}; max-width:520px; margin:0 0 34px; min-height:56px; }}
.landing-typed {{ color:{C["primary"]}; font-weight:700; }}
.landing-hero-cta {{ display:flex; align-items:center; gap:16px; flex-wrap:wrap; }}
.landing-hero-note {{ margin-top:18px; font-size:12.5px; color:{C["muted"]}; }}

/* -- hero radar visual -- */
.landing-hero-visual {{
  position:relative; height:460px; display:flex; align-items:center; justify-content:center;
  max-width: 100%; overflow: hidden;
}}
.radar-ring {{
  position:absolute; border-radius:999px; border:1.5px solid {C["primary"]}; opacity:0;
}}
.radar-ring-1 {{ width:140px; height:140px; }}
.radar-ring-2 {{ width:220px; height:220px; }}
.radar-ring-3 {{ width:300px; height:300px; }}
.radar-core {{
  position:relative; z-index:2; width:96px; height:96px; border-radius:999px; background:{C["primary"]}; color:#fff;
  display:flex; align-items:center; justify-content:center; box-shadow:0 10px 30px rgba(184,67,30,.35);
}}
.radar-orbit {{
  position:absolute; border-radius:999px; border:1px dashed {C["outline_variant"]};
  display:flex; align-items:center; justify-content:center;
}}
.radar-orbit-1 {{ width:220px; height:220px; animation:orbit-spin 9s linear infinite; }}
.radar-orbit-2 {{ width:300px; height:300px; animation:orbit-spin 14s linear infinite reverse; }}
.radar-orbit-3 {{ width:380px; height:380px; animation:orbit-spin 20s linear infinite; }}
.radar-dot {{ width:14px; height:14px; border-radius:999px; margin-top:-6px; box-shadow:0 2px 6px rgba(0,0,0,.15); }}
.radar-dot-safe {{ background:#16a34a; }}
.radar-dot-watch {{ background:#d97706; }}
.radar-dot-stop {{ background:{C["primary"]}; }}
@keyframes orbit-spin {{ from {{ transform:rotate(0deg); }} to {{ transform:rotate(360deg); }} }}
.radar-orbit > .radar-dot {{ animation:counter-spin inherit; }}
.radar-orbit-1 > .radar-dot {{ animation:counter-spin 9s linear infinite; }}
.radar-orbit-2 > .radar-dot {{ animation:counter-spin 14s linear infinite reverse; }}
.radar-orbit-3 > .radar-dot {{ animation:counter-spin 20s linear infinite; }}
@keyframes counter-spin {{ from {{ transform:rotate(0deg); }} to {{ transform:rotate(-360deg); }} }}

.radar-chip {{
  position:absolute; display:flex; align-items:center; gap:7px; background:{C["surface_lowest"]};
  border:1px solid {C["outline_variant"]}; box-shadow:0 8px 20px rgba(0,0,0,.08); border-radius:999px;
  padding:8px 14px; font-size:12px; font-weight:700; color:{C["on_surface"]}; opacity:0;
}}
.radar-chip-1 {{ top:18px; right:0; }}
.radar-chip-2 {{ bottom:30px; left:-10px; }}

/* -- logo/detector strip -- */
.landing-strip {{
  width: 100%; border-top:1px solid {C["outline_variant"]}; border-bottom:1px solid {C["outline_variant"]}; padding:26px 32px;
}}
.landing-strip-label {{ display:block; text-align:center; font-size:12px; font-weight:700; letter-spacing:.06em;
  text-transform:uppercase; color:{C["muted"]}; margin-bottom:16px; }}
.landing-strip-chips {{ display:flex; justify-content:center; gap:14px; flex-wrap:wrap; }}
.landing-strip-chip {{
  display:inline-flex; align-items:center; gap:7px; background:{C["surface_low"]}; border:1px solid {C["outline_variant"]};
  border-radius:999px; padding:8px 16px; font-size:13px; font-weight:600; color:{C["muted_dark"]};
}}

/* -- stats -- */
.landing-stats {{ max-width:1180px; width:100%; margin:0 auto; padding:72px 32px; }}
.landing-stats-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:24px; }}
.landing-stat-card {{
  background:{C["surface_lowest"]}; border:1px solid {C["outline_variant"]}; border-radius:20px; padding:28px 20px; text-align:center;
}}
.landing-stat-num {{ font-size:38px; font-weight:800; color:{C["primary"]}; letter-spacing:-0.01em; font-variant-numeric:tabular-nums; }}
.landing-stat-label {{ margin-top:8px; font-size:13.5px; color:{C["muted_dark"]}; font-weight:600; }}

/* -- section headers -- */
.landing-section-head {{ max-width:640px; margin:0 auto 48px; text-align:center; }}
.landing-eyebrow {{ font-size:12.5px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:{C["primary"]}; margin-bottom:10px; }}
.landing-h2 {{ font-size:34px; font-weight:800; letter-spacing:-0.01em; margin:0 0 12px; line-height:1.2; }}
.landing-section-sub {{ font-size:16px; color:{C["muted_dark"]}; line-height:1.6; }}

/* -- features -- */
.landing-features {{ max-width:1180px; width:100%; margin:0 auto; padding:88px 32px; }}
.landing-features-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:22px; }}
.landing-feature-card {{
  background:{C["surface_lowest"]}; border:1px solid {C["outline_variant"]}; border-radius:20px; padding:26px 22px;
  transition:border-color .2s ease, transform .2s ease, box-shadow .2s ease;
}}
.landing-feature-card:hover {{ border-color:{C["primary"]}; transform:translateY(-4px); box-shadow:0 14px 30px rgba(0,0,0,.06); }}
.landing-feature-icon {{
  width:46px; height:46px; border-radius:13px; background:{C["primary_container"]}; color:{C["primary"]};
  display:flex; align-items:center; justify-content:center; margin-bottom:16px;
}}
.landing-feature-card h3 {{ font-size:16.5px; font-weight:800; margin:0 0 8px; }}
.landing-feature-card p {{ font-size:13.5px; line-height:1.6; color:{C["muted_dark"]}; margin:0; }}

/* -- how it works -- */
.landing-how {{ max-width:1180px; width:100%; margin:0 auto; padding:0 32px 96px; }}
.landing-steps {{ position:relative; display:grid; grid-template-columns:repeat(3,1fr); gap:32px; }}
.landing-steps-line {{
  position:absolute; top:23px; left:calc(100%/6); right:calc(100%/6); height:2px; background:{C["outline_variant"]}; z-index:0;
}}
.landing-steps-line-fill {{ height:100%; width:0%; background:{C["primary"]}; }}
.landing-step {{ position:relative; z-index:1; background:{C["background"]}; text-align:center; padding-top:0; }}
.landing-step-num {{
  width:46px; height:46px; border-radius:999px; background:{C["primary"]}; color:#fff; font-weight:800; font-size:16px;
  display:flex; align-items:center; justify-content:center; margin:0 auto 16px; box-shadow:0 6px 16px rgba(184,67,30,.3);
}}
.landing-step-icon {{ color:{C["primary"]}; margin-bottom:10px; }}
.landing-step h3 {{ font-size:16.5px; font-weight:800; margin:0 0 8px; }}
.landing-step p {{ font-size:13.5px; line-height:1.6; color:{C["muted_dark"]}; max-width:280px; margin:0 auto; }}

/* -- cta banner -- */
.landing-cta-banner {{
  max-width:1180px; width: calc(100% - 64px); margin:0 auto 96px; background:{C["primary"]}; color:#fff;
  border-radius:28px; padding:64px 40px; text-align:center;
}}
.landing-cta-banner h2 {{ font-size:30px; font-weight:800; margin:0 0 10px; }}
.landing-cta-banner p {{ font-size:15.5px; opacity:.9; margin:0 0 28px; }}
.landing-cta-banner .landing-hero-cta {{ justify-content:center; }}

/* -- footer -- */
.landing-footer {{ width: 100%; border-top:1px solid {C["outline_variant"]}; padding:32px; margin-top: auto; }}
.landing-footer-inner {{ max-width:1180px; width:100%; margin:0 auto; display:flex; align-items:center; gap:16px; }}
.landing-footer-inner p {{ font-size:12.5px; color:{C["muted"]}; margin:0; }}

@media (max-width:960px) {{
  .landing-nav-links {{ display:none; }}
  .landing-hero {{ grid-template-columns:1fr; padding-top:32px; gap: 36px; }}
  .landing-hero-visual {{ height:320px; order:-1; transform: scale(0.9); transform-origin: center center; }}
  .landing-h1 {{ font-size:38px; }}
  .landing-stats-grid, .landing-features-grid {{ grid-template-columns:repeat(2,1fr); }}
  .landing-steps {{ grid-template-columns:1fr; }}
  .landing-steps-line {{ display:none; }}
}}

@media (max-width:640px) {{
  .landing-nav-inner {{ padding: 12px 16px; gap: 12px; }}
  .landing-nav-cta {{ gap: 10px; }}
  .landing-primary-btn-sm {{ padding: 8px 14px; font-size: 12.5px; }}
  .landing-link-btn {{ font-size: 13px; }}

  .landing-hero {{ padding: 24px 16px 48px; gap: 28px; min-height: auto; }}
  .landing-h1 {{ font-size: 30px; margin-bottom: 16px; }}
  .landing-sub {{ font-size: 15px; margin-bottom: 24px; min-height: auto; }}
  .landing-hero-cta {{ gap: 10px; }}
  .landing-primary-btn, .landing-ghost-btn {{ padding: 11px 18px; font-size: 13.5px; }}
  .landing-hero-visual {{ height: 260px; transform: scale(0.78); transform-origin: center center; }}

  .landing-strip {{ padding: 18px 16px; }}
  .landing-strip-chips {{ gap: 8px; }}
  .landing-strip-chip {{ padding: 6px 12px; font-size: 12px; }}

  .landing-stats {{ padding: 40px 16px; }}
  .landing-stats-grid {{ gap: 12px; }}
  .landing-stat-card {{ padding: 18px 12px; }}
  .landing-stat-num {{ font-size: 28px; }}

  .landing-features {{ padding: 48px 16px; }}
  .landing-features-grid {{ grid-template-columns: 1fr; gap: 14px; }}
  .landing-h2 {{ font-size: 24px; }}
  .landing-section-head {{ margin-bottom: 32px; }}

  .landing-how {{ padding: 0 16px 56px; }}

  .landing-cta-banner {{
    width: calc(100% - 32px);
    margin: 0 auto 56px;
    padding: 36px 18px;
    border-radius: 20px;
  }}
  .landing-cta-banner h2 {{ font-size: 22px; }}
  .landing-cta-banner p {{ font-size: 14px; margin-bottom: 20px; }}

  .landing-footer {{ padding: 24px 16px; }}
  .landing-footer-inner {{ flex-direction: column; text-align: center; gap: 8px; }}
}}

@media (max-width:400px) {{
  .landing-hero-visual {{ height: 220px; transform: scale(0.68); }}
  .landing-stats-grid {{ grid-template-columns: 1fr; }}
  .landing-h1 {{ font-size: 26px; }}
}}
"""

LANDING_JS = """
(function() {
  document.addEventListener('DOMContentLoaded', function() {
    if (typeof anime === 'undefined') return;

    anime.timeline({ easing: 'easeOutExpo' })
      .add({ targets: '.hero-word', translateY: [36, 0], opacity: [0, 1], duration: 800, delay: anime.stagger(70) })
      .add({ targets: '.hero-sub, .hero-cta, .landing-hero-note', translateY: [18, 0], opacity: [0, 1], duration: 650, delay: anime.stagger(100) }, '-=500')
      .add({ targets: '.landing-hero-visual', opacity: [0, 1], scale: [0.9, 1], duration: 800 }, '-=650')
      .add({ targets: '.radar-chip', opacity: [0, 1], translateY: [10, 0], duration: 500, delay: anime.stagger(200) }, '-=300');

    anime({
      targets: '.pulse-ring', scale: [0.55, 1.7], opacity: [0.55, 0],
      easing: 'easeOutSine', duration: 2400, loop: true, delay: anime.stagger(700),
    });

    if (typeof Typed !== 'undefined' && document.getElementById('typed-target')) {
      new Typed('#typed-target', {
        strings: [
          'stops velocity spikes.', 'flags impossible travel.',
          'freezes compromised cards.', 'catches amount outliers.', 'spots mule-burst rings.',
        ],
        typeSpeed: 38, backSpeed: 22, backDelay: 1400, loop: true, smartBackspace: true,
      });
    }

    var statObserver = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (!entry.isIntersecting || entry.target.dataset.animated) return;
        entry.target.dataset.animated = '1';
        var target = parseFloat(entry.target.dataset.target);
        var round = entry.target.dataset.round === '1';
        var suffix = entry.target.dataset.suffix || '';
        var obj = { val: 0 };
        anime({
          targets: obj, val: target, duration: 1700, easing: 'easeOutExpo',
          update: function() {
            var v = round ? obj.val.toFixed(1) : Math.round(obj.val);
            entry.target.textContent = v + suffix;
          },
        });
      });
    }, { threshold: 0.4 });
    document.querySelectorAll('.stat-num').forEach(function(el) { statObserver.observe(el); });

    var revealObserver = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry, i) {
        if (!entry.isIntersecting) return;
        anime({
          targets: entry.target, translateY: [28, 0], opacity: [0, 1],
          duration: 650, easing: 'easeOutCubic', delay: i * 70,
        });
        revealObserver.unobserve(entry.target);
      });
    }, { threshold: 0.2 });
    document.querySelectorAll('.feature-card, .step-card').forEach(function(el) {
      el.style.opacity = '0';
      revealObserver.observe(el);
    });

    var lineObserver = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (!entry.isIntersecting) return;
        anime({ targets: '.progress-line-fill', width: ['0%', '100%'], duration: 1400, easing: 'easeInOutQuad' });
        lineObserver.disconnect();
      });
    }, { threshold: 0.3 });
    var stepsEl = document.querySelector('.landing-steps');
    if (stepsEl) lineObserver.observe(stepsEl);

    var nav = document.querySelector('.landing-nav');
    if (nav) {
      window.addEventListener('scroll', function() {
        nav.classList.toggle('scrolled', window.scrollY > 12);
      });
    }
  });
})();
"""
