# Permabullish Admin Guide

## Overview

This guide covers administrative operations for managing users and subscriptions.

**Important:** All admin endpoints require the `ADMIN_SECRET` environment variable to be set and passed as a query parameter.

---

## Adding Enterprise Users

### Prerequisites
1. User must have signed in at least once via Google OAuth
2. You need the user's email address
3. You need the `ADMIN_SECRET`

### Step 1: Verify User Exists

```bash
curl "https://api.permabullish.com/api/admin/user-info/client@company.com?secret=YOUR_ADMIN_SECRET"
```

Response:
```json
{
  "user": {
    "id": 123,
    "email": "client@company.com",
    "name": "Client Name",
    "created_at": "2026-01-30T10:00:00"
  },
  "subscription": {
    "tier": "free",
    "is_expired": true
  },
  "usage": {
    "reports_used": 2,
    "reports_limit": 5
  }
}
```

### Step 2: Set Enterprise Subscription

```bash
curl -X POST "https://api.permabullish.com/api/admin/set-subscription?secret=YOUR_ADMIN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "client@company.com",
    "tier": "enterprise",
    "period_months": 12,
    "amount_paid": 50000,
    "note": "Enterprise - Company XYZ - Invoice #1234"
  }'
```

Response:
```json
{
  "success": true,
  "message": "Subscription set for client@company.com",
  "user_id": 123,
  "subscription_id": 456,
  "tier": "enterprise",
  "period_months": 12,
  "expires_at": "2027-01-30T10:00:00"
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string | Yes | User's email (must exist in system) |
| `tier` | string | Yes | `free`, `basic`, `pro`, or `enterprise` |
| `period_months` | int | No | Duration in months (default: 12) |
| `amount_paid` | float | No | Amount for record-keeping (default: 0) |
| `note` | string | No | Reference note (appears in payment_id) |

---

## Other Admin Endpoints

### Reset User Usage
Reset a user's monthly report quota (for testing or support):

```bash
curl -X POST "https://api.permabullish.com/api/admin/reset-usage/user@email.com?secret=YOUR_ADMIN_SECRET"
```

### Check Provider Status
View status of stock data providers:

```bash
curl "https://api.permabullish.com/api/admin/provider-status?secret=YOUR_ADMIN_SECRET"
```

### Reset Rate Limits
Reset rate limits on stock data providers:

```bash
curl -X POST "https://api.permabullish.com/api/admin/reset-rate-limits?secret=YOUR_ADMIN_SECRET"
```

### Test Cashfree Connection
Verify Cashfree API is working:

```bash
curl "https://api.permabullish.com/api/admin/test-cashfree?secret=YOUR_ADMIN_SECRET"
```

---

## Security Notes

1. **Never share the ADMIN_SECRET**
2. **Change the default secret** - The code has a default value; always override via environment variable
3. **Use HTTPS only** - Admin endpoints should never be called over HTTP
4. **Audit trail** - The `note` field in subscriptions helps track why/when enterprise accounts were created

---

## Common Scenarios

### Extending an Enterprise Subscription
Just call set-subscription again with a new period. It creates a new subscription record starting from now.

### Downgrading a User
Set their tier to the lower tier. Note: This takes effect immediately.

### Comped/Free Upgrade
Set `amount_paid: 0` and use the `note` field to explain why (e.g., "Beta tester reward").

---

*Last updated: January 30, 2026*
