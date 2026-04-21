"""
app/pages/page_writeups.py
Screen 3: Editable write-up sections for each selected system.
One tab per system entry. Fields vary by report type.
Includes AI Draft buttons (require ANTHROPIC_API_KEY in .env).
"""

import streamlit as st
from app.session import get_project, get_write_up
from app.constants import (
    get_default_findings,
    get_default_recommendations,
    get_default_maintenance,
    get_default_post_service,
    CONDITION_RATINGS,
)
from app.components.ui_helpers import section_header, nav_buttons, info_box, warning_box

# Knowledge base
try:
    from app.services.kb_service import (
        kb_available, get_writeup_options, get_summary_options
    )
    _KB_ON = True
except Exception:
    _KB_ON = False


def _kb_picker(
    field: str,
    system_type: str,
    condition: str,
    apply_key: str,
    disabled: bool = False,
) -> str | None:
    """
    Render a compact 'Load from Library' expander.
    Returns the selected template text, or None if nothing was chosen.
    """
    if disabled or not _KB_ON or not kb_available():
        return None

    options = get_writeup_options(system_type, field, condition)
    if not options:
        return None

    with st.expander(f"📖 Load from Library ({len(options)} templates)", expanded=False):
        labels = [o["label"] for o in options]
        chosen_label = st.selectbox(
            "Template",
            labels,
            key=f"kb_sel_{apply_key}",
            label_visibility="collapsed",
        )
        chosen = next((o for o in options if o["label"] == chosen_label), None)
        if chosen:
            st.markdown(
                f'<div style="background:rgba(26,183,56,0.06);border:1px solid '
                f'rgba(26,183,56,0.20);border-radius:6px;padding:10px 12px;'
                f'font-size:0.83em;color:#B8C5D1;line-height:1.55;'
                f'max-height:120px;overflow-y:auto;white-space:pre-wrap">'
                f'{chosen["text"][:400]}{"…" if len(chosen["text"]) > 400 else ""}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("✅ Use this template", key=f"kb_apply_{apply_key}",
                         type="primary", use_container_width=True):
                return chosen["text"]
    return None


def _kb_summary_picker(report_type: str, disabled: bool = False) -> str | None:
    """Render a 'Load from Library' expander for the overall summary field."""
    if disabled or not _KB_ON or not kb_available():
        return None

    options = get_summary_options(report_type)
    if not options:
        return None

    with st.expander(f"📖 Summary Library ({len(options)} templates)", expanded=False):
        labels = [o["label"] for o in options]
        chosen_label = st.selectbox(
            "Template",
            labels,
            key="kb_sum_sel",
            label_visibility="collapsed",
        )
        chosen = next((o for o in options if o["label"] == chosen_label), None)
        if chosen:
            st.markdown(
                f'<div style="background:rgba(26,183,56,0.06);border:1px solid '
                f'rgba(26,183,56,0.20);border-radius:6px;padding:10px 12px;'
                f'font-size:0.83em;color:#B8C5D1;line-height:1.55;'
                f'white-space:pre-wrap">'
                f'{chosen["text"]}</div>',
                unsafe_allow_html=True,
            )
            if st.button("✅ Use this template", key="kb_sum_apply",
                         type="primary", use_container_width=True):
                return chosen["text"]
    return None


def _get_import_options(proj) -> dict:
    return proj.imported_text if proj.imported_text else {}


def _ai_available() -> bool:
    try:
        from app.services.llm_service import api_key_configured
        return api_key_configured()
    except Exception:
        return False


def _draft_button(label: str, key: str, draft_key: str,
                  system_type: str, system_id: str, condition: str,
                  notes: str, report_type: str, field: str,
                  site_name: str, inspection_date: str) -> None:
    """
    Render the 'AI Draft' button for one write-up field.
    The draft is stored in session_state[draft_key] and displayed below
    the text area; the user explicitly clicks 'Accept' to apply it.
    """
    if not _ai_available():
        st.caption("*Set ANTHROPIC_API_KEY in .env to enable AI drafts.*")
        return

    if st.button(f"✨ AI Draft", key=key, help="Generate a draft using Claude AI"):
        with st.spinner("Drafting…"):
            try:
                from app.services.llm_service import generate_writeup
                draft = generate_writeup(
                    system_type=system_type,
                    system_id=system_id,
                    condition=condition,
                    notes=notes,
                    report_type=report_type,
                    field=field,
                    site_name=site_name,
                    inspection_date=inspection_date,
                )
                st.session_state[draft_key] = draft
            except Exception as e:
                st.error(f"AI generation failed: {e}")


