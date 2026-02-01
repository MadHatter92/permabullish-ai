#!/usr/bin/env python3
"""
Subscription Expiry Email Script for Permabullish

This script sends reminder emails to users whose paid subscriptions have expired.
Should be run daily via cron job, ideally around 10 AM IST.

Schedule:
- Day 0 (expiry day): Reminder that subscription expires today
- Day 1-3: Daily follow-up
- Day 3-7: Every 3 days
- Day 7-60: Weekly reminders

Usage:
    python send_expiry_emails.py [--dry-run] [--limit N]

Options:
    --dry-run    Don't actually send emails, just print what would be sent
    --limit N    Maximum number of emails to send (default: no limit)
"""

import sys
import os
from datetime import datetime
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytz
from database import get_users_with_expired_subscriptions, update_expiry_email_sent
from email_service import send_subscription_expiry_email, get_first_name

# India timezone
IST = pytz.timezone('Asia/Kolkata')


def calculate_days_since_expiry(expiry_timestamp) -> int:
    """Calculate days since subscription expired."""
    if expiry_timestamp is None:
        return 0

    if isinstance(expiry_timestamp, str):
        # Handle ISO format
        expiry_timestamp = datetime.fromisoformat(
            expiry_timestamp.replace('Z', '+00:00').replace(' ', 'T')
        )

    # Remove timezone info for comparison
    if hasattr(expiry_timestamp, 'tzinfo') and expiry_timestamp.tzinfo is not None:
        expiry_timestamp = expiry_timestamp.replace(tzinfo=None)

    return (datetime.now() - expiry_timestamp).days


def get_plan_display_name(tier: str) -> str:
    """Get display name for subscription tier."""
    names = {
        'basic': 'Basic',
        'pro': 'Pro',
        'enterprise': 'Enterprise',
    }
    return names.get(tier, tier.title())


def main():
    parser = argparse.ArgumentParser(description='Send expiry reminder emails')
    parser.add_argument('--dry-run', action='store_true', help="Don't send, just show what would be sent")
    parser.add_argument('--limit', type=int, default=0, help='Max emails to send (0 = no limit)')
    args = parser.parse_args()

    # Get current IST time
    now_ist = datetime.now(IST)
    print(f"[EXPIRY] Starting at {now_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Get users with expired subscriptions
    users = get_users_with_expired_subscriptions()
    print(f"[EXPIRY] Found {len(users)} users with expired subscriptions")

    if args.limit > 0:
        users = users[:args.limit]
        print(f"[EXPIRY] Limited to {len(users)} users")

    sent_count = 0
    failed_count = 0

    for user in users:
        user_id = user.get('id')
        email = user.get('email')
        full_name = user.get('full_name', '')
        first_name = get_first_name(full_name)
        tier = user.get('subscription_tier', 'basic')
        plan_name = get_plan_display_name(tier)
        expiry_date = user.get('subscription_expires_at')
        reports_generated = user.get('reports_generated', 0)

        days_since_expiry = calculate_days_since_expiry(expiry_date)

        print(f"\n[EXPIRY] Processing: {email}")
        print(f"  - Plan: {plan_name}")
        print(f"  - Expired: {days_since_expiry} days ago")
        print(f"  - Reports generated: {reports_generated}")

        if args.dry_run:
            print(f"  - [DRY RUN] Would send expiry email")
            sent_count += 1
            continue

        # Send expiry email
        try:
            success = send_subscription_expiry_email(
                user_email=email,
                first_name=first_name,
                plan_name=plan_name,
                days_since_expiry=days_since_expiry,
                reports_generated=reports_generated
            )

            if success:
                update_expiry_email_sent(user_id)
                print(f"  - ✓ Email sent successfully")
                sent_count += 1
            else:
                print(f"  - ✗ Failed to send email")
                failed_count += 1

        except Exception as e:
            print(f"  - ✗ Error: {e}")
            failed_count += 1

    # Summary
    print(f"\n[EXPIRY] Completed:")
    print(f"  - Sent: {sent_count}")
    print(f"  - Failed: {failed_count}")
    print(f"  - Total processed: {len(users)}")


if __name__ == "__main__":
    main()
