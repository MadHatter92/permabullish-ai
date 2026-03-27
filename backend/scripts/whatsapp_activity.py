#!/usr/bin/env python3
"""
WhatsApp activity viewer — run in Render shell for a quick snapshot.

Usage:
    python scripts/whatsapp_activity.py              # Last 24 hours
    python scripts/whatsapp_activity.py --days 7     # Last 7 days
    python scripts/whatsapp_activity.py --days 30    # Last 30 days
    python scripts/whatsapp_activity.py --phone +917259891109   # One user
    python scripts/whatsapp_activity.py --recent 50  # Last 50 events (any user)
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import get_db_connection, get_cursor, placeholder, _dict_from_row, USE_POSTGRES
import hashlib


def _hash(phone: str) -> str:
    phone = phone.strip().lstrip("+")
    if not phone.startswith("+"):
        phone = "+" + phone
    return hashlib.sha256(phone.lstrip("+").encode()).hexdigest()


def _fmt_time(ts) -> str:
    if not ts:
        return "—"
    s = str(ts)[:16]
    return s


def get_summary(days: int):
    """Print a top-level summary for the period."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    p = placeholder()

    with get_db_connection() as conn:
        cur = get_cursor(conn)

        cur.execute(
            f"SELECT COUNT(*) as c FROM whatsapp_events WHERE event_type='report_sent' AND created_at>={p}",
            (cutoff,)
        )
        reports = _dict_from_row(cur.fetchone())["c"]

        cur.execute(
            f"SELECT COUNT(DISTINCT phone_hash) as c FROM whatsapp_events WHERE created_at>={p}",
            (cutoff,)
        )
        active = _dict_from_row(cur.fetchone())["c"]

        cur.execute(
            f"""SELECT COUNT(*) as c FROM (
                SELECT phone_hash FROM whatsapp_events GROUP BY phone_hash
                HAVING MIN(created_at) >= {p}
            ) sub""",
            (cutoff,)
        )
        new_phones = _dict_from_row(cur.fetchone())["c"]

        cur.execute(
            f"SELECT COUNT(*) as c FROM whatsapp_accounts WHERE user_id IS NOT NULL AND linked_at>={p}",
            (cutoff,)
        )
        linked = _dict_from_row(cur.fetchone())["c"]

        cur.execute(
            f"SELECT COUNT(*) as c FROM whatsapp_events WHERE event_type='report_blocked_limit' AND created_at>={p}",
            (cutoff,)
        )
        blocked = _dict_from_row(cur.fetchone())["c"]

        cur.execute(
            f"SELECT COUNT(*) as c FROM whatsapp_events WHERE event_type='portfolio_analysis_sent' AND created_at>={p}",
            (cutoff,)
        )
        portfolios = _dict_from_row(cur.fetchone())["c"]

        # Action taps
        cur.execute(
            f"""SELECT event_type, COUNT(*) as c FROM whatsapp_events
                WHERE event_type IN ('action_b','action_r','action_n') AND created_at>={p}
                GROUP BY event_type""",
            (cutoff,)
        )
        actions = {_dict_from_row(r)["event_type"]: _dict_from_row(r)["c"] for r in cur.fetchall()}

        # Top stocks
        cur.execute(
            f"""SELECT ticker, COUNT(*) as c FROM whatsapp_events
                WHERE event_type='report_sent' AND ticker IS NOT NULL AND created_at>={p}
                GROUP BY ticker ORDER BY c DESC LIMIT 10""",
            (cutoff,)
        )
        top_stocks = [f"{_dict_from_row(r)['ticker']} x{_dict_from_row(r)['c']}" for r in cur.fetchall()]

        # All-time totals
        cur.execute("SELECT COUNT(DISTINCT phone_hash) as c FROM whatsapp_events")
        total_phones = _dict_from_row(cur.fetchone())["c"]
        cur.execute("SELECT COUNT(*) as c FROM whatsapp_accounts WHERE user_id IS NOT NULL")
        total_linked = _dict_from_row(cur.fetchone())["c"]
        cur.execute("SELECT COUNT(*) as c FROM whatsapp_events WHERE event_type='report_sent'")
        total_reports = _dict_from_row(cur.fetchone())["c"]

    w = 44
    print("=" * w)
    print(f"  WhatsApp Activity — Last {days} day{'s' if days != 1 else ''}")
    print("=" * w)
    print(f"  Reports sent:      {reports}")
    print(f"  Active phones:     {active}")
    print(f"  New phones:        {new_phones}")
    print(f"  Accounts linked:   {linked}")
    print(f"  Blocked (limit):   {blocked}")
    print(f"  Portfolio analyses:{portfolios}")
    print(f"  Action taps:       Bull/Bear={actions.get('action_b',0)}  Results={actions.get('action_r',0)}  News={actions.get('action_n',0)}")
    if top_stocks:
        print(f"  Top stocks:        {', '.join(top_stocks[:5])}")
        if len(top_stocks) > 5:
            print(f"                     {', '.join(top_stocks[5:])}")
    print("-" * w)
    print(f"  ALL-TIME: {total_phones} phones | {total_linked} linked | {total_reports} reports")
    print("=" * w)


