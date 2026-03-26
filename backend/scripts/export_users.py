#!/usr/bin/env python3
"""
Export all users from the database — email accounts and WhatsApp-only users.

Usage:
    python scripts/export_users.py                        # All users (email + whatsapp)
    python scripts/export_users.py --channel email        # Email users only
    python scripts/export_users.py --channel whatsapp     # WhatsApp-only users (no email)
    python scripts/export_users.py --channel both         # Users with email + WhatsApp linked
    python scripts/export_users.py --google-only          # Google OAuth users only
    python scripts/export_users.py --format csv           # CSV output
    python scripts/export_users.py --output users.csv     # Save to file
    python scripts/export_users.py --emails-only          # Email addresses only (one per line)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import get_db_connection, get_cursor, placeholder, USE_POSTGRES, _dict_from_row


def get_users(google_only: bool = False, active_only: bool = True, channel: str = "all") -> list[dict]:
    """Fetch all users — email accounts and WhatsApp-only — as a unified list."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        results = []

        month_expr = "TO_CHAR(NOW(), 'YYYY-MM')" if USE_POSTGRES else "strftime('%Y-%m', 'now')"
        nulls_last = "NULLS LAST" if USE_POSTGRES else ""
        active_cond = ("AND u.is_active = TRUE" if USE_POSTGRES else "AND u.is_active = 1") if active_only else ""
        google_cond = "AND u.google_id IS NOT NULL" if google_only else ""

        # ── Email users (with optional WA enrichment) ─────────────────────────
        if channel in ("all", "email", "both"):
            both_cond  = "AND wa.id IS NOT NULL" if channel == "both" else ""
            email_cond = "AND wa.id IS NULL" if channel == "email" else ""
            email_query = f"""
                SELECT
                    u.id,
                    u.email,
                    u.full_name,
                    u.auth_provider,
                    u.created_at,
                    CASE WHEN wa.id IS NOT NULL THEN 'both' ELSE 'email' END AS channel,
                    wa.phone_number,
                    wa.phone_hash,
                    wa.linked_at AS wa_linked_at,
                    COALESCE(wu.report_count, 0) AS wa_reports_this_month,
                    last_evt.last_active AS wa_last_active
                FROM users u
                LEFT JOIN whatsapp_accounts wa ON wa.user_id = u.id
                LEFT JOIN whatsapp_usage wu ON wu.phone_hash = wa.phone_hash
                    AND wu.month_year = {month_expr}
                LEFT JOIN (
                    SELECT phone_hash, MAX(created_at) AS last_active
                    FROM whatsapp_events
                    GROUP BY phone_hash
                ) last_evt ON last_evt.phone_hash = wa.phone_hash
                WHERE 1=1
                {active_cond}
                {google_cond}
                {both_cond}
                {email_cond}
                ORDER BY u.created_at DESC
            """
            cursor.execute(email_query)
            rows = cursor.fetchall()
            for row in rows:
                results.append(_dict_from_row(row))

        # ── WhatsApp-only users (no email account) ────────────────────────────
        if channel in ("all", "whatsapp"):
            wa_query = f"""
                SELECT
                    NULL AS id,
                    NULL AS email,
                    NULL AS full_name,
                    'whatsapp' AS auth_provider,
                    MIN(we.created_at) AS created_at,
                    'whatsapp' AS channel,
                    wa.phone_number,
                    wa.phone_hash,
                    NULL AS wa_linked_at,
                    COALESCE(wu.report_count, 0) AS wa_reports_this_month,
                    MAX(we.created_at) AS wa_last_active
                FROM whatsapp_events we
                LEFT JOIN whatsapp_accounts wa ON wa.phone_hash = we.phone_hash
                LEFT JOIN whatsapp_usage wu ON wu.phone_hash = we.phone_hash
                    AND wu.month_year = {month_expr}
                WHERE (wa.user_id IS NULL OR wa.id IS NULL)
                GROUP BY wa.phone_number, wa.phone_hash, wu.report_count
                ORDER BY MAX(we.created_at) DESC {nulls_last}
            """
            try:
                cursor.execute(wa_query)
                rows = cursor.fetchall()
                seen_hashes = {r.get("phone_hash") for r in results}
                for row in rows:
                    r = _dict_from_row(row)
                    if r.get("phone_hash") in seen_hashes:
                        continue
                    results.append(r)
            except Exception:
                pass  # whatsapp_events table may not exist in dev

        return results


def format_as_table(users: list[dict]) -> str:
    if not users:
        return "No users found"

    lines = []
    lines.append(f"{'ID':<6} {'Email':<36} {'Phone':<18} {'Name':<22} {'Channel':<10} {'Provider':<10} {'Created':<12} {'WA Rep':<8} {'WA Last Active'}")
    lines.append("-" * 140)

    for user in users:
        uid     = str(user.get("id") or "—")
        email   = (user.get("email") or "—")[:34]
        phone   = (user.get("phone_number") or "—")[:16]
        name    = (user.get("full_name") or "—")[:20]
        channel = user.get("channel") or "email"
        provider= user.get("auth_provider") or "local"
        created = str(user.get("created_at") or "")[:10]
        wa_rep  = str(user.get("wa_reports_this_month") or 0)
        wa_last = str(user.get("wa_last_active") or "—")[:10]

        lines.append(
            f"{uid:<6} "
            f"{email:<36} "
            f"{phone:<18} "
            f"{name:<22} "
            f"{channel:<10} "
            f"{provider:<10} "
            f"{created:<12} "
            f"{wa_rep:<8} "
            f"{wa_last}"
        )

    lines.append("-" * 130)

    email_count = sum(1 for u in users if u.get("channel") in ("email", "both"))
    wa_only     = sum(1 for u in users if u.get("channel") == "whatsapp")
    both_count  = sum(1 for u in users if u.get("channel") == "both")
    lines.append(f"Total: {len(users)} users  |  Email: {email_count}  |  WhatsApp-only: {wa_only}  |  Both: {both_count}")

    return "\n".join(lines)


def format_as_csv(users: list[dict]) -> str:
    if not users:
        return "No users found"

    fieldnames = ["id", "email", "phone_number", "full_name", "channel", "auth_provider",
                  "created_at", "wa_linked_at", "wa_reports_this_month", "wa_last_active"]
    lines = [",".join(fieldnames)]
    for user in users:
        row = []
        for f in fieldnames:
            val = str(user.get(f) or "")
            row.append(f'"{val}"' if "," in val else val)
        lines.append(",".join(row))
    return "\n".join(lines)


def format_as_json(users: list[dict]) -> str:
    return json.dumps(users, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(description="Export all users (email + WhatsApp)")
    parser.add_argument("--channel", "-c", choices=["all", "email", "whatsapp", "both"],
                        default="all", help="Filter by channel (default: all)")
    parser.add_argument("--google-only", "-g", action="store_true", help="Email users via Google OAuth only")
    parser.add_argument("--include-inactive", action="store_true", help="Include inactive users")
    parser.add_argument("--format", "-f", choices=["table", "csv", "json"], default="table")
    parser.add_argument("--output", "-o", type=str, help="Output file path")
    parser.add_argument("--emails-only", "-e", action="store_true", help="Output email addresses only")

    args = parser.parse_args()

    users = get_users(
        google_only=args.google_only,
        active_only=not args.include_inactive,
        channel=args.channel,
    )

    if args.emails_only:
        output = "\n".join(u["email"] for u in users if u.get("email"))
    elif args.format == "csv":
        output = format_as_csv(users)
    elif args.format == "json":
        output = format_as_json(users)
    else:
        output = format_as_table(users)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Exported {len(users)} users to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
