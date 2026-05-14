#!/usr/bin/env python3
"""
Voucher reversal batch runner.

Usage:
    python3 voucher_run.py [vouchers.csv] [--dry-run]

Input CSV has four columns: MID, VoucherID, SettlementDate (MM/DD/YYYY), AdjComment.
Headers are case-insensitive and tolerant of spaces/underscores.

- First run: Chromium opens, you log in with Okta + Okta Verify.
  Then press Enter in the terminal to start processing.
- Subsequent runs: session is cached in ~/.playwright-chrome-voucher so you
  won't re-authenticate until the session expires.
- Results are printed live and saved to results.csv.
"""

import csv
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def _to_iso_date(date_str: str) -> str:
    """Normalize user-entered dates to YYYY-MM-DD for the HTML date input.
    Accepts: 5/12/26, 05/12/2026, 2026-05-12, 5-12-26, etc."""
    s = (date_str or "").strip()
    if not s:
        return ""
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y",
                "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {date_str!r}")

USER_DATA_DIR = Path.home() / ".playwright-chrome-voucher"
START_URL     = "https://cstools-workforce.justworks.com/internal"
SCRIPT_DIR    = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------
def _norm(key: str) -> str:
    """Normalize a column header for matching: lower, strip, remove spaces/underscores."""
    return re.sub(r"[\s_]+", "", key.strip().lower())


def load_vouchers(path: Path) -> list:
    if not path.exists():
        sys.exit(f"Voucher list not found: {path}")

    # Accept CSV (comma) or TSV (tab) — sniff based on first line
    raw = path.read_text()
    first_line = raw.splitlines()[0] if raw.strip() else ""
    delim = "\t" if "\t" in first_line and first_line.count("\t") >= first_line.count(",") else ","

    vouchers = []
    reader = csv.DictReader(raw.splitlines(), delimiter=delim)
    if not reader.fieldnames:
        sys.exit(f"Voucher file has no header row: {path}")

    # Map actual field names → normalized names → required keys
    mid_key = vid_key = sdate_key = adj_key = None
    for fn in reader.fieldnames:
        n = _norm(fn)
        if n in ("mid", "memberid"):
            mid_key = fn
        elif n in ("voucherid", "voucher"):
            vid_key = fn
        elif n in ("settlementdate", "settledate", "settlement"):
            sdate_key = fn
        elif n in ("adjcomment", "adjustmentcomment", "comment", "comments", "note", "notes"):
            adj_key = fn

    missing = []
    if not mid_key:   missing.append("MID")
    if not vid_key:   missing.append("VoucherID")
    if not sdate_key: missing.append("SettlementDate")
    if not adj_key:   missing.append("AdjComment")
    if missing:
        sys.exit(f"Missing column(s) in {path.name}: {', '.join(missing)}")

    for row in reader:
        mid   = str(row.get(mid_key,   "") or "").strip()
        vid   = str(row.get(vid_key,   "") or "").strip()
        sdate = str(row.get(sdate_key, "") or "").strip()
        adj   = str(row.get(adj_key,   "") or "").strip()
        if not mid:
            continue
        vouchers.append({
            "mid":             mid,
            "voucher_id":      vid,
            "settlement_date": sdate,
            "adj_comment":     adj,
        })
    return vouchers


# ---------------------------------------------------------------------------
# Search & click helpers (shared pattern with w2c_automator)
# ---------------------------------------------------------------------------
def click_search_result(page, mid_up: str) -> bool:
    """Click the cstools search-result row for the given MID. Returns True
    if the click caused navigation away from the start URL."""
    url_before = page.url
    page.wait_for_timeout(400)

    # Primary: result row text like "M123456 First Last - Cxxxx" or "M123456 First Last -"
    primary = page.get_by_text(
        re.compile(rf"^{re.escape(mid_up)}\s+\S.*-\s*(?:C\d+)?\s*$")
    ).last
    try:
        primary.click(timeout=6000)
        page.wait_for_load_state("domcontentloaded", timeout=4000)
        if page.url != url_before:
            return True
    except Exception:
        pass

    for strat in (
        lambda: page.get_by_text(re.compile(rf"^{re.escape(mid_up)}\s")).last,
        lambda: page.get_by_role("link").filter(has_text=mid_up).first,
        lambda: page.get_by_role("option").filter(has_text=mid_up).first,
    ):
        if page.url != url_before:
            return True
        try:
            loc = strat()
            if loc.count() == 0:
                continue
            loc.click(timeout=3000)
            page.wait_for_load_state("domcontentloaded", timeout=4000)
        except Exception:
            pass
        if page.url != url_before:
            return True
    return page.url != url_before


