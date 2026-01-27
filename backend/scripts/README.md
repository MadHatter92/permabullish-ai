# Admin Scripts Guide

Scripts for user management, reporting, and data export.

---

## Quick Reference

| Task | Command |
|------|---------|
| Get all user emails | `python scripts/export_users.py --google-only --emails-only` |
| New users this week | `python scripts/weekly_new_users.py --days 7` |
| Export to CSV | `python scripts/export_users.py --format csv --output users.csv` |
| Send manual report | `python scripts/send_user_report.py daily` |

---

## 1. Export All Users (`export_users.py`)

Exports user data from the database with various filtering and format options.

### Basic Usage

```bash
cd backend

# View all users in a table
python scripts/export_users.py

# Google OAuth users only (recommended - these have verified emails)
python scripts/export_users.py --google-only
```

### Get Just Email Addresses

```bash
# All user emails (one per line)
python scripts/export_users.py --emails-only

# Only Google OAuth user emails
python scripts/export_users.py --google-only --emails-only

# Save to file
python scripts/export_users.py --google-only --emails-only --output user_emails.txt
```

### Export to Different Formats

```bash
# CSV (for Excel/Google Sheets)
python scripts/export_users.py --format csv --output users.csv

# JSON (for programmatic use)
python scripts/export_users.py --format json --output users.json

# Table (human-readable, default)
python scripts/export_users.py --format table
```

### All Options

| Option | Short | Description |
|--------|-------|-------------|
| `--google-only` | `-g` | Only Google OAuth users |
| `--include-inactive` | | Include deactivated users |
| `--format` | `-f` | Output format: `table`, `csv`, `json` |
| `--output` | `-o` | Save to file instead of printing |
| `--emails-only` | `-e` | Output only email addresses |

---

## 2. New Users Report (`weekly_new_users.py`)

Get users who signed up within a specific time period.

### Basic Usage

```bash
# New users from last 7 days (default)
python scripts/weekly_new_users.py

# New users from last 30 days
python scripts/weekly_new_users.py --days 30

# New users from yesterday only
python scripts/weekly_new_users.py --days 1
```

### Output Formats

```bash
# Detailed report (default)
python scripts/weekly_new_users.py --days 7

# Just email addresses
python scripts/weekly_new_users.py --days 7 --format emails

# CSV export
python scripts/weekly_new_users.py --days 7 --format csv --output new_users.csv

# JSON export
python scripts/weekly_new_users.py --days 30 --format json --output new_users.json
```

### All Options

| Option | Short | Description |
|--------|-------|-------------|
| `--days` | `-d` | Number of days to look back (default: 7) |
| `--google-only` | `-g` | Only Google OAuth users |
| `--format` | `-f` | Output format: `report`, `csv`, `json`, `emails` |
| `--output` | `-o` | Save to file instead of printing |
| `--no-stats` | | Skip usage statistics in report |

---

## 3. Send User Report (`send_user_report.py`)

Manually trigger the daily/weekly email reports (same as the Render cron jobs).

### Prerequisites

Set environment variables:
```bash
# Required
export RESEND_API_KEY=re_your_api_key_here
export REPORT_EMAIL_TO=mail@mayaskara.com

# OR use SMTP instead
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your@gmail.com
export SMTP_PASSWORD=your_app_password
```

### Usage

```bash
# Send daily report (new users from last 24 hours)
python scripts/send_user_report.py daily

# Send weekly report (new users from last 7 days)
python scripts/send_user_report.py weekly
```

### What the Report Contains

1. **Platform Overview**
   - Total users
   - Google OAuth users count
   - Total reports generated

2. **New Users List**
   - Email address
   - Full name
   - Auth provider (Google/Email)
   - Join date
   - Number of reports generated

---

## Running on Production (Render)

### Option A: Use Render Shell

1. Go to Render Dashboard → `permabullish-api` service
2. Click "Shell" to open a terminal
3. Run:
   ```bash
   cd /opt/render/project/src/backend
   python scripts/export_users.py --google-only --emails-only
   ```

### Option B: Trigger Cron Job Manually

1. Go to Render Dashboard → `permabullish-daily-report` or `permabullish-weekly-report`
2. Click "Trigger Run" to send a report immediately

### Option C: Connect to Production Database Locally

```bash
# Set the DATABASE_URL from Render dashboard
export DATABASE_URL="postgresql://user:pass@host:5432/db"

# Run scripts locally against production
python scripts/export_users.py --google-only
```

---

## Common Use Cases

### Marketing: Get all verified emails for newsletter

```bash
python scripts/export_users.py --google-only --emails-only --output marketing_list.txt
```

### Analytics: Weekly growth tracking

```bash
python scripts/weekly_new_users.py --days 7 --format csv --output weekly_growth.csv
```

### Investor Update: Total user count

```bash
python scripts/export_users.py --google-only --format json
# Look at the total count at the bottom
```

---

## Automated Reports (Render Cron Jobs)

The following cron jobs are configured in `render.yaml`:

| Job | Schedule | Description |
|-----|----------|-------------|
| `permabullish-daily-report` | 9:00 AM UTC daily | New users from last 24 hours |
| `permabullish-weekly-report` | Monday 9:00 AM UTC | New users from last 7 days |

### Environment Variables Required

Set these in Render Dashboard for the cron jobs:

| Variable | Value |
|----------|-------|
| `RESEND_API_KEY` | Your Resend API key |
| `REPORT_EMAIL_TO` | `mail@mayaskara.com` |
| `DATABASE_URL` | (auto-linked from database) |

---

## Troubleshooting

### "No module named 'database'"

Make sure you're running from the `backend` directory:
```bash
cd backend
python scripts/export_users.py
```

### "No users found"

- Check if the database is connected (DATABASE_URL set correctly)
- Verify users have been created via the app

### Email not sending

- Verify `RESEND_API_KEY` is set correctly
- Check Resend dashboard for delivery logs
- Try the SMTP fallback if Resend isn't working