def _show_draft(draft_key: str, textarea_key: str, wu_attr_setter) -> None:
    """If a draft exists in session_state, show it with Accept / Dismiss buttons."""
    draft = st.session_state.get(draft_key)
    if not draft:
        return
    st.info(draft)
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("✅ Accept", key=f"accept_{draft_key}"):
            st.session_state[textarea_key] = draft
            wu_attr_setter(draft)
            del st.session_state[draft_key]
            st.rerun()
    with col_b:
        if st.button("✖ Dismiss", key=f"dismiss_{draft_key}"):
            del st.session_state[draft_key]
            st.rerun()


def render():
    section_header(
        "Write-Up Editor",
        "Review and edit the findings, recommendations, and maintenance narrative for each system."
    )

    proj = get_project()

    if not proj.systems:
        warning_box(
            "No systems configured. Go back to System Selection and add at least one system."
        )
        nav_buttons(prev_page="systems", next_page="export")
        return

    # Check report lock
    is_locked = getattr(proj.meta, "status", "Draft") == "Delivered"
    if is_locked:
        st.error("🔒 This report has been marked as Delivered and is read-only. "
                 "Use **Create Revision** on the Export page to make changes.", icon="🔒")

    report_type     = proj.meta.report_type
    is_inspection   = report_type in ("Inspection", "Inspection and Maintenance")
    is_maintenance  = report_type in ("Maintenance", "Inspection and Maintenance")
    import_sections = _get_import_options(proj)
    ai_on           = _ai_available()
    site_name       = proj.meta.site_name or ""
    inspection_date = proj.meta.inspection_date or ""

    if not is_locked:
        info_box(
            "Each tab corresponds to one system. All text is fully editable — the defaults are "
            "prompts, not final copy. Use ✨ AI Draft to generate a starting point from your field notes."
        )

    # ── Auto-preload summary from imported report ─────────────────────────────
    import_extracted = st.session_state.get("import_extracted", {})
    if import_extracted and not proj.meta.site_description:
        raw_summary = import_extracted.get("raw_summary", "")
        if raw_summary:
            proj.meta.site_description = raw_summary.strip()
            st.toast("Overall summary preloaded from imported report.", icon="📋")

    # ── Auto-preload per-system write-ups from archived report ────────────────
    imported_writeups = st.session_state.get("imported_writeups", {})
    if imported_writeups and proj.systems:
        seeded = 0
        for entry in proj.systems:
            sid_upper = entry.system_id.upper()
            wup_data  = imported_writeups.get(sid_upper, {})
            if not wup_data:
                continue
            wu = proj.write_ups.get(entry.entry_id)
            if wu is None:
                continue
            if wup_data.get("findings") and not wu.findings:
                wu.findings = wup_data["findings"].strip()
                seeded += 1
            if wup_data.get("recommendations") and not wu.recommendations:
                wu.recommendations = wup_data["recommendations"].strip()
                seeded += 1
        if seeded:
            st.toast(f"Preloaded write-ups from archived report.", icon="📋")

    # ── Field conditions recap ────────────────────────────────────────────────
    if proj.systems:
        st.markdown("**📋 Field Conditions Recap**")
        st.caption("Quick reference from the Systems page — edit conditions and notes there.")
        _COND_COLORS = {"Good": "#27AD3D", "Fair": "#d48b00", "Poor": "#cc2222", "N/A": "#888"}
        for entry in proj.systems:
            color      = _COND_COLORS.get(entry.condition, "#555")
            notes_part = f"  ·  *{entry.notes}*" if entry.notes else ""
            st.markdown(
                f'<div style="font-size:0.9em;margin:2px 0">'
                f'<b>{entry.display_name}</b> '
                f'<span style="color:{color};font-weight:bold">[{entry.condition}]</span>'
                f'{notes_part}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("---")

    # ── Overall Summary ───────────────────────────────────────────────────────
    st.markdown("**Overall Summary**")

    # KB summary picker
    _kb_sum_result = _kb_summary_picker(report_type, disabled=is_locked)
    if _kb_sum_result:
        proj.meta.site_description = _kb_sum_result
        st.rerun()

    sum_col, sum_btn_col = st.columns([5, 1])
    with sum_col:
        proj.meta.site_description = st.text_area(
            label="overall_summary",
            value=proj.meta.site_description,
            height=140,
            key="meta_site_description",
            label_visibility="collapsed",
            disabled=is_locked,
            placeholder=(
                "e.g. An inspection of the above referenced stormwater components was performed on "
                "[date]. The results of the inspection revealed the following..."
            ),
            help=(
                "This paragraph appears on the cover page in the summary section. "
                "Describe the overall scope, what was inspected/maintained, and key findings."
            ),
        )
    with sum_btn_col:
        if not is_locked and ai_on:
            if st.button("✨ AI Draft", key="gen_summary",
                         help="Generate a summary from system conditions"):
                with st.spinner("Drafting…"):
                    try:
                        from app.services.llm_service import generate_summary
                        systems_data = [
                            {"system_type": s.system_type, "system_id": s.system_id,
                             "display_name": s.display_name, "condition": s.condition,
                             "notes": s.notes}
                            for s in proj.systems
                        ]
                        draft = generate_summary(
                            systems=systems_data,
                            report_type=report_type,
                            site_name=site_name,
                            inspection_date=inspection_date,
                        )
                        st.session_state["ai_draft_summary"] = draft
                    except Exception as e:
                        st.error(f"AI generation failed: {e}")
        elif not is_locked and not ai_on:
            st.caption("*Add API key for AI drafts*")

    # Show summary draft
    if not is_locked:
        _show_draft(
            "ai_draft_summary",
            "meta_site_description",
            lambda v: setattr(proj.meta, "site_description", v),
        )

    st.caption(f"{len(proj.meta.site_description)} characters")
    st.markdown("---")

    # ── Tabs — one per system ─────────────────────────────────────────────────
    tab_labels = [f"{s.system_id}" for s in proj.systems]
    tabs       = st.tabs(tab_labels)

    for tab, entry in zip(tabs, proj.systems):
        with tab:
            wu = get_write_up(entry.entry_id)

            st.markdown(f"### {entry.display_name}")
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**Type:** {entry.system_type}")
                if entry.notes:
                    st.caption(entry.notes)
            with col2:
                cond_idx = CONDITION_RATINGS.index(entry.condition) \
                    if entry.condition in CONDITION_RATINGS else 0
                entry.condition = st.selectbox(
                    "Overall Condition",
                    CONDITION_RATINGS,
                    index=cond_idx,
                    key=f"wu_cond_{entry.entry_id}",
                    disabled=is_locked,
                )

            st.markdown("---")

            # ── Inspection fields ─────────────────────────────────────────────
            if is_inspection:
                if import_sections and not is_locked:
                    with st.expander("📋 Pre-fill from imported report", expanded=False):
                        for section_name, text in import_sections.items():
                            st.caption(f"**{section_name}** ({len(text)} chars)")
                            if st.button(
                                f"Load '{section_name}' into Findings",
                                key=f"prefill_findings_{entry.entry_id}_{section_name}",
                            ):
                                wu.findings = text[:3000]
                                st.rerun()

                if not wu.findings:
                    wu.findings = get_default_findings(
                        entry.system_type, entry.system_id, entry.condition
                    )
                if not wu.recommendations:
                    wu.recommendations = get_default_recommendations(
                        entry.system_type, entry.system_id
                    )

                # KB findings picker
                _kb_f = _kb_picker(
                    "findings", entry.system_type, entry.condition,
                    f"findings_{entry.entry_id}", disabled=is_locked,
                )
                if _kb_f:
                    wu.findings = _kb_f
                    st.rerun()

                # Findings
                f_col, f_btn = st.columns([5, 1])
                with f_col:
                    st.markdown("#### Findings")
                with f_btn:
                    if not is_locked:
                        _draft_button(
                            label="AI Draft", key=f"gen_findings_{entry.entry_id}",
                            draft_key=f"ai_findings_{entry.entry_id}",
                            system_type=entry.system_type, system_id=entry.system_id,
                            condition=entry.condition, notes=entry.notes,
                            report_type=report_type, field="findings",
                            site_name=site_name, inspection_date=inspection_date,
                        )

                wu.findings = st.text_area(
                    label="findings", value=wu.findings, height=200,
                    key=f"findings_{entry.entry_id}", label_visibility="collapsed",
                    disabled=is_locked,
                    help="Describe observed conditions: inlet, outlet, media, vegetation, "
                         "structural elements, sediment accumulation, erosion, clogging.",
                )
                if not is_locked:
                    _show_draft(
                        f"ai_findings_{entry.entry_id}",
                        f"findings_{entry.entry_id}",
                        lambda v, wu=wu: setattr(wu, "findings", v),
                    )
                st.caption(f"{len(wu.findings)} characters")

                # KB recommendations picker
                _kb_r = _kb_picker(
                    "recommendations", entry.system_type, entry.condition,
                    f"recs_{entry.entry_id}", disabled=is_locked,
                )
                if _kb_r:
                    wu.recommendations = _kb_r
                    st.rerun()

                # Recommendations
                r_col, r_btn = st.columns([5, 1])
                with r_col:
                    st.markdown("#### Recommendations")
                with r_btn:
                    if not is_locked:
                        _draft_button(
                            label="AI Draft", key=f"gen_recs_{entry.entry_id}",
                            draft_key=f"ai_recs_{entry.entry_id}",
                            system_type=entry.system_type, system_id=entry.system_id,
                            condition=entry.condition, notes=entry.notes,
                            report_type=report_type, field="recommendations",
                            site_name=site_name, inspection_date=inspection_date,
                        )

                wu.recommendations = st.text_area(
                    label="recommendations", value=wu.recommendations, height=150,
                    key=f"recommendations_{entry.entry_id}", label_visibility="collapsed",
                    disabled=is_locked,
                    help="List corrective actions or confirm no action required. "
                         "Reference the O&M Plan where appropriate.",
                )
                if not is_locked:
                    _show_draft(
                        f"ai_recs_{entry.entry_id}",
                        f"recommendations_{entry.entry_id}",
                        lambda v, wu=wu: setattr(wu, "recommendations", v),
                    )
                st.caption(f"{len(wu.recommendations)} characters")

            # ── Maintenance fields ────────────────────────────────────────────
            if is_maintenance:
                if not wu.maintenance_performed:
                    wu.maintenance_performed = get_default_maintenance(
                        entry.system_type, entry.system_id
                    )
                if not wu.post_service_condition:
                    wu.post_service_condition = get_default_post_service(
                        entry.system_type, entry.system_id
                    )

                # KB maintenance picker
                _kb_m = _kb_picker(
                    "maintenance_performed", entry.system_type, entry.condition,
                    f"maint_{entry.entry_id}", disabled=is_locked,
                )
                if _kb_m:
                    wu.maintenance_performed = _kb_m
                    st.rerun()

                # Maintenance Performed
                m_col, m_btn = st.columns([5, 1])
                with m_col:
                    st.markdown("#### Maintenance Performed")
                with m_btn:
                    if not is_locked:
                        _draft_button(
                            label="AI Draft", key=f"gen_maint_{entry.entry_id}",
                            draft_key=f"ai_maint_{entry.entry_id}",
                            system_type=entry.system_type, system_id=entry.system_id,
                            condition=entry.condition, notes=entry.notes,
                            report_type=report_type, field="maintenance_performed",
                            site_name=site_name, inspection_date=inspection_date,
                        )

                wu.maintenance_performed = st.text_area(
                    label="maintenance_performed", value=wu.maintenance_performed, height=200,
                    key=f"maint_{entry.entry_id}", label_visibility="collapsed",
                    disabled=is_locked,
                    help="Describe all work completed: debris removal, sediment removal, "
                         "vegetation management, inlet/outlet clearing, repairs.",
                )
                if not is_locked:
                    _show_draft(
                        f"ai_maint_{entry.entry_id}",
                        f"maint_{entry.entry_id}",
                        lambda v, wu=wu: setattr(wu, "maintenance_performed", v),
                    )
                st.caption(f"{len(wu.maintenance_performed)} characters")

                # KB post-service picker
                _kb_ps = _kb_picker(
                    "post_service_condition", entry.system_type, entry.condition,
                    f"post_{entry.entry_id}", disabled=is_locked,
                )
                if _kb_ps:
                    wu.post_service_condition = _kb_ps
                    st.rerun()

                # Post-Service Condition
                ps_col, ps_btn = st.columns([5, 1])
                with ps_col:
                    st.markdown("#### Post-Service Condition / Follow-Up")
                with ps_btn:
                    if not is_locked:
                        _draft_button(
                            label="AI Draft", key=f"gen_post_{entry.entry_id}",
                            draft_key=f"ai_post_{entry.entry_id}",
                            system_type=entry.system_type, system_id=entry.system_id,
                            condition=entry.condition, notes=entry.notes,
                            report_type=report_type, field="post_service_condition",
                            site_name=site_name, inspection_date=inspection_date,
                        )

                wu.post_service_condition = st.text_area(
                    label="post_service", value=wu.post_service_condition, height=120,
                    key=f"post_svc_{entry.entry_id}", label_visibility="collapsed",
                    disabled=is_locked,
                    help="Condition after service and any outstanding items.",
                )
                if not is_locked:
                    _show_draft(
                        f"ai_post_{entry.entry_id}",
                        f"post_svc_{entry.entry_id}",
                        lambda v, wu=wu: setattr(wu, "post_service_condition", v),
                    )
                st.caption(f"{len(wu.post_service_condition)} characters")

            # ── Placeholder check ─────────────────────────────────────────────
            if not is_locked:
                placeholders_remain = (
                    "[" in wu.findings or "[" in wu.recommendations or
                    "[" in wu.maintenance_performed or "[" in wu.post_service_condition
                )
                if placeholders_remain:
                    st.warning(
                        "This system still has placeholder text (brackets [ ]). "
                        "Replace all bracketed prompts before exporting.",
                        icon="⚠️",
                    )

    nav_buttons(prev_page="systems", next_page="export")
