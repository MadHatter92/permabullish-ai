#!/usr/bin/env python3
"""
Cleanup Bounced Emails Script

Fetches email delivery status from Resend API and marks bounced/failed
contacts as inactive in the external_contacts table.

Usage:
    python cleanup_bounced_emails.py [--dry-run] [--limit N]

Options:
    --dry-run    Don't update database, just show what would be marked inactive
    --limit N    Maximum number of emails to fetch from Resend (default: all)
"""

import sys
import os
import argparse
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import resend
from config import RESEND_API_KEY
from database import init_database, get_db_connection, get_cursor, placeholder, USE_POSTGRES

# Initialize Resend
resend.api_key = RESEND_API_KEY

# Statuses that indicate permanent delivery failure
FAILED_STATUSES = {'bounced', 'failed', 'complained'}


def fetch_all_emails(limit: int = 0) -> list:
    """
    Fetch all sent emails from Resend API with pagination.

    Args:
        limit: Maximum emails to fetch (0 = all)

    Returns:
        List of email objects
    """
    all_emails = []
    after_cursor = None
    page = 1

    print("[RESEND] Fetching emails from Resend API...")

    while True:
        params = {"limit": 100}
        if after_cursor:
            params["after"] = after_cursor

        try:
            response = resend.Emails.list(params)
            emails = response.get("data", [])

            if not emails:
                break

            all_emails.extend(emails)
            print(f"  Page {page}: fetched {len(emails)} emails (total: {len(all_emails)})")

            # Check if we've hit the limit
            if limit > 0 and len(all_emails) >= limit:
                all_emails = all_emails[:limit]
                break

            # Check if there are more pages
            if not response.get("has_more", False):
                break

            # Get cursor for next page (last email ID)
            after_cursor = emails[-1].get("id")
            page += 1

            # Rate limit: be nice to the API
            time.sleep(0.5)

        except Exception as e:
            print(f"[ERROR] Failed to fetch emails: {e}")
            break

    print(f"[RESEND] Total emails fetched: {len(all_emails)}")
    return all_emails


def extract_bounced_emails(emails: list) -> set:
    """
    Extract email addresses that bounced or failed.

    Args:
        emails: List of email objects from Resend

    Returns:
        Set of email addresses that failed
    """
    bounced = set()
    status_counts = {}

    for email in emails:
        status = email.get("last_event", "").lower()

        # Count statuses for reporting
        status_counts[status] = status_counts.get(status, 0) + 1

        if status in FAILED_STATUSES:
            # Extract recipient email(s)
            to_list = email.get("to", [])
            if isinstance(to_list, list):
                for addr in to_list:
                    bounced.add(addr.lower().strip())
            elif isinstance(to_list, str):
                bounced.add(to_list.lower().strip())

    print("\n[STATUS BREAKDOWN]")
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        marker = " <-- FAILED" if status in FAILED_STATUSES else ""
        print(f"  {status}: {count}{marker}")

    return bounced


def mark_contacts_inactive(emails: set, dry_run: bool = False) -> tuple:
    """
    Mark external contacts as inactive if their email bounced.

    Args:
        emails: Set of email addresses to mark inactive
        dry_run: If True, don't actually update database

    Returns:
        Tuple of (updated_count, not_found_count)
    """
    if not emails:
        print("\n[DATABASE] No bounced emails to process")
        return 0, 0

    print(f"\n[DATABASE] Processing {len(emails)} bounced email addresses...")

    updated = 0
    not_found = 0

    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()

        for email in emails:
            # Check if email exists in external_contacts
            cursor.execute(
                f"SELECT id, is_active FROM external_contacts WHERE email = {p}",
                (email,)
            )
            row = cursor.fetchone()

            if row is None:
                not_found += 1
                continue

            contact_id = row[0] if isinstance(row, tuple) else row['id']
            is_active = row[1] if isinstance(row, tuple) else row['is_active']

            if not is_active:
                # Already inactive
                continue

            if dry_run:
                print(f"  [DRY RUN] Would mark inactive: {email}")
                updated += 1
            else:
                cursor.execute(
                    f"UPDATE external_contacts SET is_active = FALSE WHERE id = {p}",
                    (contact_id,)
                )
                updated += 1
                if updated <= 20 or updated % 100 == 0:
                    print(f"  Marked inactive: {email}")

        if not dry_run:
            conn.commit()

    return updated, not_found


def get_current_stats():
    """Get current external contact stats."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)

        cursor.execute("SELECT COUNT(*) FROM external_contacts")
        total = cursor.fetchone()[0]

        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) FROM external_contacts WHERE is_active = TRUE")
        else:
            cursor.execute("SELECT COUNT(*) FROM external_contacts WHERE is_active = 1")
        active = cursor.fetchone()[0]

        return total, active


def main():
    parser = argparse.ArgumentParser(description='Cleanup bounced emails from distribution list')
    parser.add_argument('--dry-run', action='store_true', help="Don't update, just show what would change")
    parser.add_argument('--limit', type=int, default=0, help='Max emails to fetch from Resend (0 = all)')
    args = parser.parse_args()

    if not RESEND_API_KEY:
        print("Error: RESEND_API_KEY not set")
        sys.exit(1)

    # Initialize database
    init_database()

    # Get stats before
    total_before, active_before = get_current_stats()
    print(f"\n[STATS] Before cleanup:")
    print(f"  Total contacts: {total_before}")
    print(f"  Active contacts: {active_before}")
    print(f"  Inactive contacts: {total_before - active_before}")

    # Fetch emails from Resend
    emails = fetch_all_emails(limit=args.limit)

    if not emails:
        print("\nNo emails found in Resend")
        return

    # Extract bounced email addresses
    bounced = extract_bounced_emails(emails)
    print(f"\n[BOUNCED] Found {len(bounced)} unique bounced/failed email addresses")

    # Mark contacts as inactive
    updated, not_found = mark_contacts_inactive(bounced, dry_run=args.dry_run)

    # Get stats after
    total_after, active_after = get_current_stats()

    print("\n" + "=" * 50)
    print("CLEANUP SUMMARY")
    print("=" * 50)
    print(f"  Emails fetched from Resend: {len(emails)}")
    print(f"  Bounced/failed addresses: {len(bounced)}")
    print(f"  Contacts marked inactive: {updated}")
    print(f"  Not in external_contacts: {not_found}")

    if args.dry_run:
        print(f"\n[DRY RUN] No changes made to database")
    else:
        print(f"\n[STATS] After cleanup:")
        print(f"  Total contacts: {total_after}")
        print(f"  Active contacts: {active_after}")
        print(f"  Inactive contacts: {total_after - active_after}")


if __name__ == "__main__":
    main()
