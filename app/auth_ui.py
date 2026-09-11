"""Login / sign-up screen for Zen analysts, backed by Supabase Auth (app/auth.py).

Pattern (card + pill tabs + shake-on-error) carried over from the sign-up
flow built for an earlier civic-issue-reporting app, re-themed to Zen's own
"Warm Civic Minimal" palette instead of that app's navy/orange one.
"""
from __future__ import annotations

from nicegui import app, run, ui

from app.auth import SESSION_KEY, AuthError, sign_in, sign_up
from app.ui_dashboard import C, bd, bg, icon, raw_html, tx

TAGLINE = {
    "login": "Sign in to the fraud operations console.",
    "signup": "Create your analyst account.",
}


def _shake(el) -> None:
    el.classes(add="auth-shake")
    ui.timer(0.45, lambda: el.classes(remove="auth-shake"), once=True)


def render_auth_card(mode: str) -> None:
    is_signup = mode == "signup"

    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">'
        '<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">'
        '<link rel="stylesheet" href="/static/theme.css">'
        '<style>body,.font-sans{font-family:"Plus Jakarta Sans",ui-sans-serif,sans-serif}</style>'
    )
    ui.page_title(("Sign Up" if is_signup else "Log In") + " — Zen")

    with ui.element("div").classes(
        f'min-h-screen w-full flex items-center justify-center p-4 {bg("background")} auth-stripes'
    ):
        with ui.element("div").classes(
            f'w-full max-w-[400px] {bg("surface_lowest")} border {bd("outline_variant")} '
            f'rounded-2xl shadow-lg p-8'
        ) as card:
            raw_html(
                f'<a href="/" class="flex items-center gap-2.5 mb-1">'
                f'<div class="w-8 h-8 rounded-xl {bg("primary")} text-white flex items-center justify-center font-bold text-sm shadow-sm">Z</div>'
                f'<span class="text-[16px] font-bold tracking-tight {tx("on_surface")}">Zen</span></a>'
            )
            raw_html(f'<p class="text-[13px] {tx("muted")} mb-6">{TAGLINE[mode]}</p>')

            raw_html(
                f'<div class="flex border {bd("outline_variant")} rounded-full overflow-hidden mb-6 text-[12px] font-bold">'
                f'<a href="/login" class="flex-1 text-center py-2 transition-colors '
                + (f'{bg("primary")} text-white' if not is_signup else f'{bg("surface_low")} {tx("muted_dark")} hover:{bg("surface_container")}')
                + '">Log In</a>'
                f'<a href="/signup" class="flex-1 text-center py-2 transition-colors '
                + (f'{bg("primary")} text-white' if is_signup else f'{bg("surface_low")} {tx("muted_dark")} hover:{bg("surface_container")}')
                + '">Sign Up</a></div>'
            )

            name_input = None
            if is_signup:
                raw_html(f'<label class="block text-[11px] font-bold {tx("muted_dark")} mb-1">Display name</label>')
                name_input = ui.input(placeholder="e.g. Priya Sharma") \
                    .props('dense outlined color="#b8431e"').classes("w-full mb-3 text-[13px]")

            raw_html(f'<label class="block text-[11px] font-bold {tx("muted_dark")} mb-1">Email</label>')
            email_input = ui.input(placeholder="you@example.com") \
                .props('dense outlined color="#b8431e"').classes("w-full mb-3 text-[13px]")

            raw_html(f'<label class="block text-[11px] font-bold {tx("muted_dark")} mb-1">Password</label>')
            password_input = ui.input(placeholder="••••••••", password=True, password_toggle_button=True) \
                .props('dense outlined color="#b8431e"').classes("w-full text-[13px]")
            raw_html(
                f'<p class="text-[11px] {tx("muted")} mt-1.5 mb-4">'
                + ("At least 6 characters. This account only accesses Zen — not any other app on this org."
                   if is_signup else "Analyst accounts only.")
                + '</p>'
            )

            submit_btn = ui.button(
                "Sign Up" if is_signup else "Log In",
            ).props("unelevated").classes(
                f'w-full py-2.5 rounded-full font-semibold text-[13px] text-white {bg("primary")} '
                f'hover:{bg("primary_hover")} transition-all active:scale-[0.98]'
            ).style(f'background:{C["primary"]} !important')

            async def submit() -> None:
                email = (email_input.value or "").strip()
                password = password_input.value or ""
                display_name = (name_input.value or "").strip() if name_input else ""

                if not email or "@" not in email or len(password) < 6:
                    _shake(card)
                    ui.notify(
                        "Enter a valid email and a password of at least 6 characters.",
                        type="negative", position="bottom-right",
                    )
                    return

                submit_btn.props("loading")
                submit_btn.disable()
                try:
                    if is_signup:
                        result = await run.io_bound(sign_up, email, password, display_name)
                    else:
                        result = await run.io_bound(sign_in, email, password)
                except AuthError as exc:
                    _shake(card)
                    ui.notify(str(exc), type="negative", position="bottom-right", timeout=5000)
                    return
                finally:
                    submit_btn.props(remove="loading")
                    submit_btn.enable()

                app.storage.user[SESSION_KEY] = {
                    "access_token": result.access_token,
                    "refresh_token": result.refresh_token,
                    "user_id": result.user_id,
                    "email": result.email,
                    "display_name": result.display_name,
                }
                ui.notify(f"Welcome, {result.display_name}.", type="positive", position="bottom-right", timeout=2500)
                ui.navigate.to("/")

            submit_btn.on("click", submit)
            for inp in [i for i in (name_input, email_input, password_input) if i is not None]:
                inp.on("keydown.enter", submit)

            raw_html(
                f'<p class="text-center text-[12px] {tx("muted")} mt-5">'
                + ('Already have an account? <a href="/login" class="font-semibold" style="color:' + C["primary"] + '">Log in</a>'
                   if is_signup else
                   'New here? <a href="/signup" class="font-semibold" style="color:' + C["primary"] + '">Create an account</a>')
                + '</p>'
            )


@ui.page("/login")
def login_page() -> None:
    render_auth_card("login")


@ui.page("/signup")
def signup_page() -> None:
    render_auth_card("signup")
