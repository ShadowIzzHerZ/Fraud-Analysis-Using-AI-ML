"""Login / sign-up screen for Zen analysts, backed by Supabase Auth (app/auth.py).

Pattern (card + pill tabs + shake-on-error) carried over from the sign-up
flow built for an earlier civic-issue-reporting app, re-themed to Zen's own
"Warm Civic Minimal" palette instead of that app's navy/orange one.
"""
from __future__ import annotations

from html import escape

from fastapi import Request
from nicegui import app, run, ui

from app.auth import (
    OAUTH_CALLBACK_PATH,
    SESSION_KEY,
    AuthError,
    complete_oauth,
    sign_in,
    sign_up,
    start_google_oauth,
)
from app.ui_dashboard import _THEME_CSS_VERSION, C, bd, bg, icon, raw_html, tx

OAUTH_VERIFIER_KEY = "zen_oauth_verifier"

# Google's official "G" mark, inline so the button needs no network round
# trip and no CDN allow-listing — this is the standard multi-color glyph
# used on Sign in with Google buttons everywhere, not app-specific art.
GOOGLE_G_SVG = (
    '<svg width="18" height="18" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">'
    '<path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.9 32.7 29.4 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 8 3l5.7-5.7C34.6 6.1 29.6 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.7-.4-3.5z"/>'
    '<path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.6 15.9 18.9 13 24 13c3.1 0 5.8 1.1 8 3l5.7-5.7C34.6 6.1 29.6 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>'
    '<path fill="#4CAF50" d="M24 44c5.5 0 10.5-2.1 14.3-5.6l-6.6-5.6C29.6 34.7 26.9 36 24 36c-5.4 0-9.9-3.3-11.3-8H6v6.2C9.4 39.7 16.1 44 24 44z"/>'
    '<path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.7 2.1-2.1 3.9-3.9 5.2l6.6 5.6C40.3 37 44 31.4 44 24c0-1.3-.1-2.7-.4-3.5z"/>'
    '</svg>'
)

TAGLINE = {
    "login": "Sign in to the fraud operations console.",
    "signup": "Create your analyst account.",
}


def _shake(el) -> None:
    el.classes(add="auth-shake")
    ui.timer(0.45, lambda: el.classes(remove="auth-shake"), once=True)


def _store_session(result) -> None:
    app.storage.user[SESSION_KEY] = {
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "user_id": result.user_id,
        "email": result.email,
        "display_name": result.display_name,
    }


def render_auth_card(mode: str, request: Request) -> None:
    is_signup = mode == "signup"

    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">'
        '<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">'
        f'<link rel="stylesheet" href="/static/theme.css?v={_THEME_CSS_VERSION}">'
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

                _store_session(result)
                ui.notify(f"Welcome, {result.display_name}.", type="positive", position="bottom-right", timeout=2500)
                ui.navigate.to("/")

            submit_btn.on("click", submit)
            for inp in [i for i in (name_input, email_input, password_input) if i is not None]:
                inp.on("keydown.enter", submit)

            raw_html(
                f'<div class="flex items-center gap-3 my-5">'
                f'<div class="flex-1 h-px {bg("outline_variant")}"></div>'
                f'<span class="text-[11px] font-semibold {tx("muted")} uppercase tracking-wider">or</span>'
                f'<div class="flex-1 h-px {bg("outline_variant")}"></div></div>'
            )

            google_btn = ui.button().props("unelevated").classes(
                f'w-full py-2.5 rounded-full font-semibold text-[13px] {tx("on_surface")} {bg("surface_lowest")} '
                f'border {bd("outline_variant")} hover:{bg("surface_low")} transition-all active:scale-[0.98]'
            )
            with google_btn:
                raw_html(f'<div class="flex items-center justify-center gap-2">{GOOGLE_G_SVG}<span>Continue with Google</span></div>')

            async def google_login() -> None:
                google_btn.props("loading")
                google_btn.disable()
                try:
                    redirect_to = str(request.base_url).rstrip("/") + OAUTH_CALLBACK_PATH
                    start = await run.io_bound(start_google_oauth, redirect_to)
                except AuthError as exc:
                    ui.notify(str(exc), type="negative", position="bottom-right", timeout=5000)
                    google_btn.props(remove="loading")
                    google_btn.enable()
                    return
                app.storage.user[OAUTH_VERIFIER_KEY] = start.code_verifier
                ui.navigate.to(start.url)

            google_btn.on("click", google_login)

            raw_html(
                f'<p class="text-center text-[12px] {tx("muted")} mt-5">'
                + ('Already have an account? <a href="/login" class="font-semibold" style="color:' + C["primary"] + '">Log in</a>'
                   if is_signup else
                   'New here? <a href="/signup" class="font-semibold" style="color:' + C["primary"] + '">Create an account</a>')
                + '</p>'
            )


@ui.page("/login")
def login_page(request: Request) -> None:
    render_auth_card("login", request)


@ui.page("/signup")
def signup_page(request: Request) -> None:
    render_auth_card("signup", request)


@ui.page(OAUTH_CALLBACK_PATH)
async def oauth_callback_page(code: str = "", error: str = "", error_description: str = "") -> None:
    """Where Google sends the browser back after consent. See app/auth.py's
    start_google_oauth/complete_oauth for the PKCE handshake this completes."""
    ui.page_title("Signing in — Zen")

    with ui.element("div").classes(
        f'min-h-screen w-full flex items-center justify-center p-4 {bg("background")} auth-stripes'
    ):
        with ui.element("div").classes(
            f'w-full max-w-[400px] {bg("surface_lowest")} border {bd("outline_variant")} '
            f'rounded-2xl shadow-lg p-8 text-center'
        ):
            raw_html(
                f'<div class="flex items-center justify-center gap-2.5 mb-4">'
                f'<div class="w-8 h-8 rounded-xl {bg("primary")} text-white flex items-center justify-center font-bold text-sm shadow-sm">Z</div>'
                f'<span class="text-[16px] font-bold tracking-tight {tx("on_surface")}">Zen</span></div>'
            )
            status = ui.column().classes("items-center w-full")

    def show_error(message: str) -> None:
        status.clear()
        with status:
            raw_html(f'<p class="text-[13px] text-rose-700 font-semibold">{escape(message)}</p>')
            raw_html(
                f'<a href="/login" class="inline-block mt-4 text-[12px] font-semibold" style="color:{C["primary"]}">Back to login</a>'
            )

    if error:
        show_error(error_description or error or "Google sign-in was cancelled.")
        return

    verifier = app.storage.user.pop(OAUTH_VERIFIER_KEY, None)
    if not code or not verifier:
        show_error(
            "This sign-in link is missing its verification data — it may have expired, or been opened in a "
            "different browser than the one you started in. Please try again."
        )
        return

    with status:
        ui.spinner(size="2em", color=C["primary"]).classes("mb-3")
        raw_html(f'<p class="text-[13px] {tx("muted")}">Finishing Google sign-in…</p>')

    try:
        result = await run.io_bound(complete_oauth, code, verifier)
    except AuthError as exc:
        show_error(str(exc))
        return

    _store_session(result)
    ui.navigate.to("/")
