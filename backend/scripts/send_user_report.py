#!/usr/bin/env python3
"""
Send user report via email. Designed to run as a Render Cron Job.

Usage:
    python scripts/send_user_report.py daily    # Daily new users report
    python scripts/send_user_report.py weekly   # Weekly new users report

Environment variables required:
    REPORT_EMAIL_TO      - Recipient email address
    RESEND_API_KEY       - Resend API key (or use SMTP vars below)

    # Alternative: SMTP
    SMTP_HOST            - SMTP server host
    SMTP_PORT            - SMTP server port (default: 587)
    SMTP_USER            - SMTP username
    SMTP_PASSWORD        - SMTP password
    SMTP_FROM            - From email address
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import get_db_connection, get_cursor, placeholder, USE_POSTGRES, _dict_from_row


def get_new_users(days: int = 7) -> list[dict]:
    """Fetch users created in the last N days."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        query = f"""
            SELECT id, email, full_name, google_id, auth_provider, created_at, signup_source
            FROM users
            WHERE created_at >= {p}
        """

        if USE_POSTGRES:
            query += " AND is_active = TRUE"
        else:
            query += " AND is_active = 1"

        query += " ORDER BY created_at DESC"

        cursor.execute(query, (cutoff,))
        rows = cursor.fetchall()

    return [_dict_from_row(row) for row in rows]


def get_usage_stats(user_id: int) -> dict:
    """Get usage stats for a user."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()

        # Count total reports viewed/generated
        cursor.execute(f"SELECT COUNT(*) as count FROM user_reports WHERE user_id = {p}", (user_id,))
        row = cursor.fetchone()
        total_reports = _dict_from_row(row)["count"] if row else 0

        # Get current month usage (reports generated, not just viewed)
        month_year = datetime.now().strftime("%Y-%m")
        cursor.execute(
            f"SELECT reports_generated FROM usage WHERE user_id = {p} AND month_year = {p}",
            (user_id, month_year)
        )
        row = cursor.fetchone()
        monthly_generated = _dict_from_row(row)["reports_generated"] if row else 0

        # Get list of companies researched (most recent 5)
        cursor.execute(f"""
            SELECT rc.ticker, rc.company_name, ur.first_viewed_at
            FROM user_reports ur
            JOIN report_cache rc ON ur.report_cache_id = rc.id
            WHERE ur.user_id = {p}
            ORDER BY ur.first_viewed_at DESC
            LIMIT 5
        """, (user_id,))
        rows = cursor.fetchall()
        companies = [f"{_dict_from_row(r)['ticker']}" for r in rows]

    return {
        "total_reports": total_reports,
        "monthly_generated": monthly_generated,
        "companies": companies
    }


def get_total_stats(days: int = 7) -> dict:
    """Get overall platform stats."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_active = TRUE")
        else:
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_active = 1")
        total_users = _dict_from_row(cursor.fetchone())["count"]

        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE google_id IS NOT NULL AND is_active = TRUE")
        else:
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE google_id IS NOT NULL AND is_active = 1")
        google_users = _dict_from_row(cursor.fetchone())["count"]

        # Total unique reports in cache
        cursor.execute("SELECT COUNT(*) as count FROM report_cache")
        total_cached_reports = _dict_from_row(cursor.fetchone())["count"]

        # Reports generated in period
        cursor.execute(f"SELECT COUNT(*) as count FROM report_cache WHERE generated_at >= {p}", (cutoff,))
        reports_in_period = _dict_from_row(cursor.fetchone())["count"]

        # Total report views (user-report links)
        cursor.execute("SELECT COUNT(*) as count FROM user_reports")
        total_report_views = _dict_from_row(cursor.fetchone())["count"]

        # Most popular stocks (top 5)
        cursor.execute("""
            SELECT rc.ticker, rc.company_name, COUNT(ur.id) as view_count
            FROM report_cache rc
            LEFT JOIN user_reports ur ON rc.id = ur.report_cache_id
            GROUP BY rc.id, rc.ticker, rc.company_name
            ORDER BY view_count DESC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        popular_stocks = [f"{_dict_from_row(r)['ticker']} ({_dict_from_row(r)['view_count']} views)" for r in rows]

        # Watchlist stats
        cursor.execute("SELECT COUNT(*) as count FROM watchlist")
        total_watchlist_items = _dict_from_row(cursor.fetchone())["count"]

        # Token usage stats (total and in period)
        cursor.execute("SELECT COALESCE(SUM(total_tokens), 0) as total FROM report_cache")
        row = cursor.fetchone()
        total_tokens_all_time = _dict_from_row(row)["total"] if row else 0

        cursor.execute(f"SELECT COALESCE(SUM(total_tokens), 0) as total FROM report_cache WHERE generated_at >= {p}", (cutoff,))
        row = cursor.fetchone()
        total_tokens_in_period = _dict_from_row(row)["total"] if row else 0

        # Estimate cost (₹3 per report or based on tokens)
        # Claude Sonnet: $3/1M input, $15/1M output ~ roughly $0.028 per report ~ ₹2.35
        estimated_cost_period = (total_tokens_in_period / 2850) * 2.35 if total_tokens_in_period > 0 else reports_in_period * 3

    return {
        "total_users": total_users,
        "google_users": google_users,
        "total_cached_reports": total_cached_reports,
        "reports_in_period": reports_in_period,
        "total_report_views": total_report_views,
        "popular_stocks": popular_stocks,
        "total_watchlist_items": total_watchlist_items,
        "total_tokens_all_time": total_tokens_all_time,
        "total_tokens_in_period": total_tokens_in_period,
        "estimated_cost_period": estimated_cost_period,
    }