# ---------------------------------------------------------------------------
# Core flow — TO BE FILLED IN AFTER CODEGEN
# ---------------------------------------------------------------------------
def reverse_voucher(page, mid: str, voucher_id: str, settlement_date: str, adj_comment: str) -> tuple:
    """Run the voucher-reversal flow for one row. Returns (status, note).

    Segments wired in:
      1. Search MID → click result → Details → Vouchers tab                 ✓
      2. Find voucher by ID → voucher Details → Reverse Voucher link        ✓
      3. Settlement date + notes + radio defaults → Confirm → Finalize      ✓
    """
    mid_up = mid.upper()

    # 1. Home page (fresh start each row) — retry once on ERR_ABORTED
    for _attempt in range(2):
        try:
            page.goto(START_URL, wait_until="domcontentloaded", timeout=15000)
            break
        except Exception:
            if _attempt == 0:
                page.wait_for_timeout(800)
                continue
            raise

    # 2. Search by MID
    search = page.get_by_role("textbox", name="Search")
    search.click()
    search.fill(mid)
    search.press("Enter")

    # 3. Click the search result → lands on the employee's diagnostic page
    if not click_search_result(page, mid_up):
        return ("not_found", "no search result for MID")

    # === SEGMENT 1 — navigate to voucher tab ===

    # 4. Click Details tile on the diagnostic page (first match)
    try:
        page.get_by_title("Details").first.click(timeout=8000)
    except Exception as e:
        return ("error_details_click", f"{type(e).__name__}: {e} @ url={page.url}")

    # 5. Click the Vouchers tab — try several selector shapes in case the
    #    cached-session DOM differs from what codegen captured.
    page.wait_for_timeout(400)  # let the Details-triggered nav settle
    _pre_click_url = page.url

    # Snapshot the page as soon as we arrive, before the click attempts.
    # Helps us see the DOM if every strategy below misses.
    try:
        _pre_shot = SCRIPT_DIR / f"debug_prevouchers_{mid_up}.png"
        page.screenshot(path=str(_pre_shot), full_page=True)
    except Exception:
        _pre_shot = None

    vouchers_strategies = [
        lambda: page.get_by_role("tab",    name=" Vouchers"),
        lambda: page.get_by_role("tab",    name="Vouchers"),
        lambda: page.get_by_role("tab",    name=re.compile(r"vouchers", re.IGNORECASE)),
        lambda: page.get_by_role("link",   name=re.compile(r"vouchers", re.IGNORECASE)),
        lambda: page.get_by_role("button", name=re.compile(r"vouchers", re.IGNORECASE)),
        # Last resort: literal text
        lambda: page.get_by_text(re.compile(r"^\s*Vouchers\s*$", re.IGNORECASE)).first,
    ]
    vouchers_clicked = False
    last_err = None
    for strat in vouchers_strategies:
        try:
            loc = strat()
            if loc.count() == 0:
                continue
            loc.first.click(timeout=3000)
            vouchers_clicked = True
            break
        except Exception as e:
            last_err = e
            continue

    if not vouchers_clicked:
        shot_hint = f" (pre-click snapshot: {_pre_shot.name})" if _pre_shot else ""
        return ("error_vouchers_tab_click",
                f"no Vouchers tab/link/button matched @ url={_pre_click_url}"
                f"{shot_hint} · last={last_err}")

    # Give the voucher list a beat to render before segment 2 starts scanning
    page.wait_for_timeout(800)

    # === SEGMENT 2 — find voucher by ID and click Reverse ===

    # 6. Find the row whose text contains the voucher_id and click its Details.
    #    .first (codegen default) would click the top voucher on the page; we
    #    must scope to the row matching this specific voucher_id.
    voucher_row = None
    for row_selector in ("tr", "[role='row']"):
        rows = page.locator(row_selector).filter(
            has_text=re.compile(rf"\b{re.escape(voucher_id)}\b")
        )
        count = rows.count()
        if count == 0:
            continue
        for i in range(count):
            cand = rows.nth(i)
            try:
                if cand.get_by_title("Details").count() == 0:
                    continue
            except Exception:
                continue
            voucher_row = cand
            break
        if voucher_row is not None:
            break

    if voucher_row is None:
        # Fallback — walk up from the voucher_id text to the nearest ancestor
        # that contains a Details element
        try:
            anchor    = page.get_by_text(
                re.compile(rf"\b{re.escape(voucher_id)}\b")
            ).first
            container = anchor.locator(
                "xpath=ancestor::*[.//*[@title='Details']][1]"
            )
            if container.count() > 0:
                voucher_row = container
        except Exception:
            voucher_row = None

    if voucher_row is None:
        try:
            shot = SCRIPT_DIR / f"debug_voucher_notfound_{mid_up}_{voucher_id}.png"
            page.screenshot(path=str(shot), full_page=True)
        except Exception:
            pass
        return ("error_voucher_not_found",
                f"voucher_id={voucher_id} not located on vouchers list "
                f"@ url={page.url} (see debug_voucher_notfound_*.png)")

    try:
        voucher_row.get_by_title("Details").first.click(timeout=8000)
    except Exception as e:
        return ("error_voucher_details_click",
                f"{type(e).__name__}: {e} @ url={page.url}")

    page.wait_for_timeout(400)  # let the voucher detail view render

    # 7. Click "Reverse Voucher" link
    try:
        page.get_by_role(
            "link",
            name=re.compile(r"Reverse\s*Voucher", re.IGNORECASE),
        ).first.click(timeout=8000)
    except Exception as e:
        return ("error_reverse_click", f"{type(e).__name__}: {e} @ url={page.url}")

    # Give the reversal form a beat to render before segment 3 starts
    page.wait_for_timeout(800)

    # === SEGMENT 3 — fill form + confirm ===

    # 8. Convert settlement date into the ISO format the <input type="date"> expects
    try:
        iso_date = _to_iso_date(settlement_date)
    except ValueError as e:
        return ("error_bad_settlement_date", f"{e}")

    # 9. Fill Settlement Date
    try:
        page.get_by_role("textbox", name="Settlement date").fill(iso_date)
    except Exception as e:
        return ("error_settlement_date_fill", f"{type(e).__name__}: {e} @ url={page.url}")

    # 10. Fill Voucher reversal notes with the per-row AdjComment
    try:
        notes = page.get_by_role("textbox", name="Voucher reversal notes")
        notes.click()
        notes.fill(adj_comment)
    except Exception as e:
        return ("error_notes_fill", f"{type(e).__name__}: {e} @ url={page.url}")

    # 11. Radio-button defaults captured by codegen — hardcoded per operator preference:
    #     revert net pay to member?     → No
    #     manually settle?              → Yes
    #     allow prev quarters?          → Yes
    try:
        page.locator("#revert-net-pay-no").check(timeout=5000)
        page.locator("#manually-settle-yes").check(timeout=5000)
        page.locator("#allow-prev-quarters-yes").check(timeout=5000)
    except Exception as e:
        return ("error_radio_check", f"{type(e).__name__}: {e} @ url={page.url}")

    # 12. Two-step confirmation — any confirm() dialogs get auto-accepted.
    page.on("dialog", lambda d: d.accept())

    try:
        page.get_by_role("button", name=re.compile(r"Confirm\s+reversal", re.I)).click(timeout=8000)
    except Exception as e:
        return ("error_confirm_click", f"{type(e).__name__}: {e} @ url={page.url}")

    # Let the page transition to the finalize step before looking for that button
    page.wait_for_timeout(600)

    try:
        page.get_by_role("button", name=re.compile(r"Finalize\s+and\s+submit\s+reversal", re.I)).click(timeout=8000)
    except Exception as e:
        return ("error_finalize_click", f"{type(e).__name__}: {e} @ url={page.url}")

    # 13. Wait for the reversal to commit. We don't know the exact success
    #     signal yet, so wait for the page to settle and then pause briefly.
    try:
        page.wait_for_load_state("networkidle", timeout=12000)
    except Exception:
        pass
    page.wait_for_timeout(800)

    return ("ok", f"reversal submitted · voucher={voucher_id} · date={iso_date}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    raw = sys.argv[1:]
    dry_run  = "--dry-run"  in raw
    no_pause = "--no-pause" in raw
    headed   = "--headed"   in raw or True
    args     = [a for a in raw if not a.startswith("--")]

    vouchers_path = Path(args[0]).expanduser() if args else SCRIPT_DIR / "vouchers.csv"
    vouchers      = load_vouchers(vouchers_path)
    print(f"Loaded {len(vouchers)} voucher(s) from {vouchers_path}")

    if dry_run:
        for v in vouchers:
            print(f"  {v['mid']} · {v['voucher_id']} · {v['settlement_date']}")
        return

    results = []
    with sync_playwright() as p:
        USER_DATA_DIR.mkdir(exist_ok=True)
        context = p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=not headed,
            viewport={"width": 1440, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()

        page.goto(START_URL, wait_until="domcontentloaded")
        if no_pause:
            page.wait_for_timeout(3000)
        else:
            print("\nIf you're not already logged in, log in now in the Chromium window.")
            input("Press Enter here when you're ready to start...")

        out_path    = SCRIPT_DIR / "results.csv"
        failed_path = SCRIPT_DIR / "failed_vouchers.csv"

        def write_results_csv():
            with out_path.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["MID", "VoucherID", "SettlementDate", "AdjComment", "Status", "Note"])
                for row in results:
                    w.writerow(row)

        overall_start = time.time()
        interrupted   = False
        try:
            for i, v in enumerate(vouchers, 1):
                per_row_start = time.time()

                if i > 1:
                    avg = (time.time() - overall_start) / (i - 1)
                    remaining = int(avg * (len(vouchers) - i + 1))
                    eta_str = f" eta {remaining // 60}m{remaining % 60:02d}s"
                else:
                    eta_str = ""

                label = f"{v['mid']} · {v['voucher_id']}"
                print(f"[{i}/{len(vouchers)}]{eta_str} {label} ...",
                      end=" ", flush=True)

                try:
                    status, note = reverse_voucher(
                        page, v["mid"], v["voucher_id"], v["settlement_date"], v["adj_comment"]
                    )
                except PWTimeout as e:
                    status, note = "timeout", str(e).splitlines()[0]
                except Exception as e:
                    status, note = "error", f"{type(e).__name__}: {e}"

                if status not in ("ok", "not_found", "placeholder"):
                    try:
                        shot = SCRIPT_DIR / f"debug_fail_{v['mid']}.png"
                        page.screenshot(path=str(shot), full_page=True)
                        note = (note + " " if note else "") + f"(see {shot.name})"
                    except Exception:
                        pass

                elapsed = time.time() - per_row_start
                print(f"{status} ({elapsed:.1f}s)"
                      + (f" — {note}" if note else ""))

                results.append((v["mid"], v["voucher_id"], v["settlement_date"],
                                v["adj_comment"], status, note))
                write_results_csv()

                if i < len(vouchers):
                    page.wait_for_timeout(400)

        except KeyboardInterrupt:
            interrupted = True
            print("\n\n⚠ Interrupted — partial results saved.")

        context.close()

    # Write failed_vouchers.csv for quick re-runs (keeps the 4-column input format)
    failed_rows = [r for r in results if r[4] not in ("ok", "not_found", "placeholder")]
    if failed_rows:
        with failed_path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["MID", "VoucherID", "SettlementDate", "AdjComment"])
            for r in failed_rows:
                w.writerow([r[0], r[1], r[2], r[3]])

    total_elapsed = time.time() - overall_start
    ok_n  = sum(1 for r in results if r[4] == "ok")
    ph_n  = sum(1 for r in results if r[4] == "placeholder")
    nf_n  = sum(1 for r in results if r[4] == "not_found")
    err_n = len(results) - ok_n - nf_n - ph_n

    print("\n=== Summary ===")
    print(f"  processed:   {len(results)} / {len(vouchers)}"
          + (" (interrupted)" if interrupted else ""))
    print(f"  ok:          {ok_n}")
    print(f"  placeholder: {ph_n}" + (" (reversal steps not yet recorded)" if ph_n else ""))
    print(f"  not_found:   {nf_n}")
    print(f"  errors:      {err_n}")
    print(f"  total time:  {int(total_elapsed // 60)}m{int(total_elapsed % 60):02d}s")
    print(f"  results:     {out_path}")
    if failed_rows:
        print(f"  failed:      {failed_path}  "
              f"(re-run: python3 {Path(__file__).name} {failed_path.name})")


if __name__ == "__main__":
    main()
