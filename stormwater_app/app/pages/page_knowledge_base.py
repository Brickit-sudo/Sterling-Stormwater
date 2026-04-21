"""
app/pages/page_knowledge_base.py
Knowledge Base manager — browse templates stored in assets/knowledge_base.xlsx.

Provides:
  - Status panel (file exists / record counts)
  - Tabbed browser: Write-Ups | Captions | Summaries | Quick Notes | Sites
  - Direct link to open the Excel file
  - Re-generate button if file is missing
"""

import subprocess
import sys
from pathlib import Path

import streamlit as st
from app.components.ui_helpers import section_header

KB_PATH = Path("assets/knowledge_base.xlsx")


def _badge(text: str, color: str, bg: str) -> str:
    return (
        f'<span style="background:{bg};color:{color};font-family:\'JetBrains Mono\','
        f'monospace;font-size:11px;font-weight:600;padding:3px 10px;'
        f'border-radius:999px;border:1px solid {color}44">{text}</span>'
    )


def render():
    section_header("Knowledge Base", "Browse and manage write-up templates stored in the Excel knowledge base.")

    # ── Status banner ─────────────────────────────────────────────────────────
    if not KB_PATH.exists():
        st.warning(
            "**Knowledge base not found.** Run `python create_knowledge_base.py` "
            "from the `stormwater_app/` directory to generate it.",
            icon="📊",
        )
        if st.button("🔧 Generate Knowledge Base Now", type="primary"):
            with st.spinner("Generating…"):
                result = subprocess.run(
                    [sys.executable, "create_knowledge_base.py"],
                    capture_output=True, text=True,
                )
            if result.returncode == 0:
                st.success("Knowledge base generated successfully!", icon="✅")
                st.rerun()
            else:
                st.error(f"Generation failed:\n{result.stderr}")
        return

    try:
        from app.services.kb_service import (
            get_writeup_options, get_caption_options,
            get_summary_options, get_quick_notes,
            get_note_categories, get_site_profiles,
        )
    except Exception as e:
        st.error(f"Could not load KB service: {e}")
        return

    # Counts
    wu_count  = len(get_writeup_options("ALL", "findings"))   + \
                len(get_writeup_options("ALL", "recommendations")) + \
                len(get_writeup_options("ALL", "maintenance_performed"))
    cap_count = len(get_caption_options("ALL"))
    sum_count = len(get_summary_options("ALL"))
    note_count = len(get_quick_notes("ALL"))
    site_count = len(get_site_profiles())

    # Status cards
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, count, color in [
        (c1, "Write-Ups",   wu_count,   "#1AB738"),
        (c2, "Captions",    cap_count,  "#38BDF8"),
        (c3, "Summaries",   sum_count,  "#F59E0B"),
        (c4, "Quick Notes", note_count, "#6B7A8A"),
        (c5, "Site Profiles", site_count, "#F43F5E"),
    ]:
        col.markdown(
            f'<div style="background:linear-gradient(180deg,#103447,#0B2A3C);'
            f'border:1px solid rgba(255,255,255,0.08);border-radius:8px;'
            f'padding:14px 16px;text-align:center">'
            f'<div style="font-family:\'Inter\',sans-serif;font-size:1.4em;'
            f'font-weight:800;color:{color}">{count}</div>'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
            f'text-transform:uppercase;letter-spacing:0.10em;color:#6B7A8A;'
            f'margin-top:3px">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # File info + re-generate
    col_info, col_btn = st.columns([3, 1])
    with col_info:
        mtime = KB_PATH.stat().st_mtime
        import datetime
        mod = datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y %H:%M")
        st.caption(f"📂 `{KB_PATH.resolve()}` — Last modified: {mod}")
    with col_btn:
        if st.button("🔄 Regenerate", help="Re-run create_knowledge_base.py"):
            with st.spinner("Regenerating…"):
                result = subprocess.run(
                    [sys.executable, "create_knowledge_base.py"],
                    capture_output=True, text=True,
                )
            if result.returncode == 0:
                st.success("Regenerated!", icon="✅")
                # Clear cache
                for k in ["_kb_cache", "_kb_mtime"]:
                    st.session_state.pop(k, None)
                st.rerun()
            else:
                st.error(f"Failed: {result.stderr[:300]}")

    st.markdown("---")

    # ── Tabbed browser ────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "✏️ Write-Ups", "📷 Captions", "📄 Summaries", "📝 Quick Notes", "🏢 Site Profiles"
    ])

    with tab1:
        st.caption("Write-up templates used in the Write-Ups page. Filter by system type and field.")
        from app.constants import SYSTEM_TYPES
        sys_filter = st.selectbox("System Type", ["ALL"] + SYSTEM_TYPES, key="kb_wu_sys")
        field_filter = st.selectbox("Field", ["findings", "recommendations", "maintenance_performed", "post_service_condition"], key="kb_wu_field")
        options = get_writeup_options(sys_filter if sys_filter != "ALL" else "ALL", field_filter)
        if not options:
            st.info("No templates found for this filter.")
        for o in options:
            with st.expander(o["label"], expanded=False):
                st.text_area("Text", value=o["text"], height=150,
                             disabled=True, label_visibility="collapsed",
                             key=f"kb_wu_{o['label'][:30]}")

    with tab2:
        st.caption("Photo caption templates. Edit the Excel file to add your own.")
        from app.constants import SYSTEM_TYPES
        sys_filter2 = st.selectbox("System Type", ["ALL"] + SYSTEM_TYPES, key="kb_cap_sys")
        caps = get_caption_options(sys_filter2 if sys_filter2 != "ALL" else "ALL")
        if not caps:
            st.info("No caption templates found.")
        for c in caps:
            st.markdown(
                f'<div style="background:linear-gradient(180deg,#103447,#0B2A3C);'
                f'border:1px solid rgba(255,255,255,0.06);border-radius:6px;'
                f'padding:8px 12px;margin-bottom:4px;display:flex;'
                f'justify-content:space-between;align-items:center">'
                f'<span style="color:#B8C5D1;font-size:0.84em">'
                f'<b style="color:#F1F5F9">{c["label"]}</b>'
                f' &nbsp;·&nbsp; <span style="color:#6B7A8A">{c["view"]}</span>'
                f'</span>'
                f'<code style="color:#1AB738;font-size:0.78em">{c["caption"]}</code>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with tab3:
        st.caption("Overall summary paragraph templates.")
        sums = get_summary_options("ALL")
        for s in sums:
            with st.expander(s["label"], expanded=False):
                st.text_area("", value=s["text"], height=100,
                             disabled=True, label_visibility="collapsed",
                             key=f"kb_sum_{s['label'][:30]}")

    with tab4:
        st.caption("Quick-insert phrases used in field notes. Edit the Excel to add your own.")
        cats = get_note_categories()
        for cat in cats:
            notes = get_quick_notes(cat)
            st.markdown(
                f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
                f'text-transform:uppercase;letter-spacing:0.10em;color:#6B7A8A;'
                f'margin:14px 0 5px 0">{cat}</div>',
                unsafe_allow_html=True,
            )
            cols = st.columns(4)
            for i, note in enumerate(notes):
                cols[i % 4].markdown(
                    f'<div style="background:rgba(26,183,56,0.06);'
                    f'border:1px solid rgba(26,183,56,0.18);border-radius:6px;'
                    f'padding:5px 10px;font-size:0.82em;color:#B8C5D1;'
                    f'margin-bottom:4px">{note}</div>',
                    unsafe_allow_html=True,
                )

    with tab5:
        st.caption("Reusable site configurations. Add your recurring sites here.")
        profiles = get_site_profiles()
        if not profiles:
            st.info("No site profiles found. Add rows to the SiteProfiles sheet in the Excel file.")
        for p in profiles:
            with st.expander(f"{p['site_name']} — {p['client_name']}", expanded=False):
                c1, c2 = st.columns(2)
                c1.markdown(f"**Address:** {p['address']}")
                c2.markdown(f"**Notes:** {p['notes']}")
                if p["systems"]:
                    st.markdown("**Systems:** " + " · ".join(p["systems"]))

    st.markdown("---")
    st.caption(
        "💡 **To add templates:** Open `assets/knowledge_base.xlsx` in Excel, "
        "add rows to any sheet, save, and the app picks up changes automatically."
    )