def generate_report(period: str = "daily") -> tuple[str, str]:
    """Generate email subject and body."""
    days = 1 if period == "daily" else 7
    period_label = "Daily" if period == "daily" else "Weekly"

    users = get_new_users(days=days)
    stats = get_total_stats(days=days)

    # Subject
    reports_in_period = stats.get('reports_in_period', 0)
    subject = f"[Permabullish] {period_label} Report - {len(users)} new users, {reports_in_period} reports"

    # Body
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"PERMABULLISH - {period_label.upper()} REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"Period: Last {days} day{'s' if days > 1 else ''}")
    lines.append(f"{'='*60}")
    lines.append("")

    # Platform stats
    lines.append("PLATFORM OVERVIEW")
    lines.append("-" * 40)
    lines.append(f"Total Users:         {stats['total_users']}")
    lines.append(f"Google OAuth Users:  {stats['google_users']}")
    lines.append(f"Unique Reports:      {stats['total_cached_reports']}")
    lines.append(f"Total Report Views:  {stats['total_report_views']}")
    lines.append(f"Watchlist Items:     {stats['total_watchlist_items']}")
    lines.append("")

    # Period activity
    lines.append(f"ACTIVITY (Last {days} day{'s' if days > 1 else ''})")
    lines.append("-" * 40)
    lines.append(f"New Users:           {len(users)}")
    lines.append(f"Reports Generated:   {stats['reports_in_period']}")
    lines.append(f"Tokens Used:         {stats['total_tokens_in_period']:,}")
    lines.append(f"Est. Cost:           ₹{stats['estimated_cost_period']:.2f}")
    lines.append("")

    # All-time token stats
    if stats['total_tokens_all_time'] > 0:
        lines.append("TOKEN USAGE (All Time)")
        lines.append("-" * 40)
        lines.append(f"Total Tokens:        {stats['total_tokens_all_time']:,}")
        all_time_cost = (stats['total_tokens_all_time'] / 2850) * 2.35
        lines.append(f"Est. Total Cost:     ₹{all_time_cost:.2f}")
        lines.append("")

    # Popular stocks
    if stats.get('popular_stocks'):
        lines.append("TOP STOCKS (by views)")
        lines.append("-" * 40)
        for i, stock in enumerate(stats['popular_stocks'], 1):
            lines.append(f"  {i}. {stock}")
        lines.append("")

    # Signup source breakdown
    if users:
        source_counts = {}
        for u in users:
            source = u.get("signup_source") or ""
            if not source:
                if u.get("google_id"):
                    source = "google_oauth"
                else:
                    source = "(direct)"
            source_counts[source] = source_counts.get(source, 0) + 1

        lines.append("SIGNUP SOURCE BREAKDOWN")
        lines.append("-" * 40)
        for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {source}: {count}")
        lines.append("")

    # New users
    lines.append(f"NEW USERS ({len(users)})")
    lines.append("-" * 40)

    if not users:
        lines.append("No new users in this period.")
    else:
        google_count = sum(1 for u in users if u.get("google_id"))
        lines.append(f"Google OAuth: {google_count} | Email/Password: {len(users) - google_count}")
        lines.append("")

        for i, user in enumerate(users, 1):
            usage = get_usage_stats(user["id"])
            provider = "Google" if user.get("google_id") else "Email"
            source = user.get("signup_source") or ""
            lines.append(f"{i}. {user['email']}")
            lines.append(f"   Name: {user['full_name']} | Provider: {provider}")
            if source:
                lines.append(f"   Source: {source}")
            lines.append(f"   Joined: {user['created_at']}")
            lines.append(f"   Reports: {usage['total_reports']} total, {usage['monthly_generated']} this month")
            if usage.get('companies'):
                lines.append(f"   Stocks: {', '.join(usage['companies'])}")
            lines.append("")

    lines.append("-" * 40)
    lines.append("End of report.")
    lines.append("")
    lines.append("--")
    lines.append("Permabullish")
    lines.append("https://permabullish.com")

    return subject, "\n".join(lines)


def send_via_resend(to_email: str, subject: str, body: str) -> bool:
    """Send email via Resend official SDK."""
    import resend

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("Error: RESEND_API_KEY not set")
        return False

    resend.api_key = api_key

    try:
        params = {
            "from": "Permabullish <hello@permabullish.com>",
            "to": [to_email],
            "subject": subject,
            "text": body,
        }

        email = resend.Emails.send(params)
        print(f"Email sent successfully: {email.get('id')}")
        return True

    except resend.exceptions.ResendError as e:
        print(f"Resend API error: {e}")
        return False
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_via_smtp(to_email: str, subject: str, body: str) -> bool:
    """Send email via SMTP."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass]):
        print("Error: SMTP configuration incomplete")
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python send_user_report.py [daily|weekly]")
        sys.exit(1)

    period = sys.argv[1].lower()
    if period not in ["daily", "weekly"]:
        print("Error: Period must be 'daily' or 'weekly'")
        sys.exit(1)

    to_email = os.environ.get("REPORT_EMAIL_TO")
    if not to_email:
        print("Error: REPORT_EMAIL_TO environment variable not set")
        sys.exit(1)

    print(f"Generating {period} report...")
    subject, body = generate_report(period)

    print(f"Sending to {to_email}...")

    # Try Resend first, fall back to SMTP
    if os.environ.get("RESEND_API_KEY"):
        success = send_via_resend(to_email, subject, body)
    elif os.environ.get("SMTP_HOST"):
        success = send_via_smtp(to_email, subject, body)
    else:
        print("Error: No email configuration found")
        print("Set RESEND_API_KEY or SMTP_* environment variables")
        print("\nReport preview:")
        print("-" * 40)
        print(body)
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
