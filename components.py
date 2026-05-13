"""
Shared UI components for Payroll Ops Streamlit tools.
Provides consistent styling, alerts, headers, and table helpers.
"""
import streamlit as st

# ---------------------------------------------------------------------------
# Design Tokens
# ---------------------------------------------------------------------------
COLORS = {
    "cyan":    "#00e5ff",
    "green":   "#06ffa5",
    "yellow":  "#ffbe0b",
    "magenta": "#ff006e",
    "purple":  "#8338ec",
    "blue":    "#2563eb",
    "muted":   "#8a9bb0",
    "amber":   "#b45309",
    "amber_bg": "#fffbeb",
}

ALERT_CONFIG = {
    "ok":   {"color": "#06ffa5", "bg": "rgba(6,255,165,0.08)",   "shadow": "rgba(6,255,165,0.12)"},
    "warn": {"color": "#ffbe0b", "bg": "rgba(255,190,11,0.08)",  "shadow": "rgba(255,190,11,0.12)"},
    "info": {"color": "#00e5ff", "bg": "rgba(0,229,255,0.06)",   "shadow": "none"},
    "err":  {"color": "#ff006e", "bg": "rgba(255,0,110,0.08)",   "shadow": "rgba(255,0,110,0.12)"},
}


# ---------------------------------------------------------------------------
# Shared CSS — call once per app at the top
# ---------------------------------------------------------------------------
def inject_global_css(prefix: str, accent_color: str = "#00e5ff"):
    """Inject shared CSS for alerts and number input cleanup. Call once at app start."""
    alert_css = ""
    for atype, cfg in ALERT_CONFIG.items():
        shadow = f"box-shadow: 0 0 15px {cfg['shadow']};" if cfg["shadow"] != "none" else ""
        alert_css += (
            f".{prefix}-alert-{atype} {{ background: {cfg['bg']}; "
            f"border-left: 3px solid {cfg['color']}; {shadow} }}\n"
        )

    st.markdown(f"""
<style>
button[data-testid="stNumberInputStepUp"],
button[data-testid="stNumberInputStepDown"] {{ display: none !important; }}
.{prefix}-alert {{ padding: 12px 18px; border-radius: 8px; margin: 12px 0; }}
{alert_css}
.{prefix}-alert-label {{ font-weight: 700; font-size: 0.82rem; letter-spacing: 0.08em; }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Header with shimmer animation
# ---------------------------------------------------------------------------
def render_header(prefix: str, title: str, subtitle: str, accent_color: str = "#00e5ff",
                  secondary_color: str = "#ff006e", icon: str = ""):
    """Render the animated gradient header used by automation tools."""
    st.markdown(f"""
<style>
.{prefix}-header {{
    background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #16213e 100%);
    padding: 26px 30px; border-radius: 14px; margin-bottom: 22px;
    border: 1px solid {_rgba(accent_color, 0.3)};
    box-shadow: 0 0 30px {_rgba(accent_color, 0.15)}, inset 0 0 20px rgba(131, 56, 236, 0.08);
    position: relative; overflow: hidden;
}}
.{prefix}-header::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, {accent_color}, {secondary_color}, #8338ec, transparent);
    background-size: 200% 100%; animation: {prefix}shimmer 4s infinite linear;
}}
@keyframes {prefix}shimmer {{
    0%   {{ background-position: 200% 0; }}
    100% {{ background-position: -200% 0; }}
}}
.{prefix}-header h1 {{
    margin: 0; color: {accent_color}; font-size: 1.55rem; font-weight: 700;
    letter-spacing: 0.05em; text-shadow: 0 0 20px {_rgba(accent_color, 0.4)};
}}
.{prefix}-header p {{ margin: 6px 0 0 0; color: #8a9bb0; font-size: 0.85rem; letter-spacing: 0.12em; }}
</style>
<div class="{prefix}-header">
    <h1>{icon}  {title}</h1>
    <p>{subtitle}</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Alert component
# ---------------------------------------------------------------------------
def render_alert(prefix: str, alert_type: str, label: str, message: str):
    """
    Render a styled alert box.
    alert_type: 'ok', 'warn', 'info', or 'err'
    """
    color = ALERT_CONFIG[alert_type]["color"]
    st.markdown(f"""
<div class="{prefix}-alert {prefix}-alert-{alert_type}">
    <span class="{prefix}-alert-label" style="color:{color};">{label}</span>
    <div style="color:#c5d1e0; font-size:0.85rem; margin-top:4px;">{message}</div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Validation warning box (used by payroll/FICA tools)
# ---------------------------------------------------------------------------
def render_validation_warning(title: str, items: list[str]):
    """Render an amber warning box with a list of validation issues."""
    items_html = "".join(
        f'<p style="margin:4px 0; font-size:0.9rem; color:#b45309;">&#9888; {item}</p>'
        for item in items
    )
    st.markdown(
        f'<div style="background:#fffbeb; border-left:3px solid #b45309; '
        f'padding:10px 14px; border-radius:4px; margin-bottom:8px;">'
        f'<p style="margin:0 0 6px 0; font-size:0.85rem; font-weight:600; color:#b45309;">{title}</p>'
        f'{items_html}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Breakdown table (Item / Amount)
# ---------------------------------------------------------------------------
def render_breakdown_table(rows: list[tuple[str, str, bool]]):
    """
    Render an Item/Amount breakdown table.
    rows: list of (label, formatted_amount, is_bold)
    """
    html = (
        '<table style="width:100%; border-collapse:collapse; font-family:inherit; font-size:1rem;">'
        '<thead><tr style="border-bottom:2px solid #ccc;">'
        '<th style="text-align:left; padding:6px 4px; font-weight:600;">Item</th>'
        '<th style="text-align:right; padding:6px 8px; font-weight:600;">Amount</th>'
        '</tr></thead><tbody>'
    )
    for label, amount, bold in rows:
        amt_str = f"<b>{amount}</b>" if bold else amount
        lbl_str = f"<b>{label}</b>" if bold else label
        html += (
            f'<tr style="border-bottom:1px solid #f0f0f0;">'
            f'<td style="padding:7px 4px;">{lbl_str}</td>'
            f'<td style="text-align:right; padding:7px 8px; font-variant-numeric:tabular-nums; '
            f'white-space:nowrap;">{amt_str}</td>'
            f'</tr>'
        )
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Copy-to-clipboard component
# ---------------------------------------------------------------------------
_COPY_BUTTON_ID = 0

def render_copyable_html(html_content: str, button_label: str = "Copy to Clipboard", height: int = 400):
    """
    Render HTML content with a copy button that copies rich HTML to clipboard.
    Jira/Confluence will preserve bold, links, and line breaks on paste.
    Content is rendered via st.markdown (links are clickable); the copy button
    is a separate stc.html iframe with the HTML embedded directly (no cross-frame access).
    """
    global _COPY_BUTTON_ID
    _COPY_BUTTON_ID += 1
    container_id = f"copyable-{_COPY_BUTTON_ID}"

    import base64 as _b64
    _encoded_html = _b64.b64encode(html_content.encode()).decode()

    st.markdown(f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         font-size: 14px; line-height: 1.8; border: 1px solid #3a4560; border-radius: 8px;
         padding: 16px; background: #0d1225; color: #e2e8f0; margin-bottom: 4px;">
        {html_content}
    </div>""", unsafe_allow_html=True)

    import streamlit.components.v1 as stc
    stc.html(f"""
<button id="btn-{container_id}" onclick="copyContent_{_COPY_BUTTON_ID}()" style="
    padding: 8px 18px; font-size: 0.85rem; font-weight: 600;
    background: #f0f2f6; border: 1px solid #d1d5db; border-radius: 6px;
    cursor: pointer; color: #374151; letter-spacing: 0.02em;
    transition: background 0.15s;">
    {button_label}
</button>
<script>
function copyContent_{_COPY_BUTTON_ID}() {{
    const raw = atob("{_encoded_html}");
    const tmp = document.createElement("div");
    tmp.innerHTML = raw;
    const plain = tmp.innerText;
    const blob = new Blob([raw], {{type: "text/html"}});
    const plainBlob = new Blob([plain], {{type: "text/plain"}});
    const item = new ClipboardItem({{"text/html": blob, "text/plain": plainBlob}});
    navigator.clipboard.write([item]).then(() => {{
        const btn = document.getElementById("btn-{container_id}");
        btn.textContent = "Copied!";
        btn.style.background = "#d1fae5";
        btn.style.borderColor = "#06ffa5";
        setTimeout(() => {{
            btn.textContent = "{button_label}";
            btn.style.background = "#f0f2f6";
            btn.style.borderColor = "#d1d5db";
        }}, 1500);
    }});
}}
</script>
""", height=50, scrolling=False)


# ---------------------------------------------------------------------------
# CS Tools summary block (used by payroll ops calculator)
# ---------------------------------------------------------------------------
def render_cs_tools_summary(header_html: str, lines: list[str]):
    """
    Render a CS Tools adjustment summary block.
    header_html: the clickable/bold header line
    lines: list of HTML strings for each detail line (e.g., "Employee Credit: $X on DATE")
    """
    body = "<br>".join(lines)
    st.markdown(
        f'<div style="font-size:0.9rem; line-height:1.8;">'
        f'<p style="margin:0 0 8px 0; line-height:1.4;">{header_html}<br>{body}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Dashboard CSS (KPI cards, section dividers, viz header)
# ---------------------------------------------------------------------------
def inject_dashboard_css(prefix: str = "viz"):
    """Inject CSS classes for dashboard KPI cards and section dividers."""
    st.markdown(f"""
<style>
.{prefix}-header {{
    background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #16213e 100%);
    padding: 26px 30px; border-radius: 14px; margin-bottom: 22px;
    border: 1px solid rgba(0, 229, 255, 0.3);
    box-shadow: 0 0 30px rgba(0, 229, 255, 0.15), inset 0 0 20px rgba(131, 56, 236, 0.08);
    position: relative; overflow: hidden;
}}
.{prefix}-header::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #00e5ff, #ff006e, #8338ec, transparent);
    background-size: 200% 100%; animation: {prefix}shimmer 4s infinite linear;
}}
@keyframes {prefix}shimmer {{
    0%   {{ background-position: 200% 0; }}
    100% {{ background-position: -200% 0; }}
}}
.{prefix}-header h1 {{
    margin: 0; color: #00e5ff; font-size: 1.55rem; font-weight: 700;
    letter-spacing: 0.05em; text-shadow: 0 0 20px rgba(0, 229, 255, 0.4);
}}
.{prefix}-header p {{ margin: 6px 0 0 0; color: #8a9bb0; font-size: 0.85rem; letter-spacing: 0.12em; }}
.kpi-card {{
    background: linear-gradient(135deg, rgba(10, 15, 30, 0.95) 0%, rgba(22, 33, 62, 0.95) 100%);
    border-radius: 10px; padding: 16px 18px; position: relative; overflow: hidden;
}}
.kpi-label {{ color: #8a9bb0; font-size: 0.68rem; letter-spacing: 0.14em; font-weight: 700; text-transform: uppercase; }}
.kpi-value {{ font-size: 1.3rem; font-weight: 700; margin: 6px 0 2px 0; font-variant-numeric: tabular-nums; }}
.kpi-sub {{ color: #64748b; font-size: 0.72rem; }}
.{prefix}-section {{
    background: linear-gradient(135deg, rgba(10,15,30,0.95), rgba(22,33,62,0.95));
    border-radius: 10px; padding: 12px 18px; margin: 18px 0 12px 0;
}}
.{prefix}-section-label {{ font-size: 0.75rem; letter-spacing: 0.16em; font-weight: 700; }}
</style>
""", unsafe_allow_html=True)


def kpi_card_html(label: str, value: str, color: str, sub: str = "") -> str:
    """Return KPI card HTML string (for use with col.markdown())."""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="kpi-card" style="border:1px solid {color}44; box-shadow:0 0 20px {color}22, inset 0 0 30px {color}0e;">'
        f'<div style="position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg, transparent, {color}, transparent);"></div>'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="color:{color}; text-shadow:0 0 14px {color}66;">{value}</div>'
        f'{sub_html}</div>'
    )


def render_kpi_card(label: str, value: str, color: str, sub: str = ""):
    """Render a single KPI card with accent color glow (calls st.markdown directly)."""
    st.markdown(kpi_card_html(label, value, color, sub), unsafe_allow_html=True)


def render_section_divider(prefix: str, label: str, color: str = "#00e5ff"):
    """Render a styled section divider with label."""
    st.markdown(f"""
<div class="{prefix}-section" style="border-left: 3px solid {color}; box-shadow: 0 0 15px {_rgba(color, 0.15)};">
    <div class="{prefix}-section-label" style="color:{color};">{label}</div>
</div>
""", unsafe_allow_html=True)


def render_dashboard_header(prefix: str, title: str, subtitle: str):
    """Render the dashboard viz header."""
    st.markdown(f"""
<div class="{prefix}-header">
    <h1>{title}</h1>
    <p>{subtitle}</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Enterprise Auth Screen
# ---------------------------------------------------------------------------
def render_auth_screen(app_name: str, password: str, accent_color: str = "#00e5ff") -> bool:
    """Render branded auth gate. Returns True if authenticated, calls st.stop() otherwise."""
    if st.session_state.get("authenticated"):
        return True

    st.markdown(f"""
<style>
.auth-container {{
    max-width: 420px; margin: 80px auto; padding: 40px 36px; border-radius: 16px;
    background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #16213e 100%);
    border: 1px solid {_rgba(accent_color, 0.3)};
    box-shadow: 0 0 40px {_rgba(accent_color, 0.12)}, inset 0 0 30px rgba(131,56,236,0.06);
    position: relative; overflow: hidden;
}}
.auth-container::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, {accent_color}, #ff006e, #8338ec, transparent);
    background-size: 200% 100%; animation: authshimmer 4s infinite linear;
}}
@keyframes authshimmer {{ 0% {{ background-position: 200% 0; }} 100% {{ background-position: -200% 0; }} }}
.auth-brand {{ color: {accent_color}; font-size: 1.4rem; font-weight: 700; letter-spacing: 0.06em;
    text-align: center; margin-bottom: 6px; text-shadow: 0 0 20px {_rgba(accent_color, 0.4)}; }}
.auth-sub {{ color: #8a9bb0; font-size: 0.78rem; text-align: center; letter-spacing: 0.14em;
    margin-bottom: 28px; text-transform: uppercase; }}
</style>
<div class="auth-container">
    <div class="auth-brand">{app_name}</div>
    <div class="auth-sub">PAYROLL OPS SUITE</div>
</div>
""", unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        pwd = st.text_input("Password", type="password", label_visibility="collapsed",
                            placeholder="Enter password...")
        if st.button("Sign In", type="primary", use_container_width=True):
            if pwd == password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                render_alert("auth", "err", "ACCESS DENIED", "Incorrect password. Try again.")
    st.stop()
    return False


# ---------------------------------------------------------------------------
# Branded Sidebar
# ---------------------------------------------------------------------------
def render_app_sidebar(app_name: str, version: str, accent_color: str = "#00e5ff",
                       quick_actions: list = None):
    """Render branded sidebar with version badge and quick actions."""
    with st.sidebar:
        st.markdown(f"""
<div style="margin-bottom: 16px;">
    <span style="color:{accent_color}; font-size:0.9rem; font-weight:700; letter-spacing:0.08em;
        text-shadow: 0 0 12px {_rgba(accent_color, 0.4)};">{app_name.upper()}</span>
    <span style="display:inline-block; margin-left:8px; padding:2px 8px; font-size:0.65rem;
        font-weight:700; letter-spacing:0.1em; border-radius:10px; color:{accent_color};
        border:1px solid {_rgba(accent_color, 0.5)};
        background:{_rgba(accent_color, 0.08)};">{version}</span>
</div>
""", unsafe_allow_html=True)
        st.markdown("---")
        if quick_actions:
            for action in quick_actions:
                btn_type = action.get("type", "secondary")
                if st.button(action["label"], key=action.get("key", action["label"]),
                             type=btn_type, use_container_width=True):
                    if action.get("callback"):
                        action["callback"]()
        st.markdown("---")
        st.markdown(
            '<p style="color:#64748b; font-size:0.7rem; letter-spacing:0.12em; '
            'text-transform:uppercase; margin-top:20px;">Payroll Ops Suite</p>',
            unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Step Progress Indicator
# ---------------------------------------------------------------------------
def render_step_progress(prefix: str, steps: list, current: int, accent_color: str = "#00e5ff"):
    """
    Render horizontal step progress.
    steps: list of {"label": str, "complete": bool}
    current: 0-indexed active step
    """
    n = len(steps)
    circles = ""
    for i, step in enumerate(steps):
        if step.get("complete"):
            bg = accent_color
            border = accent_color
            content = "&#10003;"
            text_color = "#0a0e27"
            label_color = accent_color
        elif i == current:
            bg = _rgba(accent_color, 0.15)
            border = accent_color
            content = str(i + 1)
            text_color = accent_color
            label_color = accent_color
        else:
            bg = "transparent"
            border = "#3a4560"
            content = str(i + 1)
            text_color = "#3a4560"
            label_color = "#3a4560"

        pulse = f"animation: {prefix}pulse 2s infinite ease-in-out;" if i == current and not step.get("complete") else ""
        circles += f"""
        <div style="display:flex; flex-direction:column; align-items:center; flex:1; position:relative;">
            <div style="width:32px; height:32px; border-radius:50%; background:{bg};
                border:2px solid {border}; display:flex; align-items:center; justify-content:center;
                font-size:0.75rem; font-weight:700; color:{text_color}; {pulse}
                box-shadow: {f'0 0 12px {_rgba(accent_color, 0.3)}' if step.get('complete') or i == current else 'none'};
                z-index:1;">
                {content}
            </div>
            <span style="font-size:0.68rem; color:{label_color}; margin-top:6px; font-weight:600;
                letter-spacing:0.04em; text-align:center; white-space:nowrap;">{step['label']}</span>
        </div>"""

    line_segments = ""
    for i in range(n - 1):
        color = accent_color if steps[i].get("complete") else "#3a4560"
        left_pct = (100 / (n - 1)) * i + (50 / (n - 1))
        width_pct = 100 / (n - 1) - (100 / (n - 1) * 0.4)
        line_segments += (
            f'<div style="position:absolute; top:16px; left:{left_pct}%; '
            f'width:{width_pct}%; height:2px; background:{color};"></div>'
        )

    st.markdown(f"""<style>
@keyframes {prefix}pulse {{
    0%, 100% {{ box-shadow: 0 0 8px {_rgba(accent_color, 0.3)}; }}
    50% {{ box-shadow: 0 0 20px {_rgba(accent_color, 0.6)}; }}
}}
</style>""", unsafe_allow_html=True)

    st.markdown(f"""<div style="display:flex; align-items:flex-start; justify-content:space-between; padding:16px 10px 24px 10px; position:relative; margin-bottom:12px;">{line_segments}{circles}</div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Metric Row (KPI cards in columns)
# ---------------------------------------------------------------------------
def render_metric_row(metrics: list):
    """
    Render a row of KPI cards.
    metrics: list of {"label": str, "value": str, "color": str, "sub": str (optional)}
    """
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        col.markdown(
            kpi_card_html(m["label"], m["value"], m["color"], m.get("sub", "")),
            unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page Config (standardized)
# ---------------------------------------------------------------------------
def page_config(title: str, icon: str = ""):
    """Standardized page config for all tools in the suite."""
    st.set_page_config(
        page_title=f"{title} | Payroll Ops",
        layout="wide",
        page_icon=icon or None,
        initial_sidebar_state="expanded",
    )


# ---------------------------------------------------------------------------
# Results Table with Status Badges
# ---------------------------------------------------------------------------
_STATUS_COLORS = {
    "ok": ("#06ffa5", "rgba(6,255,165,0.12)"),
    "success": ("#06ffa5", "rgba(6,255,165,0.12)"),
    "not_found": ("#ffbe0b", "rgba(255,190,11,0.12)"),
    "error": ("#ff006e", "rgba(255,0,110,0.12)"),
    "failed": ("#ff006e", "rgba(255,0,110,0.12)"),
    "pending": ("#8a9bb0", "rgba(138,155,176,0.12)"),
}


def _status_badge(status: str) -> str:
    """Return HTML for a colored status pill."""
    s = status.lower().strip() if status else "pending"
    color, bg = _STATUS_COLORS.get(s, ("#8a9bb0", "rgba(138,155,176,0.12)"))
    label = s.replace("_", " ").upper()
    return (f'<span style="display:inline-block; padding:2px 10px; border-radius:10px; '
            f'font-size:0.7rem; font-weight:700; letter-spacing:0.06em; color:{color}; '
            f'background:{bg}; border:1px solid {_rgba(color, 0.3)};">{label}</span>')


def render_results_table(df, status_col: str = "Status", height: int = 420):
    """Render a results dataframe with colored status badges."""
    if df is None or df.empty:
        return

    header_cells = "".join(
        f'<th style="padding:8px 12px; text-align:left; font-size:0.72rem; font-weight:700; '
        f'letter-spacing:0.08em; color:#8a9bb0; text-transform:uppercase; '
        f'border-bottom:2px solid #1e2442;">{col}</th>'
        for col in df.columns
    )

    rows_html = ""
    for _, row in df.iterrows():
        cells = ""
        for col in df.columns:
            val = str(row[col]) if row[col] is not None else ""
            if col == status_col:
                cell_content = _status_badge(val)
            else:
                cell_content = val
            cells += (f'<td style="padding:8px 12px; font-size:0.82rem; color:#c5d1e0; '
                      f'border-bottom:1px solid #1e2442; white-space:nowrap;">{cell_content}</td>')
        rows_html += f'<tr style="transition:background 0.15s;">{cells}</tr>'

    st.markdown(f"""
<div style="max-height:{height}px; overflow-y:auto; border-radius:10px;
    border:1px solid #1e2442; background:rgba(10,15,30,0.6);">
<table style="width:100%; border-collapse:collapse; font-family:inherit;">
    <thead><tr>{header_cells}</tr></thead>
    <tbody>{rows_html}</tbody>
</table>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tab Activity Dots
# ---------------------------------------------------------------------------
def inject_tab_dots_css(active_tabs: list, accent_color: str = "#06ffa5"):
    """
    Inject CSS that adds a colored dot after active tab labels.
    active_tabs: list of 0-indexed tab positions that have data.
    """
    if not active_tabs:
        return
    selectors = []
    for idx in active_tabs:
        selectors.append(
            f'div[data-baseweb="tab-list"] > button:nth-child({idx + 1})::after'
        )
    selector_str = ", ".join(selectors)
    st.markdown(f"""
<style>
{selector_str} {{
    content: '';
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: {accent_color};
    margin-left: 6px;
    box-shadow: 0 0 6px {_rgba(accent_color, 0.6)};
    vertical-align: middle;
}}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _rgba(hex_color: str, alpha: float) -> str:
    """Convert hex color to rgba string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"
