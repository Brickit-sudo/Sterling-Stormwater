"""
app/pages/page_bulk_import.py
Bulk Import — upload multiple PDF/DOCX reports and extract content
into the knowledge base with a review-and-approve UI.
"""

from pathlib import Path
import streamlit as st
from app.components.ui_helpers import section_header

KB_PATH = Path("assets/knowledge_base.xlsx")


def render():
    section_header(
        "Bulk Import to Knowledge Base",
        "Upload historical reports (PDF or DOCX) to extract write-ups, "
        "summaries, and captions into the knowledge base library.",
    )

    if not KB_PATH.exists():
        st.warning(
            "Knowledge base file not found. Go to **Knowledge Base** in the sidebar "
            "and click **Generate** first.",
            icon="⚠️",
        )
        return

    # ── 1. Upload ─────────────────────────────────────────────────────────────
    st.markdown("### 1 · Upload Reports")
    st.caption(
        "Select one or more Sterling inspection or maintenance reports. "
        "PDFs and Word documents (.docx) are both supported."
    )

    uploaded = st.file_uploader(
        "Drop files here or click Browse",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if not uploaded:
        st.info(
            "Upload one or more PDF or DOCX reports to extract templates from them.",
            icon="📂",
        )
        return

    # ── 2. Process ────────────────────────────────────────────────────────────
    try:
        from app.services.importer import extract_text_from_file, extract_fields
        from app.services.bulk_importer import extract_kb_rows
    except ImportError as exc:
        st.error(f"Import error: {exc}")
        return

    # Use a stable cache key based on the set of filenames
    cache_key = "bi_results_" + "_".join(sorted(f.name for f in uploaded))

    if cache_key not in st.session_state:
        all_wu, all_sum, all_cap, errors = [], [], [], []
        prog = st.progress(0.0, text="Processing reports…")
        for i, f in enumerate(uploaded):
            prog.progress((i + 0.5) / len(uploaded), text=f"Parsing {f.name}…")
            result = extract_text_from_file(f)
            if result.get("error"):
                errors.append(f"**{f.name}**: {result['error']}")
                continue
            fields       = extract_fields(result.get("raw_text", ""))
            report_type  = fields.get("report_type") or "ALL"
            source_label = Path(f.name).stem
            rows = extract_kb_rows(
                raw_text=result.get("raw_text", ""),
                sections=result.get("sections", {}),
                report_type=report_type,
                source_label=source_label,
            )
            all_wu.extend(rows["writeups"])
            all_sum.extend(rows["summaries"])
            all_cap.extend(rows["captions"])
        prog.progress(1.0, text="Done")

        st.session_state[cache_key] = {
            "wu": all_wu, "sum": all_sum, "cap": all_cap, "errors": errors,
        }

    cached = st.session_state[cache_key]
    all_wu, all_sum, all_cap = cached["wu"], cached["sum"], cached["cap"]
    errors = cached["errors"]

    for err in errors:
        st.error(err, icon="❌")

    total = len(all_wu) + len(all_sum) + len(all_cap)
    if total == 0:
        st.warning(
            "No recognizable stormwater content was extracted. "
            "Ensure the reports use Sterling headings (Findings, Bioretention, etc.).",
            icon="⚠️",
        )
        return

    # ── 3. Review ─────────────────────────────────────────────────────────────
    st.markdown(f"### 2 · Review — {len(uploaded)} file(s) processed")

    c1, c2, c3 = st.columns(3)
    for col, label, count, color in [
        (c1, "Write-Up Sections",  len(all_wu),  "#1AB738"),
        (c2, "Summary Paragraphs", len(all_sum), "#F59E0B"),
        (c3, "Photo Captions",     len(all_cap), "#38BDF8"),
    ]:
        col.markdown(
            f'<div style="background:linear-gradient(180deg,#103447,#0B2A3C);'
            f'border:1px solid rgba(255,255,255,0.08);border-radius:8px;'
            f'padding:14px 16px;text-align:center">'
            f'<div style="font-size:1.6em;font-weight:800;color:{color}">{count}</div>'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
            f'text-transform:uppercase;letter-spacing:0.10em;color:#6B7A8A;'
            f'margin-top:3px">{label}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # Selection state — keyed to this upload batch
    sel_key_wu  = f"bi_sel_wu_{cache_key}"
    sel_key_sum = f"bi_sel_sum_{cache_key}"
    sel_key_cap = f"bi_sel_cap_{cache_key}"

    if sel_key_wu  not in st.session_state: st.session_state[sel_key_wu]  = [True] * len(all_wu)
    if sel_key_sum not in st.session_state: st.session_state[sel_key_sum] = [True] * len(all_sum)
    if sel_key_cap not in st.session_state: st.session_state[sel_key_cap] = [True] * len(all_cap)

    sel_wu  = st.session_state[sel_key_wu]
    sel_sum = st.session_state[sel_key_sum]
    sel_cap = st.session_state[sel_key_cap]

    # Select / deselect all buttons
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("✅ Select All", use_container_width=True):
            st.session_state[sel_key_wu]  = [True] * len(all_wu)
            st.session_state[sel_key_sum] = [True] * len(all_sum)
            st.session_state[sel_key_cap] = [True] * len(all_cap)
            st.rerun()
    with col_b:
        if st.button("☐ Deselect All", use_container_width=True):
            st.session_state[sel_key_wu]  = [False] * len(all_wu)
            st.session_state[sel_key_sum] = [False] * len(all_sum)
            st.session_state[sel_key_cap] = [False] * len(all_cap)
            st.rerun()

    tab1, tab2, tab3 = st.tabs([
        f"✏️ Write-Ups ({len(all_wu)})",
        f"📄 Summaries ({len(all_sum)})",
        f"📷 Captions ({len(all_cap)})",
    ])

    _COND_COLOR = {"Good": "#1AB738", "Fair": "#F59E0B", "Poor": "#F43F5E", "ALL": "#6B7A8A"}

    with tab1:
        if not all_wu:
            st.info("No write-up sections extracted.")
        for i, row in enumerate(all_wu):
            chk_col, content_col = st.columns([1, 14])
            with chk_col:
                sel_wu[i] = st.checkbox("", value=sel_wu[i], key=f"bi_wu_{cache_key}_{i}")
            with content_col:
                field_display = row["field"].replace("_", " ").title()
                cond_color = _COND_COLOR.get(row["condition"], "#6B7A8A")
                st.markdown(
                    f'<div style="background:linear-gradient(180deg,#103447,#0B2A3C);'
                    f'border:1px solid rgba(255,255,255,0.06);border-left:3px solid '
                    f'{cond_color}55;border-radius:8px;padding:10px 14px;margin-bottom:4px">'
                    f'<div style="font-weight:600;font-size:13px;color:#F1F5F9;margin-bottom:4px">'
                    f'{row["label"]}</div>'
                    f'<div style="font-size:11px;color:#6B7A8A;display:flex;gap:12px;'
                    f'flex-wrap:wrap;margin-bottom:6px">'
                    f'<span>System: <b style="color:#B8C5D1">{row["system_type"]}</b></span>'
                    f'<span>Field: <b style="color:#B8C5D1">{field_display}</b></span>'
                    f'<span>Condition: <b style="color:{cond_color}">{row["condition"]}</b></span>'
                    f'</div>'
                    f'<div style="font-size:0.82em;color:#8CA3B5;max-height:80px;'
                    f'overflow-y:auto;white-space:pre-wrap;line-height:1.5">'
                    f'{row["text"][:350]}{"…" if len(row["text"]) > 350 else ""}'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

    with tab2:
        if not all_sum:
            st.info("No summary paragraphs extracted.")
        for i, row in enumerate(all_sum):
            chk_col, content_col = st.columns([1, 14])
            with chk_col:
                sel_sum[i] = st.checkbox("", value=sel_sum[i], key=f"bi_sum_{cache_key}_{i}")
            with content_col:
                st.markdown(
                    f'<div style="background:linear-gradient(180deg,#103447,#0B2A3C);'
                    f'border:1px solid rgba(255,255,255,0.06);border-radius:8px;'
                    f'padding:10px 14px;margin-bottom:4px">'
                    f'<div style="font-weight:600;font-size:13px;color:#F1F5F9;margin-bottom:4px">'
                    f'{row["label"]}</div>'
                    f'<div style="font-size:11px;color:#6B7A8A;margin-bottom:6px">'
                    f'Report type: <b style="color:#B8C5D1">{row["report_type"]}</b></div>'
                    f'<div style="font-size:0.82em;color:#8CA3B5;max-height:80px;'
                    f'overflow-y:auto;white-space:pre-wrap;line-height:1.5">'
                    f'{row["text"][:350]}{"…" if len(row["text"]) > 350 else ""}'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

    with tab3:
        if not all_cap:
            st.info("No photo captions extracted.")
        for i, row in enumerate(all_cap):
            chk_col, content_col = st.columns([1, 14])
            with chk_col:
                sel_cap[i] = st.checkbox("", value=sel_cap[i], key=f"bi_cap_{cache_key}_{i}")
            with content_col:
                st.markdown(
                    f'<div style="background:linear-gradient(180deg,#103447,#0B2A3C);'
                    f'border:1px solid rgba(255,255,255,0.06);border-radius:8px;'
                    f'padding:8px 14px;margin-bottom:4px;display:flex;'
                    f'align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">'
                    f'<span style="font-size:0.84em">'
                    f'<b style="color:#F1F5F9">{row["label"]}</b>'
                    f' <span style="color:#6B7A8A">· {row["system_type"]}</span>'
                    f'</span>'
                    f'<code style="color:#1AB738;font-size:0.78em">{row["caption"]}</code>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── 4. Commit ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 3 · Add to Knowledge Base")

    n_wu  = sum(1 for v in sel_wu  if v)
    n_sum = sum(1 for v in sel_sum if v)
    n_cap = sum(1 for v in sel_cap if v)
    n_tot = n_wu + n_sum + n_cap

    info_col, btn_col = st.columns([4, 1])
    with info_col:
        st.caption(
            f"**{n_wu}** write-up sections · **{n_sum}** summaries · "
            f"**{n_cap}** captions selected"
        )
    with btn_col:
        commit = st.button(
            f"💾 Add {n_tot} items",
            type="primary",
            use_container_width=True,
            disabled=(n_tot == 0),
        )

    if commit:
        from app.services.bulk_importer import append_rows_to_kb
        try:
            wu_rows  = [all_wu[i]  for i, v in enumerate(sel_wu)  if v]
            sum_rows = [all_sum[i] for i, v in enumerate(sel_sum) if v]
            cap_rows = [all_cap[i] for i, v in enumerate(sel_cap) if v]

            wu_added, sum_added, cap_added = append_rows_to_kb(wu_rows, sum_rows, cap_rows)

            # Bust KB cache
            for k in ["_kb_cache", "_kb_mtime"]:
                st.session_state.pop(k, None)
            # Clear batch cache so re-upload starts fresh
            st.session_state.pop(cache_key, None)

            st.success(
                f"Added {wu_added} write-ups, {sum_added} summaries, "
                f"and {cap_added} captions to the knowledge base.",
                icon="✅",
            )
            st.balloons()
        except Exception as exc:
            st.error(f"Failed to save: {exc}")

    st.caption(
        "💡 After importing, visit **Knowledge Base** in the sidebar to browse and "
        "clean up entries. Open `assets/knowledge_base.xlsx` directly to rename labels."
    )
