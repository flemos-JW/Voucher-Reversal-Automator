"""Voucher Reversal Dashboard.

Paste a 4-column table (MID, VoucherID, SettlementDate, AdjComment), save to vouchers.csv,
copy the terminal command, run it. Mirror of the W-2C Automator dashboard.

Launch:
    python3 -m streamlit run /Users/franciscolemos/apps/voucher_reversal/voucher_dashboard.py
"""
import base64
import io
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


import pandas as pd
import streamlit as st
from components import (
    inject_global_css, render_header, render_alert, render_app_sidebar,
    render_step_progress, render_metric_row, render_section_divider,
    render_results_table, page_config,
)

SCRIPT_DIR    = Path(__file__).resolve().parent
INPUT_PATH    = SCRIPT_DIR / "vouchers.csv"
RESULTS_PATH  = SCRIPT_DIR / "results.csv"
FAILED_PATH   = SCRIPT_DIR / "failed_vouchers.csv"
RUN_SCRIPT    = SCRIPT_DIR / "voucher_run.py"

page_config("Voucher Reversal", "🔄")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def _clear_data():
    for k in list(st.session_state.keys()):
        if k != "authenticated":
            del st.session_state[k]
    st.rerun()

render_app_sidebar("Voucher Reversal", "v1.2", "#ffbe0b",
                   quick_actions=[{"label": "Clear Session", "callback": _clear_data, "key": "vr_clear"}])

with st.sidebar:
    if st.button("Install Dependencies", key="vr_install", use_container_width=True):
        with st.spinner("Installing..."):
            _r = subprocess.run(
                "pip install playwright streamlit pandas && python -m playwright install chromium",
                shell=True, capture_output=True, text=True,
            )
        if _r.returncode == 0:
            st.success("Dependencies installed!")
        else:
            st.error(f"Install failed:\n{_r.stderr[-300:]}")
    st.caption("Run once on first setup")

# ---------------------------------------------------------------------------
# Header + shared styles
# ---------------------------------------------------------------------------
inject_global_css("vr", accent_color="#ffbe0b")
render_header("vr", "VOUCHER REVERSAL AUTOMATOR",
              "PASTE TABLE · SAVE · RUN AUTOMATION",
              accent_color="#ffbe0b", secondary_color="#ff006e", icon="\U0001f504")

_guide_path = Path(__file__).resolve().parent / "Voucher_Reversal_Guide.pdf"
if _guide_path.exists():
    import streamlit.components.v1 as _stc
    with open(_guide_path, "rb") as _f:
        _pdf_b64 = base64.b64encode(_f.read()).decode()
    _stc.html(f"""
    <a href="#" id="pdf_vr" style="color:#ffbe0b; font-size:0.85rem; text-decoration:none; font-weight:600;">
    📖 Open User Guide (PDF)</a>
    <script>
    document.getElementById('pdf_vr').addEventListener('click', function(e) {{
        e.preventDefault();
        var b64 = "{_pdf_b64}";
        var bin = atob(b64);
        var arr = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
        var blob = new Blob([arr], {{type: 'application/pdf'}});
        window.open(URL.createObjectURL(blob), '_blank');
    }});
    </script>
    """, height=30)

# ---------------------------------------------------------------------------
# Step Progress
# ---------------------------------------------------------------------------
_has_data = bool(st.session_state.get("voucher_raw", "").strip())
_has_saved = bool(st.session_state.get("vr_saved_count"))
_has_results = RESULTS_PATH.exists()
steps = [
    {"label": "Paste Table", "complete": _has_data},
    {"label": "Save", "complete": _has_saved},
    {"label": "Run", "complete": _has_results},
    {"label": "Results", "complete": _has_results},
]
_current = 0
if steps[0]["complete"]:
    _current = 1
if steps[1]["complete"]:
    _current = 2
if steps[2]["complete"]:
    _current = 3
render_step_progress("vr", steps, _current, "#ffbe0b")

# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------
st.caption(
    "Expected columns: **MID**, **VoucherID**, **SettlementDate**, **AdjComment** "
    "(tab or comma separated, headers on the first line). Duplicates are auto-removed. "
    "Dates in MM/DD/YYYY format."
)

