"""
app/components/styles.py
Sterling Stormwater — monday.com-inspired dark enterprise design system.

Palette (monday.com dark theme + Sterling brand):
  Base:      #181b34  — main background (monday dark)
  Surface:   #1c1f3b  — sidebar, topbar (monday board_views_blue)
  Elevated:  #30324e  — cards, panels (monday panel)
  Overlay:   #363a52  — hover, popovers (monday hover)
  Input:     #2a2d4a  — form fields
  Green:     #1AB738  — Sterling accent / primary CTA
  Text:      #d5d8df  primary · #9699a6  secondary · #6e6f8f  muted
"""

import streamlit as st


def inject_styles():
    st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════════════════
   FONTS — Figtree (monday.com primary) + JetBrains Mono
═══════════════════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ═══════════════════════════════════════════════════════════════════════════
   DESIGN TOKENS — monday.com dark palette + Sterling brand
═══════════════════════════════════════════════════════════════════════════ */
:root {
  /* Backgrounds — monday.com dark theme */
  --bg-base:     #181b34;
  --bg-surface:  #1c1f3b;
  --bg-elevated: #30324e;
  --bg-overlay:  #363a52;
  --bg-input:    #2a2d4a;

  /* Borders */
  --border-subtle:  rgba(255,255,255,0.06);
  --border-default: #4b4e69;
  --border-strong:  rgba(255,255,255,0.22);
  --border-accent:  rgba(26,183,56,0.40);

  /* Text — monday.com dark text hierarchy */
  --text-primary:   #d5d8df;
  --text-secondary: #9699a6;
  --text-muted:     #6e6f8f;
  --text-disabled:  #4b4e69;
  --text-on-green:  #04140A;

  /* Brand — Sterling Green */
  --green:       #1AB738;
  --green-hover: #22D344;
  --green-glow:  rgba(26,183,56,0.25);
  --green-dim:   rgba(26,183,56,0.14);

  /* Status — monday.com colors */
  --danger:  #e2445c;
  --warning: #ffcb00;
  --info:    #579bfc;

  /* Motion — monday.com productive timing */
  --motion-fast: 100ms;
  --motion-base: 150ms;
  --ease-out: cubic-bezier(0.4, 0, 0.2, 1);

  /* Layout */
  --sidebar-width:  230px;
  --topbar-height:  52px;
  --viewtab-height: 40px;
  --content-offset: calc(var(--topbar-height) + var(--viewtab-height));
}

/* ═══════════════════════════════════════════════════════════════════════════
   HIDE STREAMLIT CHROME
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
.stAppHeader,
#MainMenu, footer { display: none !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   BASE RESET
═══════════════════════════════════════════════════════════════════════════ */
html, body {
  background: var(--bg-base) !important;
  color: var(--text-primary) !important;
  font-size: 13px;
}
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
  background: var(--bg-base) !important;
  color: var(--text-primary) !important;
  font-family: 'Figtree', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

/* Native Streamlit sidebar handles stMain offset via flexbox — no manual margin needed */

