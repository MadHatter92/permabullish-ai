#!/usr/bin/env python3
"""
Re-engagement Email Script for Permabullish

This script sends re-engagement emails to inactive free users.
Can be run multiple times per day via cron job for batched sending.

Batch Schedule (IST timing):
- Batch 0: 9 AM IST (Morning)
- Batch 1: 2 PM IST (Afternoon)
- Batch 2: 6 PM IST (Evening)

Batch Rotation:
- Contacts rotate through batches using: (contact_id + day_of_year) % 3
- This ensures the same person receives emails at different times on different days

User Schedule (IST timing):
- Days 1-14 after signup: Daily emails (if inactive for 1+ days)
- Days 15-180 after signup: Weekly emails (if inactive for 7+ days)

Batch Size Limit:
- Default: 200 emails per batch (configurable via --batch-size)
- This caps total emails (users + external contacts) per run for domain warm-up / deliverability

Usage:
    python send_reengagement_emails.py [--dry-run] [--limit N] [--batch N] [--batch-size N]

Options:
    --dry-run       Don't actually send emails, just print what would be sent
    --limit N       Maximum number of emails to send (default: no limit)
    --batch N       Force specific batch (0, 1, 2). Auto-detects if not specified.
    --batch-size N  Max emails per batch run (default: 200). Set 0 for unlimited.
    --all           Send to all batches (ignore batching, for backward compatibility)
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

# Max emails per batch run (for domain warm-up / deliverability)
DEFAULT_BATCH_SIZE = 200

# Batch time windows (IST hours)
# Batch 0: 9 AM (hour 9)
# Batch 1: 2 PM (hour 14)
# Batch 2: 6 PM (hour 18)
BATCH_HOURS = {
    0: (8, 12),   # 8 AM - 12 PM -> Batch 0 (Morning)
    1: (12, 16),  # 12 PM - 4 PM -> Batch 1 (Afternoon)
    2: (16, 23),  # 4 PM - 11 PM -> Batch 2 (Evening)
}


def get_batch_from_hour(hour: int) -> int:
    """
    Determine which batch to run based on current IST hour.
    Returns batch number 0, 1, or 2.
    """
    for batch_num, (start, end) in BATCH_HOURS.items():
        if start <= hour < end:
            return batch_num
    # Default to batch 0 for early morning hours (before 8 AM)
    return 0


def get_batch_name(batch_num: int) -> str:
    """Get human-readable batch name."""
    names = {0: "Morning (9 AM)", 1: "Afternoon (2 PM)", 2: "Evening (6 PM)"}
    return names.get(batch_num, f"Batch {batch_num}")


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
    parser.add_argument('--batch', type=int, choices=[0, 1, 2], help='Force specific batch (0=Morning, 1=Afternoon, 2=Evening)')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE, help=f'Max emails per batch run (default: {DEFAULT_BATCH_SIZE}, 0 = unlimited)')
    parser.add_argument('--all', action='store_true', help='Send to all contacts (ignore batching)')
    args = parser.parse_args()

    # Get current IST time
    now_ist = datetime.now(IST)
    day_of_year = now_ist.timetuple().tm_yday
    current_hour = now_ist.hour

    # Determine batch number
    if args.all:
        batch_num = None
        batch_info = "ALL BATCHES"
    elif args.batch is not None:
        batch_num = args.batch
        batch_info = f"BATCH {batch_num} ({get_batch_name(batch_num)})"
    else:
        batch_num = get_batch_from_hour(current_hour)
        batch_info = f"BATCH {batch_num} ({get_batch_name(batch_num)}) - auto-detected"

    # Batch size limit
    batch_size = args.batch_size
    batch_size_info = f"{batch_size} emails" if batch_size > 0 else "unlimited"

    print(f"[RE-ENGAGEMENT] Starting at {now_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"[RE-ENGAGEMENT] Day of year: {day_of_year}, Hour: {current_hour}")
    print(f"[RE-ENGAGEMENT] Processing: {batch_info}")
    print(f"[RE-ENGAGEMENT] Batch size limit: {batch_size_info}")

    # Get featured reports for emails
    sample_reports = get_featured_reports_for_email(day_of_year)
    print(f"[RE-ENGAGEMENT] Loaded {len(sample_reports)} featured reports")

    # Get eligible users
    users = get_users_for_reengagement()
    print(f"[RE-ENGAGEMENT] Found {len(users)} eligible users")

    if args.limit > 0:
        users = users[:args.limit]
        print(f"[RE-ENGAGEMENT] Limited to {len(users)} users (--limit)")

    # Apply batch size cap to users
    if batch_size > 0 and len(users) > batch_size:
        users = users[:batch_size]
        print(f"[RE-ENGAGEMENT] Capped to {len(users)} users (--batch-size {batch_size})")

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
    # EXTERNAL CONTACTS (with batching)
    # =========================================================================
    print(f"\n[RE-ENGAGEMENT] Processing external contacts...")
    print(f"[RE-ENGAGEMENT] {batch_info}")

    # Fetch contacts for this batch (or all if --all)
    if batch_num is not None:
        external_contacts = get_external_contacts_for_reengagement(
            batch_num=batch_num,
            day_of_year=day_of_year
        )
        print(f"[RE-ENGAGEMENT] Found {len(external_contacts)} eligible contacts for batch {batch_num}")
    else:
        external_contacts = get_external_contacts_for_reengagement()
        print(f"[RE-ENGAGEMENT] Found {len(external_contacts)} eligible external contacts (all batches)")

    # Apply --limit (counts across users + external)
    if args.limit > 0:
        remaining_limit = args.limit - sent_count
        if remaining_limit > 0:
            external_contacts = external_contacts[:remaining_limit]
        else:
            external_contacts = []
        print(f"[RE-ENGAGEMENT] Limited to {len(external_contacts)} external contacts (--limit)")

    # Apply batch size cap (counts across users + external)
    if batch_size > 0:
        remaining_batch = batch_size - sent_count
        if remaining_batch > 0:
            if len(external_contacts) > remaining_batch:
                external_contacts = external_contacts[:remaining_batch]
                print(f"[RE-ENGAGEMENT] Capped to {len(external_contacts)} external contacts (--batch-size {batch_size}, {sent_count} already sent to users)")
        else:
            print(f"[RE-ENGAGEMENT] Batch size reached ({sent_count} sent to users), skipping external contacts")
            external_contacts = []

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
    print(f"  {batch_info}")
    print(f"  Batch size limit: {batch_size_info}")
    print(f"  Day of year: {day_of_year}")
    print(f"  Users - Sent: {sent_count}, Failed: {failed_count}")
    print(f"  External - Sent: {external_sent}, Failed: {external_failed}")
    print(f"  TOTAL - Sent: {sent_count + external_sent}, Failed: {failed_count + external_failed}")


if __name__ == "__main__":
    main()
