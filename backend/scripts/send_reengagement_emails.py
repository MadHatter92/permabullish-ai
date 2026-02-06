#!/usr/bin/env python3
"""
Re-engagement Email Script for Permabullish

This script sends re-engagement emails to inactive free users.
Should be run daily via cron job, ideally around 10 AM IST.

Schedule (IST timing):
- Days 1-14 after signup: Daily emails (if inactive for 7+ days)
- Days 15-180 after signup: Weekly emails (if inactive for 7+ days)

Usage:
    python send_reengagement_emails.py [--dry-run] [--limit N]

Options:
    --dry-run    Don't actually send emails, just print what would be sent
    --limit N    Maximum number of emails to send (default: no limit)
"""

import sys
import os
import time
from datetime import datetime
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytz
from database import (
    get_users_for_reengagement,
    update_reengagement_email_sent,
    get_external_contacts_for_reengagement,
    update_external_contact_email_sent,
    get_external_contact_count,
)
from email_service import (
    send_reengagement_email,
    get_featured_reports_for_email,
    get_template_for_day,
    get_first_name,
)

# India timezone
IST = pytz.timezone('Asia/Kolkata')


def calculate_days_since(timestamp) -> int:
    """Calculate days since a timestamp."""
    if timestamp is None:
        return 999  # Large number for "never"

    if isinstance(timestamp, str):
        # Handle ISO format
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00').replace(' ', 'T'))

    # Remove timezone info for comparison
    if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
        timestamp = timestamp.replace(tzinfo=None)

    return (datetime.now() - timestamp).days


def main():
    parser = argparse.ArgumentParser(description='Send re-engagement emails to inactive users')
    parser.add_argument('--dry-run', action='store_true', help="Don't send, just show what would be sent")
    parser.add_argument('--limit', type=int, default=0, help='Max emails to send (0 = no limit)')
    args = parser.parse_args()

    # Get current IST time
    now_ist = datetime.now(IST)
    print(f"[RE-ENGAGEMENT] Starting at {now_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Get featured reports for emails
    sample_reports = get_featured_reports_for_email()
    print(f"[RE-ENGAGEMENT] Loaded {len(sample_reports)} featured reports")

    # Get eligible users
    users = get_users_for_reengagement()
    print(f"[RE-ENGAGEMENT] Found {len(users)} eligible users")

    if args.limit > 0:
        users = users[:args.limit]
        print(f"[RE-ENGAGEMENT] Limited to {len(users)} users")

    sent_count = 0
    failed_count = 0

    for user in users:
        user_id = user['id']
        email = user['email']
        full_name = user.get('full_name', '')
        first_name = get_first_name(full_name)

        # Calculate days since signup
        days_since_signup = calculate_days_since(user.get('created_at'))
        email_count = user.get('reengagement_email_count', 0) or 0

        # Determine which template to use
        template_num = get_template_for_day(days_since_signup, email_count)

        print(f"  User {user_id} ({email}): {days_since_signup} days, {email_count} emails sent, template {template_num}")

        if args.dry_run:
            print(f"    [DRY RUN] Would send template {template_num}")
            sent_count += 1
            continue

        # Send the email
        try:
            success = send_reengagement_email(
                user_email=email,
                first_name=first_name,
                template_num=template_num,
                sample_reports=sample_reports
            )

            if success:
                # Update tracking in database
                update_reengagement_email_sent(user_id)
                sent_count += 1
                print(f"    [SENT] Template {template_num}")
            else:
                failed_count += 1
                print(f"    [FAILED] Template {template_num}")

        except Exception as e:
            failed_count += 1
            print(f"    [ERROR] {e}")

        # Rate limit: Resend allows 2 requests/second
        time.sleep(0.6)

    print(f"\n[RE-ENGAGEMENT] Users complete:")
    print(f"  Sent: {sent_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total processed: {len(users)}")

    # =========================================================================
    # EXTERNAL CONTACTS
    # =========================================================================
    print(f"\n[RE-ENGAGEMENT] Processing external contacts...")

    external_contacts = get_external_contacts_for_reengagement()
    print(f"[RE-ENGAGEMENT] Found {len(external_contacts)} eligible external contacts")

    if args.limit > 0:
        remaining_limit = args.limit - sent_count
        if remaining_limit > 0:
            external_contacts = external_contacts[:remaining_limit]
        else:
            external_contacts = []
        print(f"[RE-ENGAGEMENT] Limited to {len(external_contacts)} external contacts")

    external_sent = 0
    external_failed = 0

    for contact in external_contacts:
        contact_id = contact['id']
        email = contact['email']
        first_name = contact.get('first_name') or ''
        email_count = contact.get('reengagement_email_count', 0) or 0

        # External contacts use template rotation 1-14 (generic, broker, Hindi, Gujarati)
        template_num = (email_count % 14) + 1

        print(f"  External {contact_id} ({email}): {email_count} emails sent, template {template_num}")

        if args.dry_run:
            print(f"    [DRY RUN] Would send template {template_num}")
            external_sent += 1
            continue

        try:
            success = send_reengagement_email(
                user_email=email,
                first_name=first_name,
                template_num=template_num,
                sample_reports=sample_reports
            )

            if success:
                update_external_contact_email_sent(contact_id)
                external_sent += 1
                print(f"    [SENT] Template {template_num}")
            else:
                external_failed += 1
                print(f"    [FAILED] Template {template_num}")

        except Exception as e:
            external_failed += 1
            print(f"    [ERROR] {e}")

        # Rate limit: Resend allows 2 requests/second
        time.sleep(0.6)

    print(f"\n[RE-ENGAGEMENT] External contacts complete:")
    print(f"  Sent: {external_sent}")
    print(f"  Failed: {external_failed}")
    print(f"  Total processed: {len(external_contacts)}")

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print(f"\n[RE-ENGAGEMENT] FINAL SUMMARY:")
    print(f"  Users - Sent: {sent_count}, Failed: {failed_count}")
    print(f"  External - Sent: {external_sent}, Failed: {external_failed}")
    print(f"  TOTAL - Sent: {sent_count + external_sent}, Failed: {failed_count + external_failed}")


if __name__ == "__main__":
    main()
