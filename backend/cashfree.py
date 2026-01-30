"""
Cashfree Payment Gateway Integration.
Handles order creation, payment verification, and webhook processing.
"""

import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Optional
import requests

from config import CASHFREE_APP_ID, CASHFREE_SECRET_KEY, CASHFREE_ENV, FRONTEND_URL


# API endpoints based on environment
CASHFREE_API_BASE = (
    "https://sandbox.cashfree.com/pg" if CASHFREE_ENV == "sandbox"
    else "https://api.cashfree.com/pg"
)


def get_headers() -> dict:
    """Get headers for Cashfree API requests."""
    return {
        "Content-Type": "application/json",
        "x-api-version": "2023-08-01",
        "x-client-id": CASHFREE_APP_ID,
        "x-client-secret": CASHFREE_SECRET_KEY,
    }


def create_order(
    order_id: str,
    amount: float,
    customer_id: str,
    customer_email: str,
    customer_name: str,
    customer_phone: str = "9999999999",
    return_url: str = None,
) -> dict:
    """
    Create a Cashfree payment order.

    Args:
        order_id: Unique order identifier
        amount: Order amount in INR
        customer_id: Customer identifier (user_id)
        customer_email: Customer email
        customer_name: Customer name
        customer_phone: Customer phone (required by Cashfree)
        return_url: URL to redirect after payment

    Returns:
        dict with payment_session_id and order details, or error
    """
    if not CASHFREE_APP_ID or not CASHFREE_SECRET_KEY:
        return {"success": False, "error": "Cashfree not configured"}

    url = f"{CASHFREE_API_BASE}/orders"

    if not return_url:
        return_url = f"{FRONTEND_URL}/payment-status.html?order_id={order_id}"

    payload = {
        "order_id": order_id,
        "order_amount": float(amount),
        "order_currency": "INR",
        "customer_details": {
            "customer_id": str(customer_id),
            "customer_email": customer_email,
            "customer_phone": customer_phone,
            "customer_name": customer_name,
        },
        "order_meta": {
            "return_url": return_url,
            "notify_url": f"{FRONTEND_URL.replace('permabullish.com', 'api.permabullish.com')}/api/webhooks/cashfree",
        },
        "order_note": f"Permabullish subscription - {order_id}",
    }

    try:
        response = requests.post(url, headers=get_headers(), json=payload)
        data = response.json()

        if response.status_code in [200, 201]:
            return {
                "success": True,
                "order_id": data.get("order_id"),
                "payment_session_id": data.get("payment_session_id"),
                "order_status": data.get("order_status"),
                "cf_order_id": data.get("cf_order_id"),
            }
        else:
            return {
                "success": False,
                "error": data.get("message", "Failed to create order"),
                "details": data,
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_order_status(order_id: str) -> dict:
    """
    Get the status of an order.

    Args:
        order_id: The order ID to check

    Returns:
        dict with order status details
    """
    if not CASHFREE_APP_ID or not CASHFREE_SECRET_KEY:
        return {"success": False, "error": "Cashfree not configured"}

    url = f"{CASHFREE_API_BASE}/orders/{order_id}"

    try:
        response = requests.get(url, headers=get_headers())
        data = response.json()

        if response.status_code == 200:
            return {
                "success": True,
                "order_id": data.get("order_id"),
                "order_status": data.get("order_status"),
                "order_amount": data.get("order_amount"),
                "cf_order_id": data.get("cf_order_id"),
            }
        else:
            return {
                "success": False,
                "error": data.get("message", "Failed to get order status"),
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_payment_details(order_id: str) -> dict:
    """
    Get payment details for an order.

    Args:
        order_id: The order ID

    Returns:
        dict with payment details including payment method, transaction ID, etc.
    """
    if not CASHFREE_APP_ID or not CASHFREE_SECRET_KEY:
        return {"success": False, "error": "Cashfree not configured"}

    url = f"{CASHFREE_API_BASE}/orders/{order_id}/payments"

    try:
        response = requests.get(url, headers=get_headers())
        data = response.json()

        if response.status_code == 200:
            # Return the latest successful payment if any
            payments = data if isinstance(data, list) else []
            successful_payment = None

            for payment in payments:
                if payment.get("payment_status") == "SUCCESS":
                    successful_payment = payment
                    break

            return {
                "success": True,
                "payments": payments,
                "successful_payment": successful_payment,
                "is_paid": successful_payment is not None,
            }
        else:
            return {
                "success": False,
                "error": data.get("message", "Failed to get payment details"),
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def verify_webhook_signature(payload: bytes, signature: str, timestamp: str) -> bool:
    """
    Verify Cashfree webhook signature.

    Args:
        payload: Raw request body bytes
        signature: x-webhook-signature header value
        timestamp: x-webhook-timestamp header value

    Returns:
        True if signature is valid
    """
    if not CASHFREE_SECRET_KEY:
        return False

    try:
        # Cashfree signature format: timestamp + payload
        string_to_sign = timestamp + str(payload.decode('utf-8'))
        computed_signature = hmac.new(
            CASHFREE_SECRET_KEY.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed_signature, signature)
    except Exception:
        return False


def parse_order_id_metadata(order_id: str) -> dict:
    """
    Parse metadata from order_id format: sub_{user_id}_{tier}_{period}m_{timestamp}

    Args:
        order_id: The order ID string

    Returns:
        dict with user_id, tier, period_months
    """
    try:
        parts = order_id.split("_")
        if len(parts) >= 4 and parts[0] == "sub":
            return {
                "user_id": int(parts[1]),
                "tier": parts[2],
                "period_months": int(parts[3].replace("m", "")),
            }
    except Exception:
        pass
    return {}


def generate_order_id(user_id: int, tier: str, period_months: int) -> str:
    """
    Generate a unique order ID.

    Format: sub_{user_id}_{tier}_{period}m_{timestamp}
    """
    timestamp = int(time.time())
    return f"sub_{user_id}_{tier}_{period_months}m_{timestamp}"


# Test function to verify credentials
def test_connection() -> dict:
    """Test Cashfree API connection with current credentials."""
    if not CASHFREE_APP_ID or not CASHFREE_SECRET_KEY:
        return {
            "success": False,
            "error": "Cashfree credentials not configured",
            "app_id_set": bool(CASHFREE_APP_ID),
            "secret_set": bool(CASHFREE_SECRET_KEY),
        }

    # Try to fetch a non-existent order (should return 404, not 401)
    url = f"{CASHFREE_API_BASE}/orders/test_connection_check"

    try:
        response = requests.get(url, headers=get_headers())

        if response.status_code == 401:
            return {
                "success": False,
                "error": "Invalid credentials",
                "status_code": response.status_code,
            }
        elif response.status_code == 404:
            # This is expected - credentials work but order doesn't exist
            return {
                "success": True,
                "message": "Cashfree credentials verified",
                "environment": CASHFREE_ENV,
            }
        else:
            return {
                "success": True,
                "message": f"Connection OK (status: {response.status_code})",
                "environment": CASHFREE_ENV,
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
