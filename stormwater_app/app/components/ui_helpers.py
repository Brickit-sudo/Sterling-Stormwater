"""
app/components/ui_helpers.py
Reusable small UI elements used across multiple pages.
"""

import streamlit as st


def section_header(title: str, subtitle: str = ""):
    """Dark enterprise page section header with Sterling Green accent bar."""
    st.markdown(
        f'<div style="padding:8px 0 10px 0;margin-bottom:4px">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">'
        f'<div style="width:3px;height:16px;background:#1AB738;border-radius:2px;'
        f'box-shadow:0 0 8px rgba(26,183,56,0.60)"></div>'
        f'<h2 style="font-family:\'Inter\',sans-serif;font-size:1.15em;font-weight:700;'
        f'color:#F1F5F9;margin:0;letter-spacing:-0.01em">{title}</h2>'
        f'</div>'
        + (
            f'<p style="color:#6B7A8A;font-size:0.84em;margin:0 0 4px 22px;'
            f'font-weight:450">{subtitle}</p>'
            if subtitle else ""
        )
        + f'</div>',
        unsafe_allow_html=True,
    )


def nav_buttons(prev_page: str = None, next_page: str = None,
                prev_label: str = "← Back", next_label: str = "Next →"):
    """Bottom navigation row shared across all pages."""
    from app.session import set_page
    cols = st.columns([1, 4, 1])
    with cols[0]:
        if prev_page and st.button(prev_label, use_container_width=True):
            set_page(prev_page)
            st.rerun()
    with cols[2]:
        if next_page and st.button(next_label, type="primary", use_container_width=True):
            set_page(next_page)
            st.rerun()


def info_box(text: str):
    st.info(text, icon="ℹ️")


def warning_box(text: str):
    st.warning(text, icon="⚠️")


def field_row(label: str, value: str) -> str:
    """Labeled text input row, returns new value."""
    return st.text_input(label, value=value)


def report_type_badge(report_type: str):
    colors = {
        "Inspection": "🔵",
        "Maintenance": "🟠",
        "Inspection and Maintenance": "🟢",
    }
    icon = colors.get(report_type, "⚪")
    st.markdown(f"**Report Type:** {icon} {report_type}")
