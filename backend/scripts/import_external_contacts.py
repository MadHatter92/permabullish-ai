#!/usr/bin/env python3
"""
Import External Contacts Script

Imports email contacts from CSV files (Resend audience export format) into the
external_contacts table for re-engagement email campaigns.

CSV Format Expected:
    id,created_at,first_name,last_name,email,unsubscribed

Usage:
    python import_external_contacts.py <csv_file> [<csv_file2> ...]
    python import_external_contacts.py --list  # List current contacts

Options:
    --dry-run    Don't actually import, just show what would be imported
    --list       List all external contacts in database
    --source     Custom source tag for imported contacts (default: filename)
"""

import sys
import os
import csv
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    init_database,
    add_external_contact,
    get_external_contact_count,
    get_external_contacts_for_reengagement,
)


def import_csv(filepath: str, source: str = None, dry_run: bool = False) -> tuple[int, int, int]:
    """
    Import contacts from a CSV file.

    Returns:
        Tuple of (imported, skipped, errors)
    """
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        return 0, 0, 1

    # Use filename as source if not provided
    if source is None:
        source = os.path.basename(filepath).replace('.csv', '')

    imported = 0
    skipped = 0
    errors = 0

    print(f"\nImporting from: {filepath}")
    print(f"Source tag: {source}")
    print("-" * 50)

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            email = row.get('email', '').strip().lower()

            if not email or '@' not in email:
                skipped += 1
                continue

            # Check if unsubscribed in source
            unsubscribed = row.get('unsubscribed', 'false').lower() == 'true'
            if unsubscribed:
                print(f"  Skipping (unsubscribed): {email}")
                skipped += 1
                continue

            first_name = row.get('first_name', '').strip() or None
            last_name = row.get('last_name', '').strip() or None

            if dry_run:
                print(f"  [DRY RUN] Would import: {email}")
                imported += 1
            else:
                result = add_external_contact(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    source=source
                )
                if result:
                    imported += 1
                    if imported <= 10 or imported % 50 == 0:
                        print(f"  Imported: {email}")
                else:
                    errors += 1
                    print(f"  Error importing: {email}")

    return imported, skipped, errors


def list_contacts():
    """List all external contacts in database."""
    contacts = get_external_contacts_for_reengagement()
    total = get_external_contact_count()

    print(f"\nExternal Contacts (Total: {total})")
    print("=" * 60)

    for contact in contacts[:50]:  # Show first 50
        email = contact['email']
        first_name = contact.get('first_name') or ''
        email_count = contact.get('reengagement_email_count', 0)
        print(f"  {email:<40} {first_name:<15} (emails: {email_count})")

    if len(contacts) > 50:
        print(f"  ... and {len(contacts) - 50} more")


def main():
    parser = argparse.ArgumentParser(description='Import external contacts from CSV files')
    parser.add_argument('files', nargs='*', help='CSV files to import')
    parser.add_argument('--dry-run', action='store_true', help="Don't import, just show what would happen")
    parser.add_argument('--list', action='store_true', help='List current contacts')
    parser.add_argument('--source', type=str, help='Custom source tag for imports')
    args = parser.parse_args()

    # Initialize database (creates table if needed)
    init_database()

    if args.list:
        list_contacts()
        return

    if not args.files:
        print("Usage: python import_external_contacts.py <csv_file> [<csv_file2> ...]")
        print("       python import_external_contacts.py --list")
        return

    total_imported = 0
    total_skipped = 0
    total_errors = 0

    for filepath in args.files:
        imported, skipped, errors = import_csv(
            filepath,
            source=args.source,
            dry_run=args.dry_run
        )
        total_imported += imported
        total_skipped += skipped
        total_errors += errors

    print("\n" + "=" * 50)
    print("IMPORT SUMMARY")
    print("=" * 50)
    print(f"  Imported: {total_imported}")
    print(f"  Skipped:  {total_skipped}")
    print(f"  Errors:   {total_errors}")
    print(f"  Total contacts in database: {get_external_contact_count()}")

    if args.dry_run:
        print("\n[DRY RUN] No changes were made to the database.")


if __name__ == "__main__":
    main()
