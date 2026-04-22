"""
app/pages/page_login.py
Sterling Stormwater — Professional dark login screen.

Fix: Split st.markdown calls so base64 logo data never trips the
markdown parser into treating subsequent HTML as a code block.
"""

import base64
from pathlib import Path
import streamlit as st
from app.services.api_client import login

_LOGO_PATH = Path("assets/sterling_logo.png")


def render():
    # ── 1. Page-level styles + background layers ──────────────────────────────
    st.markdown("""
<style>
/* Force full-dark canvas on login page */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: #06141C !important;
    min-height: 100vh !important;
}
/* Reset sidebar margin — no sidebar on login page */
[data-testid="stMain"] {
    margin-left: 0 !important;
}
[data-testid="stSidebar"] {
    display: none !important;
}
.block-container,
[data-testid="stMainBlockContainer"] {
    max-width: 440px !important;
    margin: 0 auto !important;
    padding: 0 !important;
    padding-top: 5vh !important;
}

/* Aurora glow blob */
@keyframes sw-aurora {
    0%   { transform: translate(0,0) scale(1); }
    100% { transform: translate(-80px,40px) scale(1.2); }
}
.sw-glow-blob {
    position: fixed;
    top: -10%; left: 30%;
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(26,183,56,0.09) 0%, transparent 70%);
    filter: blur(60px);
    animation: sw-aurora 14s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: 0;
}
/* Grid texture */
.sw-grid-bg {
    position: fixed; inset: 0;
    background-image:
        linear-gradient(rgba(255,255,255,0.022) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.022) 1px, transparent 1px);
    background-size: 40px 40px;
    -webkit-mask-image: radial-gradient(ellipse 70% 70% at 50% 50%, black 0%, transparent 100%);
    mask-image: radial-gradient(ellipse 70% 70% at 50% 50%, black 0%, transparent 100%);
    pointer-events: none;
    z-index: 0;
}
/* Login card container */
.sw-login-card {
    position: relative;
    z-index: 1;
    background: linear-gradient(180deg, #103447 0%, #0B2A3C 100%);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    padding: 36px 36px 28px 36px;
    box-shadow:
        0 1px 0 rgba(255,255,255,0.06) inset,
        0 24px 64px rgba(0,0,0,0.55),
        0 0 0 1px rgba(0,0,0,0.20);
    text-align: center;
}
.sw-login-card-topbar {
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    border-radius: 14px 14px 0 0;
    background: linear-gradient(90deg, transparent, rgba(26,183,56,0.55), transparent);
}
.sw-login-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: #1AB738;
    font-weight: 600;
    margin-bottom: 8px;
}
.sw-login-title {
    font-family: 'Inter', sans-serif;
    font-size: 1.5em;
    font-weight: 800;
    color: #F1F5F9;
    margin: 0 0 4px 0;
    letter-spacing: -0.02em;
}
.sw-login-sub {
    color: #6B7A8A;
    font-size: 0.84em;
    margin: 0 0 4px 0;
    font-weight: 400;
}
.sw-footer {
    text-align: center;
    padding-top: 18px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #3D4D5C;
    letter-spacing: 0.06em;
}
</style>

<div class="sw-glow-blob"></div>
<div class="sw-grid-bg"></div>
""", unsafe_allow_html=True)

    # ── 2. Logo (separate call — keeps base64 isolated from card HTML) ────────
    if _LOGO_PATH.exists():
        logo_b64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode()
        st.markdown(
            f'<div style="text-align:center;position:relative;z-index:1;'
            f'margin-bottom:-12px;padding-top:4px">'
            f'<img src="data:image/png;base64,{logo_b64}" '
            f'style="height:44px;display:inline-block;'
            f'filter:drop-shadow(0 0 24px rgba(26,183,56,0.45))" />'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── 3. Card header (no base64 here) ───────────────────────────────────────
    st.markdown("""
<div class="sw-login-card">
    <div class="sw-login-card-topbar"></div>
    <div class="sw-login-eyebrow">Field Service Platform</div>
    <div class="sw-login-title">Sign in to Sterling</div>
    <div class="sw-login-sub">Report Generator &amp; Field Documentation</div>
</div>
""", unsafe_allow_html=True)

    # ── 4. Streamlit form (native widgets, styled by global CSS) ─────────────
    mode = st.session_state.get("login_mode", "signin")

    if mode == "signin":
        with st.form("login_form", border=False):
            email    = st.text_input("Email",    placeholder="you@sterlingstormwater.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submit   = st.form_submit_button(
                "Sign In  →", type="primary", use_container_width=True
            )

        if submit:
            if not email or not password:
                st.error("Enter your email and password.")
                return
            with st.spinner("Signing in…"):
                result = login(email, password)
            if result and result.get("access_token"):
                st.session_state["token"]        = result["access_token"]
                st.session_state["current_user"] = result["user"]
                st.rerun()
            else:
                from app.services.db import local_login
                if local_login(email, password):
                    st.session_state["token"]        = "local"
                    st.session_state["current_user"] = {
                        "email": email,
                        "name":  email.split("@")[0].replace(".", " ").title(),
                    }
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

        st.markdown(
            '<div style="text-align:center;margin-top:10px">',
            unsafe_allow_html=True,
        )
        if st.button("Forgot password?", key="goto_reset",
                     help="Reset your local password"):
            st.session_state["login_mode"] = "reset"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    elif mode == "reset":
        st.markdown(
            '<div style="text-align:center;color:#9699a6;font-size:13px;'
            'margin-bottom:12px">Enter your email and choose a new password.</div>',
            unsafe_allow_html=True,
        )
        with st.form("reset_form", border=False):
            r_email    = st.text_input("Email", placeholder="you@sterlingstormwater.com")
            r_pw1      = st.text_input("New password",     type="password", placeholder="••••••••")
            r_pw2      = st.text_input("Confirm password", type="password", placeholder="••••••••")
            r_submit   = st.form_submit_button(
                "Reset Password", type="primary", use_container_width=True
            )

        if r_submit:
            from app.services.db import set_local_password, get_conn
            if not r_email or not r_pw1:
                st.error("Email and new password are required.")
            elif r_pw1 != r_pw2:
                st.error("Passwords don't match.")
            elif len(r_pw1) < 8:
                st.error("Password must be at least 8 characters.")
            else:
                # Verify email exists
                try:
                    c = get_conn()
                    row = c.execute(
                        "SELECT email FROM local_users WHERE email=?", (r_email,)
                    ).fetchone()
                except Exception:
                    row = None
                if not row:
                    st.error("No account found for that email.")
                else:
                    set_local_password(r_email, r_pw1)
                    st.success("Password updated. You can now sign in.")
                    st.session_state["login_mode"] = "signin"
                    st.rerun()

        if st.button("← Back to sign in", key="back_to_signin"):
            st.session_state["login_mode"] = "signin"
            st.rerun()

    # ── 5. Footer ─────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="sw-footer">Sterling Stormwater Maintenance Services, Inc</div>',
        unsafe_allow_html=True,
    )