raw = st.text_area(
    "Voucher Reversal Table",
    height=340,
    placeholder=(
        "MID\tVoucherID\tSettlementDate\tAdjComment\n"
        "M123456\tV789012\t03/15/2025\tReverse per client request\n"
        "M234567\tV890123\t03/15/2025\tDuplicate payment"
    ),
    label_visibility="collapsed",
    key="voucher_raw",
)

# ---------------------------------------------------------------------------
# Parse pasted input
# ---------------------------------------------------------------------------
def _norm(s):
    return re.sub(r"[\s_]+", "", str(s).strip().lower())


def parse_paste(text):
    """Parse pasted text -> DataFrame. Returns (df, error_message)."""
    if not text.strip():
        return None, None
    first = text.splitlines()[0]
    delim = "\t" if first.count("\t") >= first.count(",") else ","
    try:
        df = pd.read_csv(io.StringIO(text), sep=delim, dtype=str).fillna("")
    except Exception as e:
        return None, f"Could not parse table: {e}"
    if df.empty:
        return None, "No rows found."

    lookup = {_norm(c): c for c in df.columns}
    mid_key = lookup.get("mid") or lookup.get("memberid")
    vid_key = lookup.get("voucherid") or lookup.get("voucher")
    sd_key  = lookup.get("settlementdate") or lookup.get("settledate") or lookup.get("settlement")
    adj_key = (lookup.get("adjcomment") or lookup.get("adjustmentcomment")
               or lookup.get("comment") or lookup.get("comments")
               or lookup.get("note") or lookup.get("notes"))

    missing = []
    if not mid_key: missing.append("MID")
    if not vid_key: missing.append("VoucherID")
    if not sd_key:  missing.append("SettlementDate")
    if not adj_key: missing.append("AdjComment")
    if missing:
        return None, f"Missing column(s): {', '.join(missing)}"

    out = pd.DataFrame({
        "MID":            df[mid_key].astype(str).str.strip(),
        "VoucherID":      df[vid_key].astype(str).str.strip(),
        "SettlementDate": df[sd_key].astype(str).str.strip(),
        "AdjComment":     df[adj_key].astype(str).str.strip(),
    })
    out = out[out["MID"].str.len() > 0]
    out = out.drop_duplicates().reset_index(drop=True)
    return out, None


parsed_df, parse_err = parse_paste(raw)

col_preview, col_save = st.columns([2.5, 1])

with col_preview:
    if parse_err:
        render_alert("vr", "err", "⚠ PARSE ERROR", parse_err)
    elif parsed_df is not None and not parsed_df.empty:
        st.caption(f"📝 **{len(parsed_df)}** unique row(s) parsed")
        st.dataframe(parsed_df, use_container_width=True, hide_index=True, height=220)
    else:
        st.caption("Paste a table above — preview will appear here.")

with col_save:
    save_disabled = parsed_df is None or parsed_df.empty
    if st.button("💾  Save to vouchers.csv",
                 type="primary",
                 use_container_width=True,
                 disabled=save_disabled):
        parsed_df.to_csv(INPUT_PATH, index=False)
        st.session_state["vr_saved_count"] = len(parsed_df)
        st.rerun()
    if save_disabled:
        st.caption("⬅ Paste valid rows first")

if st.session_state.get("vr_saved_count"):
    render_alert("vr", "ok",
                 f"✓ SAVED — {st.session_state['vr_saved_count']} row(s) written to vouchers.csv",
                 "")

# ---------------------------------------------------------------------------
# Command & Run
# ---------------------------------------------------------------------------
render_section_divider("vr", "EXECUTE", "#ffbe0b")

cmd = f"python3 {RUN_SCRIPT}"
st.code(cmd, language="bash")

st.markdown("""
<div style="color:#8a9bb0; font-size:0.82rem; line-height:1.7; margin-top:-6px;">
    1. Open a Terminal &rarr; paste the command above.<br>
    2. Chromium opens &mdash; log in via Okta Verify if needed, then press <b>Enter</b> to start.<br>
    3. Progress streams live; results save to <code>results.csv</code> after every row.
</div>
""", unsafe_allow_html=True)

