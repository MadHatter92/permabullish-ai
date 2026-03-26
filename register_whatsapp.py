"""
One-time script to register a WhatsApp number and subscribe the WABA to the app.
Run this when setting up a new WhatsApp number or after migration.

Usage:
    1. Fill in TOKEN, PHONE_NUMBER_ID, WABA_ID, and PIN below
    2. Run: python register_whatsapp.py
"""

import requests

TOKEN           = "YOUR_SYSTEM_USER_TOKEN"  # Permanent system user token from Meta Business Manager
PHONE_NUMBER_ID = "1011541565382226"        # From WhatsApp Manager -> Phone Numbers
WABA_ID         = "4560525840844943"        # WhatsApp Business Account ID
PIN             = "123456"                  # 6-digit 2FA pin (set once, remember it)

# Step 1: Register the phone number
print("=== Registering phone number ===")
r = requests.post(
    f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/register",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={"messaging_product": "whatsapp", "pin": PIN},
)
print(r.status_code, r.json())

# Step 2: Subscribe app to WABA (routes real messages to webhook)
print("\n=== Subscribing app to WABA ===")
r2 = requests.post(
    f"https://graph.facebook.com/v19.0/{WABA_ID}/subscribed_apps",
    headers={"Authorization": f"Bearer {TOKEN}"},
)
print(r2.status_code, r2.json())