/* ═══════════════════════════════════════════════════════════════════════════
   LAYOUT — push content below fixed topbar + viewtabs
═══════════════════════════════════════════════════════════════════════════ */
.block-container,
[data-testid="stMainBlockContainer"] {
  max-width: 100% !important;
  padding-top: calc(var(--content-offset) + 20px) !important;
  padding-left: 1rem !important;
  padding-right: 1rem !important;
  padding-bottom: 2rem !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE ENTER ANIMATION
═══════════════════════════════════════════════════════════════════════════ */
@keyframes sw-fade-up {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.main .block-container > div {
  animation: sw-fade-up 200ms var(--ease-out);
}

/* ═══════════════════════════════════════════════════════════════════════════
   TYPOGRAPHY
═══════════════════════════════════════════════════════════════════════════ */
.stMarkdown p, .stMarkdown li,
[data-testid="stMarkdownContainer"] p {
  color: var(--text-secondary) !important;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.55;
}
.stMarkdown strong, .stMarkdown b,
[data-testid="stMarkdownContainer"] strong {
  color: var(--text-primary) !important;
  font-weight: 600;
}
.stMarkdown h1 {
  color: var(--text-primary) !important;
  font-size: 1.6rem !important; font-weight: 700 !important;
  letter-spacing: -0.02em !important; line-height: 1.25 !important;
}
.stMarkdown h2 {
  color: var(--text-primary) !important;
  font-size: 1.25rem !important; font-weight: 600 !important;
  letter-spacing: -0.015em !important;
}
.stMarkdown h3 {
  color: var(--text-primary) !important;
  font-size: 1.05rem !important; font-weight: 600 !important;
  letter-spacing: -0.01em !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   WIDGET LABELS
═══════════════════════════════════════════════════════════════════════════ */
label[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] p,
.stSelectbox label p, .stTextInput label p,
.stTextArea label p, .stCheckbox label p, .stRadio label p {
  color: var(--text-secondary) !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   INPUTS
═══════════════════════════════════════════════════════════════════════════ */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
  background: var(--bg-input) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 6px !important;
  font-size: 13px !important;
  font-weight: 400 !important;
  min-height: 36px !important;
  transition: border-color var(--motion-fast) var(--ease-out),
              box-shadow var(--motion-fast) var(--ease-out) !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
  border-color: rgba(26,183,56,0.60) !important;
  box-shadow: 0 0 0 3px rgba(26,183,56,0.12) !important;
  outline: none !important;
}
.stTextInput > div > div > input::placeholder { color: var(--text-muted) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   TEXTAREAS
═══════════════════════════════════════════════════════════════════════════ */
.stTextArea > div > div > textarea {
  background: var(--bg-input) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 6px !important;
  font-size: 13px !important;
  font-weight: 400 !important;
  transition: border-color var(--motion-fast) var(--ease-out),
              box-shadow var(--motion-fast) var(--ease-out) !important;
}
.stTextArea > div > div > textarea:focus {
  border-color: rgba(26,183,56,0.60) !important;
  box-shadow: 0 0 0 3px rgba(26,183,56,0.12) !important;
}
.stTextArea > div > div > textarea::placeholder { color: var(--text-muted) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   SELECTBOX
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stSelectbox"] > div[data-baseweb="select"] > div,
[data-baseweb="select"] > div:first-child {
  background: var(--bg-input) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 6px !important;
  min-height: 36px !important;
}
[data-baseweb="select"] span,
[data-baseweb="select"] > div div {
  color: var(--text-primary) !important;
  background: transparent !important;
  font-size: 13px !important;
}

/* Dropdown portal */
[data-baseweb="popover"], [data-baseweb="popover"] > div,
[data-baseweb="popover"] [data-baseweb="menu"] {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 6px !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.50) !important;
}
[data-baseweb="popover"] ul, [data-baseweb="popover"] [role="listbox"], ul[role="listbox"] {
  background: var(--bg-elevated) !important;
}
[data-baseweb="popover"] li, [data-baseweb="popover"] [role="option"], li[role="option"] {
  background: transparent !important;
  color: var(--text-secondary) !important;
  font-size: 13px !important;
}
[data-baseweb="popover"] li:hover, li[role="option"]:hover {
  background: var(--bg-overlay) !important;
  color: var(--text-primary) !important;
}
[data-baseweb="popover"] [aria-selected="true"], li[role="option"][aria-selected="true"] {
  background: var(--green-dim) !important;
  color: var(--green) !important;
  font-weight: 500 !important;
}
[data-baseweb="popover"] li > *, [data-baseweb="popover"] [role="option"] > *,
[data-baseweb="popover"] [role="option"] span, [data-baseweb="popover"] [role="option"] div {
  background: transparent !important; color: inherit !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   FILE UPLOADER
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stFileUploaderDropzone"] {
  background: var(--bg-elevated) !important;
  border: 1px dashed var(--border-default) !important;
  border-radius: 8px !important;
}
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] small { color: var(--text-muted) !important; font-size: 13px !important; }
[data-testid="stFileUploaderDropzone"] button {
  background: linear-gradient(180deg,#1AB738 0%,#149A2E 100%) !important;
  border: 1px solid rgba(26,183,56,0.60) !important;
  color: #04140A !important; border-radius: 6px !important; font-weight: 600 !important; font-size: 13px !important;
}
[data-testid="stFileUploaderDropzone"] button:hover {
  background: linear-gradient(180deg,#22D344 0%,#18B135 100%) !important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 6px !important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] span,
[data-testid="stFileUploader"] [data-testid="stFileUploaderFileName"] { color: var(--text-secondary) !important; font-size: 13px !important; }
[data-testid="stFileUploader"] button[kind="minimal"],
[data-testid="stFileUploader"] button[title="Remove file"] { color: var(--text-muted) !important; background: transparent !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   EXPANDERS
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 8px !important;
  transition: border-color var(--motion-base) var(--ease-out) !important;
}
[data-testid="stExpander"]:hover { border-color: rgba(255,255,255,0.16) !important; }
[data-testid="stExpander"] summary {
  background: var(--bg-elevated) !important;
  color: var(--text-primary) !important;
}
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span {
  color: var(--text-secondary) !important;
  font-weight: 500 !important;
  font-size: 13px !important;
}
details[data-testid="stExpander"] > div[data-testid="stExpanderDetails"] {
  background: var(--bg-elevated) !important;
  border-top: 1px solid var(--border-subtle) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   MISC ELEMENTS
═══════════════════════════════════════════════════════════════════════════ */
hr { border-color: var(--border-subtle) !important; margin: 8px 0 !important; }
[data-testid="stCheckbox"] label p, [data-testid="stCheckbox"] span { color: var(--text-secondary) !important; font-size: 13px !important; }
[data-testid="stRadio"] label p { color: var(--text-secondary) !important; font-size: 13px !important; }
[data-testid="stAlert"] {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 6px !important;
}
[data-testid="stAlert"] p, [data-testid="stAlert"] div { color: var(--text-secondary) !important; font-size: 13px !important; }
[data-testid="stSpinner"] p { color: var(--text-muted) !important; }

.stCaption p {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px !important; letter-spacing: 0.4px !important;
  color: var(--text-muted) !important;
}
[data-testid="stMetricLabel"] {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px !important; text-transform: uppercase !important;
  letter-spacing: 0.08em !important; color: var(--text-muted) !important;
}
[data-testid="stMetricValue"] {
  color: var(--text-primary) !important;
  font-weight: 700 !important;
  font-size: 1.5rem !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   TABS — compact monday.com style
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stTabs"] button[data-baseweb="tab"] {
  font-size: 12px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.07em !important;
  color: var(--text-muted) !important;
  background: transparent !important;
  font-weight: 500 !important;
  padding: 8px 12px !important;
  transition: color var(--motion-fast) var(--ease-out) !important;
}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--green) !important;
  border-bottom-color: var(--green) !important;
  font-weight: 600 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid var(--border-default) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   BORDERED CONTAINERS
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 8px !important;
  box-shadow: 0 1px 0 rgba(255,255,255,0.03) inset, 0 4px 12px rgba(0,0,0,0.30) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   BUTTON INTERNALS — strip Streamlit injected bg
═══════════════════════════════════════════════════════════════════════════ */
button[data-testid^="stBaseButton"] *,
button[data-testid^="stBaseButton"] > div,
button[data-testid^="stBaseButton"] > div > span,
button[data-testid^="stBaseButton"] [data-has-shortcut],
button[data-testid^="stBaseButton"] [data-testid="stMarkdownContainer"],
button[data-testid^="stBaseButton"] [data-testid="stMarkdownContainer"] p,
.stButton > button *, .stButton > button > div,
.stButton > button > div > span, .stButton > button [data-has-shortcut],
.stButton > button [data-testid="stMarkdownContainer"],
.stButton > button [data-testid="stMarkdownContainer"] p {
  background: transparent !important; background-color: transparent !important;
  color: inherit !important; border: none !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   BUTTONS — Primary (Sterling Green)
═══════════════════════════════════════════════════════════════════════════ */
button[data-testid="stBaseButton-primary"],
.stButton > button[kind="primary"] {
  background: linear-gradient(180deg,#1AB738 0%,#149A2E 100%) !important;
  color: #04140A !important;
  border: 1px solid rgba(26,183,56,0.60) !important;
  border-radius: 6px !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  box-shadow: 0 1px 0 rgba(255,255,255,0.18) inset, 0 1px 3px rgba(0,0,0,0.30) !important;
  transition: all var(--motion-fast) var(--ease-out) !important;
}
button[data-testid="stBaseButton-primary"]:hover,
.stButton > button[kind="primary"]:hover {
  background: linear-gradient(180deg,#22D344 0%,#18B135 100%) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 12px rgba(26,183,56,0.30) !important;
}
button[data-testid="stBaseButton-primary"]:active,
.stButton > button[kind="primary"]:active { transform: scale(0.97) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   BUTTONS — Secondary (ghost)
═══════════════════════════════════════════════════════════════════════════ */
button[data-testid="stBaseButton-secondary"],
.stButton > button[kind="secondary"],
.stButton > button:not([kind="primary"]) {
  background: rgba(255,255,255,0.05) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 6px !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  transition: all var(--motion-fast) var(--ease-out) !important;
}
button[data-testid="stBaseButton-secondary"]:hover,
.stButton > button[kind="secondary"]:hover,
.stButton > button:not([kind="primary"]):hover {
  background: rgba(255,255,255,0.09) !important;
  border-color: rgba(255,255,255,0.22) !important;
  transform: translateY(-1px) !important;
}
button[data-testid="stBaseButton-secondary"]:active,
.stButton > button:not([kind="primary"]):active { transform: scale(0.97) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   BUTTONS — Disabled
═══════════════════════════════════════════════════════════════════════════ */
.stButton > button:disabled, .stButton > button[disabled],
button[data-testid^="stBaseButton"]:disabled {
  background: rgba(255,255,255,0.03) !important;
  color: var(--text-disabled) !important;
  border: 1px solid rgba(255,255,255,0.05) !important;
  opacity: 1 !important; cursor: not-allowed !important; box-shadow: none !important;
}

/* Download button */
[data-testid="stDownloadButton"] > button {
  background: linear-gradient(180deg,#1AB738 0%,#149A2E 100%) !important;
  border: 1px solid rgba(26,183,56,0.60) !important;
  color: #04140A !important; font-weight: 600 !important;
  border-radius: 6px !important; font-size: 13px !important;
}
[data-testid="stDownloadButton"] > button:hover {
  background: linear-gradient(180deg,#22D344 0%,#18B135 100%) !important;
  transform: translateY(-1px) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   SIDEBAR COLLAPSE — hide native Streamlit « button; we use our own ◀ toggle
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {
  display: none !important;
}

/* Smooth topbar + viewtabs slide when sidebar toggles */
.monday-topbar, .monday-view-tabs {
  transition: left 200ms var(--ease-out) !important;
}

/* Sidebar is always visible — topbar/viewtabs always start at sidebar-width */

/* ═══════════════════════════════════════════════════════════════════════════
   SIDEBAR — monday.com #1c1f3b dark navy
═══════════════════════════════════════════════════════════════════════════ */

[data-testid="stSidebar"] {
  display: block !important;
  transform: translateX(0) !important;
  visibility: visible !important;
  opacity: 1 !important;
  position: fixed !important;
  left: 0 !important;
  top: 0 !important;
  height: 100vh !important;
  z-index: 999 !important;
  background: var(--bg-surface) !important;
  border-right: 1px solid var(--border-default) !important;
  width: var(--sidebar-width) !important;
  min-width: var(--sidebar-width) !important;
  transition: width 200ms ease, transform 200ms ease !important;
}

/* Collapsed state: slide out */
[data-testid="stSidebar"].sidebar-collapsed {
  transform: translateX(calc(-1 * var(--sidebar-width))) !important;
  width: 0 !important;
  min-width: 0 !important;
  overflow: hidden !important;
}

[data-testid="stSidebar"] > div,
[data-testid="stSidebarContent"] {
  background: var(--bg-surface) !important;
}

[data-testid="stSidebar"] > div:first-child {
  width: var(--sidebar-width) !important;
  min-width: var(--sidebar-width) !important;
  max-width: var(--sidebar-width) !important;
  overflow-y: auto !important;
  height: 100vh !important;
}

[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown span,
[data-testid="stSidebar"] .stCaption p,
[data-testid="stSidebar"] label {
  color: var(--text-secondary) !important;
  font-size: 13px !important;
}
[data-testid="stSidebar"] strong, [data-testid="stSidebar"] b { color: var(--text-primary) !important; }
[data-testid="stSidebar"] hr { border-color: var(--border-subtle) !important; margin: 5px 0 !important; }

/* Sidebar nav buttons — compact 32px rows, left-aligned */
[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: none !important;
  color: var(--text-secondary) !important;
  border-radius: 6px !important;
  text-align: left !important;
  justify-content: flex-start !important;
  font-size: 13px !important;
  font-weight: 400 !important;
  padding: 5px 10px !important;
  height: 32px !important;
  min-height: 32px !important;
  transition: background var(--motion-fast) var(--ease-out),
              color var(--motion-fast) var(--ease-out) !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--bg-overlay) !important;
  color: var(--text-primary) !important;
}

/* ── Active nav item: marker div → sibling button highlight ── */
[data-testid="stSidebar"] div:has(.sw-nav.sw-active) + div .stButton > button {
  background: rgba(26,183,56,0.16) !important;
  color: var(--text-primary) !important;
  font-weight: 500 !important;
}

/* ── Section header buttons — slightly heavier, spaced top ── */
[data-testid="stSidebar"] div:has(.sw-sec) + div .stButton > button {
  color: var(--text-secondary) !important;
  font-weight: 500 !important;
  height: 34px !important;
  min-height: 34px !important;
  margin-top: 2px !important;
}

/* ── Indented sub-items ── */
[data-testid="stSidebar"] div:has(.sw-i1) + div .stButton > button {
  padding-left: 22px !important;
}
[data-testid="stSidebar"] div:has(.sw-i2) + div .stButton > button {
  padding-left: 36px !important;
  font-size: 12px !important;
  height: 30px !important;
  min-height: 30px !important;
}

/* Active + indented combinations */
[data-testid="stSidebar"] div:has(.sw-nav.sw-active.sw-i1) + div .stButton > button {
  padding-left: 22px !important;
}
[data-testid="stSidebar"] div:has(.sw-nav.sw-active.sw-i2) + div .stButton > button {
  padding-left: 36px !important;
  font-size: 12px !important;
}

/* Primary buttons in sidebar (Save) */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: linear-gradient(180deg,#1AB738 0%,#149A2E 100%) !important;
  color: #04140A !important;
  border: 1px solid rgba(26,183,56,0.60) !important;
  font-weight: 600 !important;
  border-radius: 6px !important;
  height: auto !important;
  min-height: 32px !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
  background: linear-gradient(180deg,#22D344 0%,#18B135 100%) !important;
}
[data-testid="stSidebar"] .stButton > button:disabled {
  color: var(--text-disabled) !important; background: transparent !important; opacity: 1 !important;
}
[data-testid="stSidebar"] .stButton > button *,
[data-testid="stSidebar"] button[data-testid^="stBaseButton"] *,
[data-testid="stSidebar"] button[data-testid^="stBaseButton"] [data-testid="stMarkdownContainer"] {
  background: transparent !important; background-color: transparent !important; color: inherit !important;
}
[data-testid="stSidebar"] .stTextInput > div > div > input {
  background: var(--bg-input) !important; color: var(--text-primary) !important;
  border: 1px solid var(--border-default) !important; font-size: 12px !important;
  border-radius: 6px !important; min-height: 32px !important;
}
[data-testid="stSidebar"] .stSelectbox > div[data-baseweb="select"] > div {
  background: var(--bg-input) !important; border: 1px solid var(--border-default) !important;
  border-radius: 6px !important; min-height: 32px !important;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
  color: var(--text-muted) !important; font-size: 10px !important;
  text-transform: uppercase !important; letter-spacing: 0.08em !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   FIXED TOPBAR — monday.com board header
═══════════════════════════════════════════════════════════════════════════ */
.monday-topbar {
  position: fixed;
  top: 0;
  left: var(--sidebar-width);
  right: 0;
  height: var(--topbar-height);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  padding: 0 16px;
  z-index: 999;
  gap: 8px;
  font-family: 'Figtree', sans-serif;
  box-shadow: 0 1px 4px rgba(0,0,0,0.25);
}
.monday-board-icon {
  width: 26px; height: 26px;
  border-radius: 6px;
  background: var(--green-dim);
  border: 1px solid var(--border-accent);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px;
  flex-shrink: 0;
}
.monday-board-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 280px;
}
.monday-board-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}
.monday-topbar-divider {
  width: 1px; height: 20px;
  background: var(--border-default);
  margin: 0 2px;
  flex-shrink: 0;
}
.monday-topbar-actions {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-left: auto;
}
.monday-action-btn {
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-family: 'Figtree', sans-serif;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  cursor: pointer;
  display: inline-flex; align-items: center; gap: 4px;
  transition: all 100ms var(--ease-out);
  white-space: nowrap;
  text-decoration: none;
}
.monday-action-btn:hover {
  background: var(--bg-overlay);
  color: var(--text-primary);
  border-color: rgba(255,255,255,0.20);
}
.monday-action-btn.green {
  background: var(--green);
  color: #04140A;
  border-color: rgba(26,183,56,0.60);
  font-weight: 600;
}
.monday-action-btn.green:hover { background: var(--green-hover); }

.monday-notif-btn {
  position: relative;
  width: 30px; height: 30px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
  transition: background 100ms;
  flex-shrink: 0;
}
.monday-notif-btn:hover { background: var(--bg-overlay); color: var(--text-primary); }
.monday-notif-badge {
  position: absolute;
  top: 1px; right: 1px;
  background: var(--danger);
  color: white;
  border-radius: 50%;
  min-width: 15px; height: 15px;
  font-size: 9px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  border: 2px solid var(--bg-surface);
  line-height: 1;
  padding: 0 2px;
}
.monday-notif-badge.info { background: var(--info); }

.monday-status-pill {
  display: inline-flex; align-items: center;
  height: 18px; padding: 0 7px;
  border-radius: 9px;
  font-size: 10px; font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.monday-avatar {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1AB738, #0f8c28);
  color: #04140A;
  font-size: 10px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  border: 2px solid rgba(26,183,56,0.35);
  letter-spacing: 0.02em;
}

/* ═══════════════════════════════════════════════════════════════════════════
   VIEW TABS BAR — monday.com views strip
═══════════════════════════════════════════════════════════════════════════ */
.monday-view-tabs {
  position: fixed;
  top: var(--topbar-height);
  left: var(--sidebar-width);
  right: 0;
  height: var(--viewtab-height);
  background: var(--bg-base);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  padding: 0 12px;
  z-index: 998;
  gap: 0;
  overflow-x: auto;
  overflow-y: hidden;
  font-family: 'Figtree', sans-serif;
}
.monday-view-tabs::-webkit-scrollbar { height: 0; }
.monday-view-tab {
  display: inline-flex; align-items: center; gap: 5px;
  height: var(--viewtab-height);
  padding: 0 12px;
  font-size: 13px;
  font-weight: 400;
  color: var(--text-muted);
  cursor: pointer;
  border-bottom: 3px solid transparent;
  margin-bottom: 0;
  white-space: nowrap;
  transition: color 100ms, border-color 100ms;
  user-select: none;
  text-decoration: none;
  flex-shrink: 0;
}
.monday-view-tab:hover {
  color: var(--text-secondary);
  background: rgba(255,255,255,0.025);
}
.monday-view-tab.active {
  color: var(--text-primary);
  border-bottom-color: var(--green);
  font-weight: 500;
}
.monday-view-tab-icon { font-size: 13px; opacity: 0.7; }
.monday-view-tab-sep {
  width: 1px; height: 16px;
  background: var(--border-subtle);
  margin: 0 4px;
  flex-shrink: 0;
}
.monday-view-tab-add {
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: var(--viewtab-height);
  color: var(--text-muted);
  font-size: 18px; font-weight: 300;
  cursor: pointer;
  transition: color 100ms;
  flex-shrink: 0;
}
.monday-view-tab-add:hover { color: var(--text-secondary); }

/* ═══════════════════════════════════════════════════════════════════════════
   DIALOGS / MODALS
═══════════════════════════════════════════════════════════════════════════ */
[data-baseweb="dialog"], [data-baseweb="dialog"] > div,
div[role="dialog"], div[role="dialog"] > div,
[data-testid="stModal"], [data-testid="stModal"] > div {
  background: var(--bg-elevated) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 10px !important;
  box-shadow: 0 1px 0 rgba(255,255,255,0.04) inset, 0 20px 60px rgba(0,0,0,0.60) !important;
}
[data-baseweb="dialog"] [data-baseweb="block"] { background: var(--bg-elevated) !important; }
[data-baseweb="dialog"] p, [data-baseweb="dialog"] span, [data-baseweb="dialog"] label,
div[role="dialog"] p, div[role="dialog"] span, div[role="dialog"] label,
div[role="dialog"] .stMarkdown p { color: var(--text-secondary) !important; font-size: 13px !important; }
[data-baseweb="dialog"] input, [data-baseweb="dialog"] textarea,
div[role="dialog"] input, div[role="dialog"] textarea {
  background: var(--bg-input) !important; color: var(--text-primary) !important;
  border: 1px solid var(--border-default) !important;
}
div[role="dialog"] .stButton > button {
  background: rgba(255,255,255,0.05) !important; color: var(--text-primary) !important;
  border: 1px solid var(--border-default) !important; border-radius: 6px !important; font-size: 13px !important;
}
div[role="dialog"] .stButton > button:hover {
  background: rgba(255,255,255,0.09) !important; border-color: rgba(255,255,255,0.22) !important;
}
div[role="dialog"] button[data-testid="stBaseButton-primary"],
div[role="dialog"] .stButton > button[kind="primary"] {
  background: linear-gradient(180deg,#1AB738 0%,#149A2E 100%) !important;
  border: 1px solid rgba(26,183,56,0.60) !important; color: #04140A !important; font-weight: 600 !important;
}
div[role="dialog"] button[data-testid^="stBaseButton"] *,
div[role="dialog"] .stButton > button * { background: transparent !important; color: inherit !important; }
div[role="dialog"] hr { border-color: var(--border-subtle) !important; }
div[role="dialog"] .stCaption p { color: var(--text-muted) !important; }
div[role="dialog"] label p,
div[role="dialog"] [data-testid="stWidgetLabel"] p { color: var(--text-secondary) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   SCROLLBAR
═══════════════════════════════════════════════════════════════════════════ */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.10); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.18); }

/* ═══════════════════════════════════════════════════════════════════════════
   UTILITY CLASSES
═══════════════════════════════════════════════════════════════════════════ */
.sw-eyebrow {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 10px !important; font-weight: 600 !important;
  text-transform: uppercase !important; letter-spacing: 0.12em !important;
  color: var(--text-muted) !important;
}
</style>
""", unsafe_allow_html=True)