st.caption("If Okta login is required, use the terminal command above instead.")
if st.button("Run Now", type="primary", use_container_width=True, key="vr_run_now"):
    _cmd = ["python3", str(RUN_SCRIPT), "--no-pause"]
    with st.spinner("Running voucher reversal automation..."):
        _proc = subprocess.run(_cmd, capture_output=True, text=True, timeout=600, cwd=str(SCRIPT_DIR))
    if _proc.returncode == 0:
        render_alert("vr", "ok", "✓ RUN COMPLETE", "Automation finished successfully. Results are below.")
    else:
        render_alert("vr", "err", "⚠ RUN FAILED", f"Exit code {_proc.returncode}. Check terminal output for details.")
    st.rerun()

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
render_section_divider("vr", "RESULTS", "#06ffa5")

if st.button("Refresh Results", key="vr_refresh"):
    st.rerun()

if not RESULTS_PATH.exists():
    render_alert("vr", "info", "NO RESULTS YET",
                 "Save rows above and run the command to populate this panel.")
else:
    _results_mtime = os.path.getmtime(RESULTS_PATH)
    _results_ago = datetime.now() - datetime.fromtimestamp(_results_mtime)
    _mins_ago = int(_results_ago.total_seconds() / 60)
    _time_str = f"{_mins_ago} min ago" if _mins_ago < 60 else f"{_mins_ago // 60}h {_mins_ago % 60}m ago"
    st.caption(f"Results from: {datetime.fromtimestamp(_results_mtime).strftime('%I:%M %p')} ({_time_str})")

    try:
        df = pd.read_csv(RESULTS_PATH, dtype=str).fillna("")
    except Exception as e:
        st.error(f"Couldn't read results.csv: {e}")
        df = None

    if df is not None and not df.empty:
        total = len(df)
        ok_n  = int((df["Status"] == "ok").sum())
        ph_n  = int((df["Status"] == "placeholder").sum()) if "Status" in df.columns else 0
        nf_n  = int((df["Status"] == "not_found").sum())
        err_n = total - ok_n - ph_n - nf_n

        render_metric_row([
            {"label": "Processed", "value": str(total), "color": "#ffbe0b"},
            {"label": "Successful", "value": str(ok_n), "color": "#06ffa5"},
            {"label": "Placeholder", "value": str(ph_n), "color": "#8a9bb0"},
            {"label": "Not Found", "value": str(nf_n), "color": "#ffbe0b"},
            {"label": "Errors", "value": str(err_n), "color": "#ff006e"},
        ])

        st.write("")
        filter_mode = st.radio(
            "Show",
            ["All", "Failures only", "Successes only"],
            horizontal=True,
            label_visibility="collapsed",
        )
        if filter_mode == "Failures only":
            display_df = df[~df["Status"].isin(["ok", "placeholder"])]
        elif filter_mode == "Successes only":
            display_df = df[df["Status"] == "ok"]
        else:
            display_df = df

        render_results_table(display_df, "Status")

        if FAILED_PATH.exists() and FAILED_PATH.stat().st_mtime >= RESULTS_PATH.stat().st_mtime:
            failed_rows = pd.read_csv(FAILED_PATH, dtype=str) if FAILED_PATH.stat().st_size else pd.DataFrame()
            if not failed_rows.empty:
                st.write("")
                render_alert("vr", "warn",
                             f"⚠ {len(failed_rows)} row(s) FAILED",
                             "Edit below to remove rows you don't want to retry.")
                edited_csv = st.text_area(
                    "Failed rows (CSV format)", value=failed_rows.to_csv(index=False),
                    height=150, key="vr_retry_edit")
                retry_cmd = f"python3 {RUN_SCRIPT} {FAILED_PATH}"
                st.code(retry_cmd, language="bash")
                st.caption("Tip: a succeeded retry overwrites its row in results.csv.")
                if st.button("Retry Now", type="primary", key="vr_retry_btn"):
                    FAILED_PATH.write_text(edited_csv)
                    _retry_cmd = ["python3", str(RUN_SCRIPT), str(FAILED_PATH), "--no-pause"]
                    with st.spinner(f"Retrying {len(failed_rows)} row(s)..."):
                        _rproc = subprocess.run(_retry_cmd, capture_output=True, text=True, timeout=600, cwd=str(SCRIPT_DIR))
                    if _rproc.returncode == 0:
                        render_alert("vr", "ok", "✓ RETRY COMPLETE", "All retried rows processed.")
                    else:
                        render_alert("vr", "err", "⚠ RETRY FAILED", f"Exit code {_rproc.returncode}.")
                    st.rerun()
    else:
        render_alert("vr", "info", "RESULTS FILE IS EMPTY", "")