def get_conversations(days: int):
    """List every unique phone that was active in the period, with their activity."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    p = placeholder()

    with get_db_connection() as conn:
        cur = get_cursor(conn)

        # Get all active phones with metadata
        cur.execute(
            f"""SELECT
                    e.phone_hash,
                    a.phone_number,
                    MIN(e.created_at) as first_seen,
                    MAX(e.created_at) as last_seen,
                    COUNT(*) as total_events,
                    SUM(CASE WHEN e.event_type='report_sent' THEN 1 ELSE 0 END) as reports,
                    SUM(CASE WHEN e.event_type='portfolio_analysis_sent' THEN 1 ELSE 0 END) as portfolios,
                    MAX(CASE WHEN a.user_id IS NOT NULL THEN 1 ELSE 0 END) as is_linked
                FROM whatsapp_events e
                LEFT JOIN whatsapp_accounts a ON e.phone_hash = a.phone_hash
                WHERE e.created_at >= {p}
                GROUP BY e.phone_hash, a.phone_number
                ORDER BY last_seen DESC""",
            (cutoff,)
        )
        phones = [_dict_from_row(r) for r in cur.fetchall()]

        if not phones:
            print(f"  No activity in the last {days} day(s).")
            return

        print(f"\n  {len(phones)} phone(s) active in last {days} day(s):\n")

        for i, ph in enumerate(phones, 1):
            number  = ph.get("phone_number") or f"[hash: {ph['phone_hash'][:12]}…]"
            linked  = "✅ linked" if ph["is_linked"] else "○ unlinked"
            reports = ph["reports"]
            portf   = ph["portfolios"]
            last    = _fmt_time(ph["last_seen"])
            first   = _fmt_time(ph["first_seen"])

            line = f"  {i:>3}. {number}  {linked}"
            if reports:
                line += f"  | {reports} report{'s' if reports != 1 else ''}"
            if portf:
                line += f"  | {portf} portfolio"
            line += f"  | last: {last}"
            print(line)

            # Show tickers they queried
            cur.execute(
                f"""SELECT DISTINCT ticker FROM whatsapp_events
                    WHERE phone_hash = {p} AND ticker IS NOT NULL AND created_at >= {p}
                    ORDER BY created_at DESC LIMIT 10""",
                (ph["phone_hash"], cutoff)
            )
            tickers = [_dict_from_row(r)["ticker"] for r in cur.fetchall()]
            if tickers:
                print(f"       Stocks: {', '.join(tickers)}")


def get_recent_events(limit: int):
    """Print the most recent N events across all users."""
    p = placeholder()

    with get_db_connection() as conn:
        cur = get_cursor(conn)

        if USE_POSTGRES:
            cur.execute(
                f"""SELECT e.event_type, e.ticker, e.created_at, a.phone_number, e.phone_hash
                    FROM whatsapp_events e
                    LEFT JOIN whatsapp_accounts a ON e.phone_hash = a.phone_hash
                    ORDER BY e.created_at DESC LIMIT {p}""",
                (limit,)
            )
        else:
            cur.execute(
                f"""SELECT e.event_type, e.ticker, e.created_at, a.phone_number, e.phone_hash
                    FROM whatsapp_events e
                    LEFT JOIN whatsapp_accounts a ON e.phone_hash = a.phone_hash
                    ORDER BY e.created_at DESC LIMIT {p}""",
                (limit,)
            )

        rows = [_dict_from_row(r) for r in cur.fetchall()]

    print(f"\n  Last {limit} events:\n")
    print(f"  {'Time':<17} {'Event':<32} {'Ticker':<12} {'Phone'}")
    print("  " + "-" * 80)
    for r in rows:
        number = r.get("phone_number") or f"[…{r['phone_hash'][:8]}]"
        ticker = r.get("ticker") or ""
        ts     = _fmt_time(r["created_at"])
        print(f"  {ts:<17} {r['event_type']:<32} {ticker:<12} {number}")


def get_phone_history(phone: str):
    """Print full event history for one phone number."""
    # Accept +91... or 91... format
    raw = phone.strip().lstrip("+")
    phone_hash = hashlib.sha256(raw.encode()).hexdigest()
    p = placeholder()

    with get_db_connection() as conn:
        cur = get_cursor(conn)

        # Check account
        cur.execute(
            f"SELECT phone_number, user_id, linked_at FROM whatsapp_accounts WHERE phone_hash={p}",
            (phone_hash,)
        )
        row = cur.fetchone()
        acct = _dict_from_row(row) if row else {}

        # Get all events
        cur.execute(
            f"""SELECT event_type, ticker, metadata, created_at FROM whatsapp_events
                WHERE phone_hash={p} ORDER BY created_at DESC""",
            (phone_hash,)
        )
        events = [_dict_from_row(r) for r in cur.fetchall()]

    print(f"\n  Phone: +{raw}")
    if acct:
        linked = f"user_id={acct['user_id']} (since {_fmt_time(acct['linked_at'])})" if acct.get("user_id") else "unlinked"
        print(f"  Account: {linked}")
    else:
        print("  Account: no record (never messaged or hash mismatch)")

    if not events:
        print("  No events found.")
        return

    print(f"  Total events: {len(events)}\n")
    print(f"  {'Time':<17} {'Event':<32} {'Ticker'}")
    print("  " + "-" * 60)
    for e in events:
        ticker = e.get("ticker") or ""
        ts     = _fmt_time(e["created_at"])
        print(f"  {ts:<17} {e['event_type']:<32} {ticker}")


def main():
    parser = argparse.ArgumentParser(description="WhatsApp activity viewer")
    parser.add_argument("--days",   type=int, default=1,  help="Period in days (default: 1)")
    parser.add_argument("--recent", type=int, default=0,  help="Show last N events across all users")
    parser.add_argument("--phone",  type=str, default="", help="Show full history for one phone number")
    args = parser.parse_args()

    if args.phone:
        get_phone_history(args.phone)
    elif args.recent:
        get_recent_events(args.recent)
    else:
        get_summary(args.days)
        get_conversations(args.days)


if __name__ == "__main__":
    main()
