"""
WhatsApp Bot for Permabullish
Handles incoming messages via Meta WhatsApp Cloud API webhook.
"""

import os
import re
import json
import hmac
import math
import hashlib
import asyncio
import logging
from io import BytesIO
from datetime import datetime, timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response

import database as db
from yahoo_finance import search_stocks
from share_card import generate_share_card
from config import FRONTEND_URL, is_us_exchange

logger = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────

WHATSAPP_ACCESS_TOKEN    = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_APP_SECRET      = os.getenv("WHATSAPP_APP_SECRET", "")
WHATSAPP_VERIFY_TOKEN    = os.getenv("WHATSAPP_VERIFY_TOKEN", "pb_whatsapp_2026")

GRAPH_API_URL = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
SEND_HEADERS  = {
    "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

SESSION_TTL_MINUTES = 5

# Monthly report limits by subscription tier (None = unlinked phone)
MONTHLY_LIMITS = {
    None:         3,
    "free":       5,
    "basic":      50,
    "pro":        100,
    "enterprise": 10000,
}

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

_executor = ThreadPoolExecutor(max_workers=4)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()


def _verify_signature(body: bytes, signature: str) -> bool:
    if not WHATSAPP_APP_SECRET:
        return True  # Skip check in dev if secret not set
    expected = "sha256=" + hmac.new(
        WHATSAPP_APP_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


def _looks_like_email(text: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", text.strip()))


def _next_month_reset() -> str:
    """Return human-readable reset date (e.g. 'April 1')."""
    now = datetime.now()
    first_next = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    return first_next.strftime("%B 1")


def _get_phone_tier(phone_hash: str) -> Optional[str]:
    """Return subscription tier for this phone, or None if unlinked."""
    account = db.get_whatsapp_account(phone_hash)
    if not account or not account.get("user_id"):
        return None
    user = db.get_user_by_id(account["user_id"])
    if not user:
        return None
    return user.get("subscription_tier") or "free"


_PORTFOLIO_KEYWORDS = {
    "portfolio", "my portfolio", "analyze portfolio", "analyse portfolio",
    "check portfolio", "portfolio analysis", "portfolio review",
    "review portfolio", "analyze my portfolio", "analyse my portfolio",
    "review my portfolio", "check my portfolio", "analyse my investments",
    "analyze my investments", "portfolio check",
}

def _is_portfolio_request(text: str) -> bool:
    t = text.lower().strip()
    return any(kw in t for kw in _PORTFOLIO_KEYWORDS)


def _classify_market_cap(market_cap: Optional[float], is_us: bool) -> str:
    """Classify a stock as Large / Mid / Small cap."""
    if not market_cap:
        return "Unknown"
    if is_us:
        if market_cap >= 10e9:
            return "Large Cap"
        elif market_cap >= 2e9:
            return "Mid Cap"
        return "Small Cap"
    else:
        crore = 1e7  # 1 Cr = 10M
        if market_cap >= 20_000 * crore:
            return "Large Cap"
        elif market_cap >= 5_000 * crore:
            return "Mid Cap"
        return "Small Cap"


async def _download_whatsapp_media(media_id: str) -> Optional[bytes]:
    """Fetch binary content of a WhatsApp media object."""
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"https://graph.facebook.com/v19.0/{media_id}",
            headers=headers,
        )
        if r.status_code != 200:
            logger.warning(f"Media metadata fetch failed {r.status_code}: {r.text}")
            return None
        media_url = r.json().get("url")
        if not media_url:
            return None
        r2 = await client.get(media_url, headers=headers)
        if r2.status_code != 200:
            logger.warning(f"Media download failed {r2.status_code}")
            return None
        return r2.content


# ─── Webhook Endpoints ────────────────────────────────────────────────────────

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Meta webhook verification handshake."""
    params = dict(request.query_params)
    if (params.get("hub.mode") == "subscribe" and
            params.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN):
        return Response(content=params["hub.challenge"], media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def handle_webhook(request: Request):
    """Receive and process incoming WhatsApp messages. Always returns 200."""
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")

    if not _verify_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        data = json.loads(body)
        entry   = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value   = changes.get("value", {})

        if "messages" not in value:
            return {"status": "ok"}  # Status update, not a message

        message  = value["messages"][0]
        phone    = message["from"]
        msg_type = message["type"]

        # Acknowledge read immediately (fire and forget)
        asyncio.create_task(_mark_read(message["id"]))
        _log_event(phone, "message_received", metadata={"type": msg_type})

        if msg_type == "text":
            query = message["text"]["body"].strip()
            asyncio.create_task(_handle_text(phone, query))

        elif msg_type == "interactive":
            interactive = message["interactive"]
            itype = interactive.get("type")
            if itype == "list_reply":
                selection_id = interactive["list_reply"]["id"]
            elif itype == "button_reply":
                selection_id = interactive["button_reply"]["id"]
            else:
                selection_id = None

            if selection_id:
                asyncio.create_task(_handle_selection(phone, selection_id))

        elif msg_type == "image":
            caption  = message.get("image", {}).get("caption", "").strip()
            media_id = message.get("image", {}).get("id", "")
            if _is_portfolio_request(caption):
                asyncio.create_task(_handle_portfolio_image(phone, media_id))
            else:
                asyncio.create_task(_send_unhandled_type(phone))
                _log_event(phone, "unhandled_message_type",
                           metadata={"type": msg_type, "caption": caption[:80]})

        else:
            asyncio.create_task(_send_unhandled_type(phone))
            _log_event(phone, "unhandled_message_type",
                       metadata={"type": msg_type}, flagged=True)

    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}", exc_info=True)
        _log_event("unknown", "api_error", metadata={"error": str(e)}, flagged=True)

    return {"status": "ok"}


# ─── Message Handlers ─────────────────────────────────────────────────────────

GREETINGS = {"hi", "hello", "hey", "hii", "helo", "namaste", "namaskar",
             "start", "help", "?", "sup", "yo", "good morning", "good evening",
             "good afternoon", "good night"}

WELCOME_MESSAGE = (
    "👋 Welcome to *Permabullish* — AI-powered stock research!\n\n"
    "Send me any stock name or ticker and I'll instantly send you:\n"
    "📊 Recommendation with target price\n"
    "📝 AI analysis summary\n\n"
    "Try it — send *RELIANCE*, *TCS*, *INFY*, or any NSE/BSE/NYSE/NASDAQ stock.\n\n"
    "🆓 *3 free reports/month* — no sign-up needed.\n"
    "🔗 More at permabullish.com"
)


async def _handle_text(phone: str, text: str):
    """Route incoming text: greeting, email linking, portfolio, or stock search."""
    if text.lower().strip() in GREETINGS:
        await _send_text(phone, WELCOME_MESSAGE)
        return

    if _looks_like_email(text):
        await _handle_account_link(phone, text.strip().lower())
        return

    if _is_portfolio_request(text):
        await _send_text(
            phone,
            "📊 *Portfolio Analysis*\n\n"
            "Send me a screenshot of your portfolio and I'll analyze:\n"
            "• Sector & industry allocation\n"
            "• Large / Mid / Small cap mix\n"
            "• Concentration & risk assessment\n"
            "• Recent news on your holdings\n"
            "• Personalized suggestions\n\n"
            "Just send the screenshot with *portfolio* as the caption 👆"
        )
        return

    # Clear any stale disambiguation session
    db.clear_whatsapp_session(_hash_phone(phone))

    results = search_stocks(text, limit=8)

    if not results:
        _log_event(phone, "unmatched_query", query_text=text, flagged=True)
        await _send_text(
            phone,
            f"Couldn't find *{text}*. Try the NSE/BSE ticker "
            "(e.g. RELIANCE, TCS, INFY) or the full company name."
        )
        return

    # Exact ticker match → go direct
    exact = [r for r in results if r["symbol"].upper() == text.upper()]
    if len(exact) == 1:
        _log_event(phone, "stock_resolved_exact", ticker=exact[0]["symbol"])
        await _send_report(phone, exact[0]["symbol"], exact[0]["exchange"])
        return

    # 2–3 results → reply buttons
    if len(results) <= 3:
        _log_event(phone, "disambiguation_shown")
        db.save_whatsapp_session(_hash_phone(phone), "awaiting_selection", results)
        await _send_reply_buttons(phone, results)
        return

    # 4+ results → interactive list
    _log_event(phone, "disambiguation_shown")
    db.save_whatsapp_session(_hash_phone(phone), "awaiting_selection", results[:8])
    await _send_interactive_list(phone, results[:8], text)


async def _handle_selection(phone: str, selection_id: str):
    """Route interactive reply: action button or disambiguation selection."""
    # Action buttons have the prefix ACT_
    if selection_id.startswith("ACT_"):
        await _handle_action(phone, selection_id)
        return

    # Disambiguation: format is TICKER_EXCHANGE
    parts = selection_id.split("_", 1)
    if len(parts) != 2:
        await _send_text(phone, "Sorry, I didn't understand that. Please send the stock name again.")
        return

    ticker, exchange = parts[0], parts[1]
    db.clear_whatsapp_session(_hash_phone(phone))
    _log_event(phone, "disambiguation_selected", ticker=ticker,
               metadata={"exchange": exchange})
    await _send_report(phone, ticker, exchange)


async def _handle_action(phone: str, action_id: str):
    """Handle an action button: ACT_B/R/N_TICKER_EXCHANGE."""
    parts = action_id.split("_", 3)
    if len(parts) != 4:
        await _send_text(phone, "Invalid action. Please try again.")
        return

    _, action_code, ticker, exchange = parts

    # Gate: require linked account
    phone_hash = _hash_phone(phone)
    account = db.get_whatsapp_account(phone_hash)
    is_linked = account and account.get("user_id")

    if not is_linked:
        await _send_text(
            phone,
            "🔐 *Charts, Results and News* require a linked account.\n\n"
            "Reply with your Permabullish email to link, or sign up free at permabullish.com"
        )
        return

    _log_event(phone, f"action_{action_code.lower()}", ticker=ticker,
               metadata={"exchange": exchange})

    if action_code == "B":
        await _send_bull_bear_action(phone, ticker, exchange)
    elif action_code == "R":
        await _send_results_action(phone, ticker, exchange)
    elif action_code == "N":
        await _send_news_action(phone, ticker, exchange)
    else:
        await _send_text(phone, "Unknown action. Please try again.")


async def _handle_account_link(phone: str, email: str):
    """Try to link a WhatsApp number to a Permabullish account by email."""
    phone_hash = _hash_phone(phone)
    user = db.get_user_by_email(email)
    if not user:
        await _send_text(
            phone,
            f"No Permabullish account found for {email}. "
            "Sign up at permabullish.com to create one."
        )
        return

    db.link_whatsapp_account(phone_hash, user["id"], phone_number=f"+{phone}")
    _log_event(phone, "account_linked", metadata={"user_id": user["id"]})

    tier  = user.get("subscription_tier", "free")
    limit = MONTHLY_LIMITS.get(tier, 5)
    await _send_text(
        phone,
        f"✅ *Linked!* Your WhatsApp is connected to your Permabullish account ({email}).\n\n"
        f"You now have *{limit} reports/month* on your {tier.title()} plan.\n"
        "Send any stock name or ticker to get an analysis."
    )


async def _send_report(phone: str, ticker: str, exchange: str):
    """Check monthly limit, then fetch/generate and deliver a report."""
    ticker    = ticker.upper()
    exchange  = exchange.upper()
    phone_hash = _hash_phone(phone)
    month_year = datetime.now().strftime("%Y-%m")

    # ── Usage gate ──────────────────────────────────────────────────────────
    tier  = _get_phone_tier(phone_hash)
    limit = MONTHLY_LIMITS.get(tier, 3)
    count = db.get_whatsapp_monthly_count(phone_hash, month_year)

    if count >= limit:
        await _send_limit_blocked_nudge(phone, tier, limit)
        _log_event(phone, "report_blocked_limit", ticker=ticker,
                   metadata={"count": count, "limit": limit, "tier": tier})
        return

    # ── Fetch / generate report ──────────────────────────────────────────────
    cached = db.get_cached_report(ticker, exchange, language="en")

    if not cached:
        await _send_text(
            phone,
            f"Fetching analysis for *{ticker}*... This takes about 30 seconds ⏳"
        )
        try:
            loop = asyncio.get_event_loop()
            cached = await loop.run_in_executor(_executor, _generate_report, ticker, exchange)
        except Exception as e:
            logger.error(f"Report generation error for {ticker}: {e}", exc_info=True)
            await _send_text(
                phone,
                f"Something went wrong generating the report for *{ticker}*. "
                "Please try again or email mail@mayaskara.com"
            )
            _log_event(phone, "api_error", ticker=ticker,
                       metadata={"error": str(e)}, flagged=True)
            return

    if not cached:
        await _send_text(phone, f"Couldn't fetch data for *{ticker}*. Please try again later.")
        _log_event(phone, "api_error", ticker=ticker, flagged=True)
        return

    # ── Deliver report (card + text) ─────────────────────────────────────────
    _log_event(phone, "report_sent", ticker=ticker)

    api_base = "https://api.permabullish.com"
    card_url  = f"{api_base}/whatsapp/card/{ticker}.png?exchange={exchange}"

    rec = cached.get("recommendation", "HOLD").replace("_", " ").title()
    await _send_image(phone, card_url, f"*{ticker}* — {rec}")
    await asyncio.sleep(0.8)
    await _send_text(phone, _format_report_text(cached, ticker, exchange, cached.get("id")))

    # ── Increment usage ───────────────────────────────────────────────────────
    new_count = db.increment_whatsapp_monthly_count(phone_hash, month_year)

    # ── Action buttons ────────────────────────────────────────────────────────
    await asyncio.sleep(0.5)
    await _send_action_buttons(phone, ticker, exchange)

    # ── Post-report nudges ────────────────────────────────────────────────────
    account = db.get_whatsapp_account(phone_hash)
    is_linked = account and account.get("user_id")

    if not is_linked:
        if not account:
            # First ever report — create record and send linking prompt
            db.create_whatsapp_account(phone_hash, phone_number=f"+{phone}")
            await asyncio.sleep(1.5)
            if new_count >= limit:
                # Also just hit the free cap
                await _send_text(
                    phone,
                    f"📊 You've used all {limit} free reports this month. They reset on {_next_month_reset()}.\n\n"
                    "💡 Link your account for 5 free reports/month — reply with your email, "
                    "or upgrade at permabullish.com"
                )
            else:
                await _send_text(
                    phone,
                    "💼 Have a Permabullish account? Reply with your email to link it "
                    "and get *5 free reports/month* plus charts, results and news."
                )
        elif new_count >= limit:
            # Hit the free cap on a known-but-unlinked number
            await asyncio.sleep(1.5)
            await _send_limit_exhausted_nudge(phone, tier, limit)


def _generate_report(ticker: str, exchange: str) -> Optional[dict]:
    """Synchronous report generation — run in executor to avoid blocking event loop."""
    from yahoo_finance import fetch_stock_data
    from report_generator import generate_ai_analysis, generate_report_html

    stock_data = fetch_stock_data(ticker, exchange)
    if not stock_data:
        return None

    analysis    = generate_ai_analysis(stock_data, "en", exchange=exchange)
    report_html = generate_report_html(stock_data, analysis, "en", exchange=exchange)

    basic = stock_data.get("basic_info", {})
    price = stock_data.get("price_info", {})
    token_usage = analysis.get("_token_usage", {})

    report_cache_id = db.save_cached_report(
        ticker=ticker,
        exchange=exchange,
        company_name=basic.get("company_name", ticker),
        sector=basic.get("sector", ""),
        current_price=price.get("current_price", 0),
        ai_target_price=analysis.get("target_price", 0),
        recommendation=analysis.get("recommendation", "HOLD"),
        report_html=report_html,
        report_data=json.dumps({"stock_data": stock_data, "analysis": analysis}),
        input_tokens=token_usage.get("input_tokens", 0),
        output_tokens=token_usage.get("output_tokens", 0),
        total_tokens=token_usage.get("total_tokens", 0),
        language="en",
    )
    return db.get_cached_report_by_id(report_cache_id)


def _format_report_text(cached: dict, ticker: str, exchange: str, report_id: int = None) -> str:
    """Format a compact WhatsApp text report from cached data."""
    company_name    = cached.get("company_name", ticker)
    recommendation  = cached.get("recommendation", "HOLD").replace("_", " ").upper()
    current_price   = cached.get("current_price") or 0
    ai_target_price = cached.get("ai_target_price") or 0
    currency        = "$" if is_us_exchange(exchange) else "₹"

    # Upside/downside %
    upside = ""
    if current_price and ai_target_price:
        pct  = ((ai_target_price - current_price) / current_price) * 100
        sign = "+" if pct >= 0 else ""
        upside = f" ({sign}{pct:.0f}%)"

    rec_emoji = {
        "STRONG BUY": "🟢", "BUY": "🟢",
        "HOLD": "🟡",
        "SELL": "🔴", "STRONG SELL": "🔴",
    }.get(recommendation, "⚪")

    # Extract structured fields from stored report_data JSON
    report_data = cached.get("report_data") or {}
    if isinstance(report_data, str):
        try:
            report_data = json.loads(report_data)
        except Exception:
            report_data = {}

    analysis   = report_data.get("analysis", {}) or {}
    stock_data = report_data.get("stock_data", {}) or {}

    valuation  = analysis.get("valuation", {}) or stock_data.get("valuation", {}) or {}
    returns    = analysis.get("returns", {}) or stock_data.get("returns", {}) or {}
    financials = analysis.get("financials", {}) or stock_data.get("financials", {}) or {}
    conviction = analysis.get("conviction") or analysis.get("confidence_level", "")

    pe  = valuation.get("pe_ratio")
    roe = returns.get("roe") or financials.get("roe")

    # Investment thesis
    thesis = (
        analysis.get("investment_thesis")
        or analysis.get("thesis")
        or analysis.get("summary")
        or ""
    )
    if isinstance(thesis, dict):
        thesis = thesis.get("summary") or thesis.get("text") or ""
    thesis = str(thesis).strip()
    if len(thesis) > 300:
        thesis = thesis[:297] + "..."

    # Build message
    parts = [
        f"📊 *{ticker} — {company_name}*",
        "",
        f"{rec_emoji} *Recommendation:* {recommendation}",
    ]
    if ai_target_price:
        parts.append(f"🎯 *Target Price:* {currency}{ai_target_price:,.0f}{upside}")
    if conviction:
        parts.append(f"⚡ *Conviction:* {str(conviction).title()}")
    parts.append("")

    metrics = []
    if pe:
        metrics.append(f"P/E: {pe:.1f}x" if isinstance(pe, (int, float)) else f"P/E: {pe}")
    if roe:
        metrics.append(f"ROE: {roe:.1f}%" if isinstance(roe, (int, float)) else f"ROE: {roe}")
    if metrics:
        parts += ["*Key Metrics*", " | ".join(metrics), ""]

    if thesis:
        parts += ["*Analysis*", thesis, ""]

    if report_id:
        report_url = (
            f"{FRONTEND_URL}/report.html"
            f"?id={report_id}"
            f"&utm_source=whatsapp&utm_medium=bot"
        )
    else:
        report_url = (
            f"{FRONTEND_URL}/generate.html"
            f"?symbol={ticker}&exchange={exchange}"
            f"&utm_source=whatsapp&utm_medium=bot"
        )
    parts += [
        "⚠️ _Not financial advice. DYOR._",
        f"🔗 Login to read the full report: {report_url}",
    ]

    return "\n".join(parts)


# ─── Action Handlers ──────────────────────────────────────────────────────────

async def _send_bull_bear_action(phone: str, ticker: str, exchange: str):
    """Send bull and bear case from cached report data — no API call needed."""
    cached = db.get_cached_report(ticker, exchange, language="en")
    if not cached:
        await _send_text(phone, f"No cached report found for *{ticker}*. Send the ticker first to generate one.")
        return

    report_data = cached.get("report_data") or {}
    if isinstance(report_data, str):
        try:
            report_data = json.loads(report_data)
        except Exception:
            report_data = {}

    analysis  = report_data.get("analysis", {}) or {}
    bull_case = analysis.get("bull_case", [])
    bear_case = analysis.get("bear_case", [])

    if not bull_case and not bear_case:
        await _send_text(phone, f"Bull/Bear case not available for *{ticker}*.")
        return

    lines = [f"🐂🐻 *{ticker} — Bull & Bear Case*\n"]

    if bull_case:
        lines.append("*🐂 Bull Case*")
        for point in bull_case[:3]:
            lines.append(f"• {str(point).strip()}")
        lines.append("")

    if bear_case:
        lines.append("*🐻 Bear Case*")
        for point in bear_case[:3]:
            lines.append(f"• {str(point).strip()}")
        lines.append("")

    lines.append("⚠️ _Not financial advice. DYOR._")
    await _send_text(phone, "\n".join(lines).strip())


async def _send_results_action(phone: str, ticker: str, exchange: str):
    """Send last 4 quarters of revenue + net income."""
    import yfinance as yf
    from yahoo_finance import get_ticker_symbol

    currency = "$" if is_us_exchange(exchange) else "₹"

    def _fmt(v):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "—"
        if is_us_exchange(exchange):
            if abs(v) >= 1e12:
                return f"{currency}{v/1e12:.2f}T"
            elif abs(v) >= 1e9:
                return f"{currency}{v/1e9:.2f}B"
            elif abs(v) >= 1e6:
                return f"{currency}{v/1e6:.1f}M"
        else:
            if abs(v) >= 1e12:
                return f"{currency}{v/1e12:.2f}L Cr"
            elif abs(v) >= 1e9:
                return f"{currency}{v/1e7:.0f} Cr"
            elif abs(v) >= 1e7:
                return f"{currency}{v/1e7:.0f} Cr"
        return f"{currency}{v:,.0f}"

    try:
        yf_symbol = get_ticker_symbol(ticker, exchange)
        yft = yf.Ticker(yf_symbol)

        # Try quarterly_income_stmt first (newer yfinance), fall back to quarterly_financials
        qf = getattr(yft, "quarterly_income_stmt", None)
        if qf is None or (hasattr(qf, "empty") and qf.empty):
            qf = yft.quarterly_financials

        if qf is None or (hasattr(qf, "empty") and qf.empty):
            await _send_text(phone, f"No quarterly results available for *{ticker}*.")
            return

        lines = [f"📋 *{ticker} — Quarterly Results*\n"]
        cols  = list(qf.columns[:4])

        rev_key = next((k for k in qf.index if "revenue" in str(k).lower()), None)
        inc_key = next((k for k in qf.index if "net income" in str(k).lower()), None)

        for col in cols:
            dt  = str(col.date()) if hasattr(col, "date") else str(col)[:10]
            rev = qf.loc[rev_key, col] if rev_key is not None else None
            inc = qf.loc[inc_key, col] if inc_key is not None else None
            lines.append(f"*{dt}*")
            if rev is not None:
                lines.append(f"  Revenue: {_fmt(rev)}")
            if inc is not None:
                lines.append(f"  Net Income: {_fmt(inc)}")
            lines.append("")

        if len(lines) <= 1:
            await _send_text(phone, f"No quarterly results available for *{ticker}*.")
            return

        lines.append("⚠️ _Source: Yahoo Finance. DYOR._")
        await _send_text(phone, "\n".join(lines).strip())

    except Exception as e:
        logger.warning(f"Results action failed for {ticker}: {e}")
        await _send_text(
            phone,
            f"Couldn't fetch results for *{ticker}* right now. Please try again later."
        )


def _parse_news_item(item: dict) -> tuple:
    """Extract (title, link, publisher) from old or new yfinance news format."""
    # New format (yfinance >= 0.2.60): fields nested under 'content'
    content = item.get("content") or {}
    if content:
        title     = content.get("title", "")
        canonical = content.get("canonicalUrl") or {}
        link      = canonical.get("url", "") or content.get("url", "")
        provider  = content.get("provider") or {}
        publisher = provider.get("displayName", "") or content.get("source", "")
    else:
        # Old format: fields at top level
        title     = item.get("title", "")
        link      = item.get("link", "")
        publisher = item.get("publisher", "")
    return title, link, publisher


async def _send_news_action(phone: str, ticker: str, exchange: str):
    """Send latest 4 news headlines."""
    import yfinance as yf
    from yahoo_finance import get_ticker_symbol

    try:
        yf_symbol = get_ticker_symbol(ticker, exchange)
        news = yf.Ticker(yf_symbol).news or []

        if not news:
            await _send_text(phone, f"No recent news found for *{ticker}*.")
            return

        lines = [f"📰 *{ticker} — Latest News*\n"]
        for item in news[:4]:
            title, link, publisher = _parse_news_item(item)
            if title:
                line = f"• {title}"
                if publisher:
                    line += f" _{publisher}_"
                if link:
                    line += f"\n  {link}"
                lines.append(line)
                lines.append("")

        if len(lines) <= 1:
            await _send_text(phone, f"No recent news found for *{ticker}*.")
            return

        await _send_text(phone, "\n".join(lines).strip())

    except Exception as e:
        logger.warning(f"News action failed for {ticker}: {e}")
        await _send_text(
            phone,
            f"Couldn't fetch news for *{ticker}* right now. Please try again later."
        )


# ─── Portfolio Analysis ───────────────────────────────────────────────────────

async def _handle_portfolio_image(phone: str, media_id: str):
    """Analyze a portfolio screenshot: extract holdings, enrich, and generate AI analysis."""
    import base64
    import anthropic
    import yfinance as yf
    from yahoo_finance import get_ticker_symbol

    phone_hash = _hash_phone(phone)

    # Gate: require linked account
    account = db.get_whatsapp_account(phone_hash)
    if not account or not account.get("user_id"):
        await _send_text(
            phone,
            "📊 *Portfolio Analysis* is available for linked accounts.\n\n"
            "Reply with your Permabullish email to link, or sign up free at permabullish.com"
        )
        return

    _log_event(phone, "portfolio_analysis_started")
    await _send_text(phone, "📊 Analyzing your portfolio... This takes about 20 seconds ⏳")

    # ── Download image ───────────────────────────────────────────────────────
    image_bytes = await _download_whatsapp_media(media_id)
    if not image_bytes:
        await _send_text(phone, "Couldn't download the image. Please try again.")
        _log_event(phone, "portfolio_analysis_error", metadata={"error": "download_failed"})
        return

    # Detect MIME type from magic bytes
    if image_bytes[:4] == b'\x89PNG':
        media_type = "image/png"
    elif image_bytes[:4] == b'RIFF':
        media_type = "image/webp"
    else:
        media_type = "image/jpeg"

    image_b64 = base64.standard_b64encode(image_bytes).decode()

    # ── Pass 1: Extract holdings from screenshot via Claude vision ───────────
    ai = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    try:
        extraction = ai.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract all stock holdings from this portfolio screenshot.\n"
                            "Return ONLY a valid JSON array, no other text.\n"
                            "Format: [{\"symbol\": \"RELIANCE\", \"exchange\": \"NSE\", "
                            "\"name\": \"Reliance Industries\", \"quantity\": 10, "
                            "\"current_value\": 25000, \"invested_value\": 20000, \"pnl_pct\": 12.5}]\n"
                            "Rules:\n"
                            "- exchange: NSE or BSE for Indian stocks, NYSE or NASDAQ for US\n"
                            "- current_value and invested_value as plain numbers (no currency symbols)\n"
                            "- Use null for fields not visible in the screenshot\n"
                            "- If no stocks are visible, return []"
                        ),
                    },
                ],
            }],
        )
        raw = extraction.content[0].text.strip()
        # Strip markdown fences if present
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip("`").strip()
        holdings = json.loads(raw)
    except Exception as e:
        logger.error(f"Portfolio extraction failed for {phone}: {e}", exc_info=True)
        await _send_text(
            phone,
            "I couldn't read the portfolio from that screenshot. "
            "Try a clearer image showing stock names and values, and caption it *portfolio*."
        )
        _log_event(phone, "portfolio_analysis_error", metadata={"error": "extraction_failed"})
        return

    if not holdings:
        await _send_text(
            phone,
            "No stock holdings found in the screenshot. "
            "Please send a clearer image of your portfolio holdings."
        )
        return

    # ── Pass 2: Enrich holdings with yfinance data ───────────────────────────
    def _enrich(h: dict) -> dict:
        symbol   = (h.get("symbol") or "").upper()
        exchange = (h.get("exchange") or "NSE").upper()
        is_us    = is_us_exchange(exchange)
        try:
            yf_sym = get_ticker_symbol(symbol, exchange)
            info   = yf.Ticker(yf_sym).info or {}
            news   = yf.Ticker(yf_sym).news or []

            top_news = []
            for item in news[:2]:
                title, _, publisher = _parse_news_item(item)
                if title:
                    pub = f" ({publisher})" if publisher else ""
                    top_news.append(f"{symbol}: {title}{pub}")

            return {
                **h,
                "sector":    info.get("sector") or "Unknown",
                "industry":  info.get("industry") or "",
                "cap_class": _classify_market_cap(info.get("marketCap"), is_us),
                "beta":      info.get("beta"),
                "news":      top_news,
            }
        except Exception:
            return {**h, "sector": "Unknown", "cap_class": "Unknown", "news": []}

    loop    = asyncio.get_event_loop()
    capped  = holdings[:15]  # Limit to 15 stocks to stay within time budget
    enriched = await loop.run_in_executor(_executor, lambda: [_enrich(h) for h in capped])

    # ── Pass 3: AI portfolio analysis ────────────────────────────────────────
    news_lines = []
    for h in enriched[:6]:
        news_lines.extend(h.get("news", [])[:1])

    holdings_for_prompt = json.dumps(
        [{k: v for k, v in h.items() if k != "news"} for h in enriched],
        indent=2,
    )
    news_for_prompt = "\n".join(news_lines) or "No recent news available."

    try:
        analysis = ai.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": (
                    "Analyze this stock portfolio. Use WhatsApp formatting (* for bold).\n\n"
                    f"Holdings:\n{holdings_for_prompt}\n\n"
                    f"Recent news on top holdings:\n{news_for_prompt}\n\n"
                    "Provide a concise analysis with these sections:\n"
                    "1. *Holdings Detected* — stock names + approximate values (1–2 lines)\n"
                    "2. *Sector Allocation* — top sectors with % (based on current_value if available, else equal weight)\n"
                    "3. *Market Cap Mix* — Large / Mid / Small cap breakdown\n"
                    "4. *Risk Assessment* — concentration, beta if available, key risks (3–4 lines)\n"
                    "5. *News Highlights* — 2–3 notable headlines affecting the portfolio\n"
                    "6. *Overall Opinion* — honest 2–3 sentence view\n"
                    "7. *Suggestions* — 2–3 specific, actionable improvements\n\n"
                    "Be concise. End with: ⚠️ _Not financial advice. DYOR._"
                ),
            }],
        )
        analysis_text = analysis.content[0].text.strip()
    except Exception as e:
        logger.error(f"Portfolio analysis generation failed: {e}", exc_info=True)
        await _send_text(phone, "Analysis generation failed. Please try again later.")
        return

    _log_event(phone, "portfolio_analysis_sent", metadata={"holdings_count": len(holdings)})

    # Split if over WhatsApp's 4096 char limit
    if len(analysis_text) <= 4096:
        await _send_text(phone, analysis_text)
    else:
        await _send_text(phone, analysis_text[:4090] + "…")
        await asyncio.sleep(0.8)
        await _send_text(phone, "…" + analysis_text[4090:])


# ─── Nudge Messages ───────────────────────────────────────────────────────────

async def _send_limit_blocked_nudge(phone: str, tier: Optional[str], limit: int):
    """Tell the user they've hit their monthly limit."""
    reset = _next_month_reset()
    if tier is None:
        msg = (
            f"📊 You've used all *{limit} free reports* this month. "
            f"They reset on {reset}.\n\n"
            "To get more reports:\n"
            "• Reply with your Permabullish email to link your account *(5 free/month)*\n"
            "• Or upgrade at permabullish.com for up to 100 reports/month"
        )
    elif tier == "free":
        msg = (
            f"📊 You've used all *{limit} reports* on your Free plan this month. "
            f"They reset on {reset}.\n\n"
            "Upgrade to Basic (₹999/month) for *50 reports/month* → permabullish.com"
        )
    elif tier == "basic":
        msg = (
            f"📊 You've used all *{limit} reports* on your Basic plan this month. "
            f"They reset on {reset}.\n\n"
            "Upgrade to Pro (₹1,499/month) for *100 reports/month* → permabullish.com"
        )
    else:
        msg = (
            f"📊 You've reached the *{limit} report* limit for this month. "
            f"They reset on {reset}. Contact us at mail@mayaskara.com for enterprise options."
        )
    await _send_text(phone, msg)


async def _send_limit_exhausted_nudge(phone: str, tier: Optional[str], limit: int):
    """Nudge after the user just sent their last free report."""
    reset = _next_month_reset()
    if tier is None:
        msg = (
            f"📊 You've just used your last free report this month ({limit}/{limit}). "
            f"They reset on {reset}.\n\n"
            "💡 Link your account for *5 free reports/month* — reply with your email, "
            "or upgrade at permabullish.com"
        )
    else:
        msg = (
            f"📊 You've just used your last report this month ({limit}/{limit}). "
            f"They reset on {reset}. Upgrade at permabullish.com for more."
        )
    await _send_text(phone, msg)


async def _send_unhandled_type(phone: str):
    await _send_text(
        phone,
        "I can look up any stock by name or ticker (e.g. RELIANCE, TCS, INFY, AAPL).\n\n"
        "📊 Want portfolio analysis? Send a screenshot of your portfolio "
        "with *portfolio* as the caption.\n\n"
        "For other queries, email mail@mayaskara.com"
    )


# ─── WhatsApp API Senders ─────────────────────────────────────────────────────

async def _send_text(phone: str, body: str):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(GRAPH_API_URL, headers=SEND_HEADERS, json={
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": body, "preview_url": False},
        })
        if r.status_code >= 400:
            logger.warning(f"WhatsApp send_text failed {r.status_code}: {r.text}")


async def _send_image(phone: str, url: str, caption: str = ""):
    payload: dict = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "image",
        "image": {"link": url},
    }
    if caption:
        payload["image"]["caption"] = caption
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(GRAPH_API_URL, headers=SEND_HEADERS, json=payload)
        if r.status_code >= 400:
            logger.warning(f"WhatsApp send_image failed {r.status_code}: {r.text}")


async def _send_reply_buttons(phone: str, options: list):
    """Send up to 3 reply buttons for disambiguation."""
    buttons = [
        {
            "type": "reply",
            "reply": {
                "id": f"{o['symbol']}_{o['exchange']}"[:256],
                "title": f"{o['symbol']} · {o['exchange']}"[:20],
            },
        }
        for o in options[:3]
    ]
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(GRAPH_API_URL, headers=SEND_HEADERS, json={
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": "Found a few matches. Which one?"},
                "action": {"buttons": buttons},
            },
        })


async def _send_interactive_list(phone: str, options: list, query: str):
    """Send interactive list for disambiguation with many results."""
    rows = [
        {
            "id": f"{o['symbol']}_{o['exchange']}"[:256],
            "title": o["symbol"][:24],
            "description": f"{o['name'][:55]} · {o['exchange']}",
        }
        for o in options[:10]
    ]
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(GRAPH_API_URL, headers=SEND_HEADERS, json={
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": f"Found {len(rows)} matches for *{query}*. Select one:"},
                "action": {
                    "button": "Select Stock",
                    "sections": [{"title": "Results", "rows": rows}],
                },
            },
        })


async def _send_action_buttons(phone: str, ticker: str, exchange: str):
    """Send 3 action buttons after every report."""
    t = ticker.upper()
    e = exchange.upper()
    buttons = [
        {
            "type": "reply",
            "reply": {
                "id":    f"ACT_B_{t}_{e}"[:256],
                "title": "🐂 Bull & Bear",
            },
        },
        {
            "type": "reply",
            "reply": {
                "id":    f"ACT_R_{t}_{e}"[:256],
                "title": "📋 Results",
            },
        },
        {
            "type": "reply",
            "reply": {
                "id":    f"ACT_N_{t}_{e}"[:256],
                "title": "📰 Latest News",
            },
        },
    ]
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(GRAPH_API_URL, headers=SEND_HEADERS, json={
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": "Get more details:"},
                "action": {"buttons": buttons},
            },
        })
        if r.status_code >= 400:
            logger.warning(f"WhatsApp send_action_buttons failed {r.status_code}: {r.text}")


async def _mark_read(message_id: str):
    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(GRAPH_API_URL, headers=SEND_HEADERS, json={
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        })


# ─── Image Endpoints ──────────────────────────────────────────────────────────

@router.get("/card/{ticker}.png")
async def serve_card(ticker: str, exchange: str = "NSE"):
    """Generate and serve a recommendation card PNG with live price."""
    ticker   = ticker.upper()
    exchange = exchange.upper()

    cached = db.get_cached_report(ticker, exchange, language="en")
    if not cached:
        raise HTTPException(status_code=404, detail="No cached report found")

    # Fetch live price — fall back to cached if it fails
    current_price = cached.get("current_price") or 0
    try:
        import yfinance as yf
        from yahoo_finance import get_ticker_symbol
        yf_symbol = get_ticker_symbol(ticker, exchange)
        info = yf.Ticker(yf_symbol).fast_info
        live_price = getattr(info, "last_price", None) or getattr(info, "regular_market_price", None)
        if live_price and live_price > 0:
            current_price = float(live_price)
    except Exception:
        pass  # Use cached price as fallback

    img_bytes = generate_share_card(
        company_name=cached.get("company_name", ticker),
        ticker=ticker,
        exchange=exchange,
        sector=cached.get("sector", ""),
        recommendation=cached.get("recommendation", "HOLD"),
        current_price=current_price,
        target_price=cached.get("ai_target_price", 0),
    )
    return Response(content=img_bytes, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=300"})


@router.get("/chart/{ticker}.png")
async def serve_chart(ticker: str, exchange: str = "NSE"):
    """Generate and serve a 6-month price chart PNG."""
    loop = asyncio.get_event_loop()
    try:
        img_bytes = await loop.run_in_executor(
            _executor, _generate_price_chart, ticker.upper(), exchange.upper()
        )
        return Response(content=img_bytes, media_type="image/png",
                        headers={"Cache-Control": "public, max-age=1800"})
    except Exception as e:
        logger.error(f"Chart error for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chart generation failed")


def _generate_price_chart(ticker: str, exchange: str) -> bytes:
    """Generate a 6-month price chart using yfinance + matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import yfinance as yf
    from yahoo_finance import get_ticker_symbol

    yf_symbol = get_ticker_symbol(ticker, exchange)
    hist = yf.Ticker(yf_symbol).history(period="6mo")
    if hist.empty:
        raise ValueError(f"No chart data for {ticker}")

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor("#102a43")
    ax.set_facecolor("#1e3a5f")

    price_min = hist["Close"].min()
    price_max = hist["Close"].max()
    padding   = (price_max - price_min) * 0.08
    y_bottom  = price_min - padding
    y_top     = price_max + padding
    ax.set_ylim(y_bottom, y_top)

    ax.plot(hist.index, hist["Close"], color="#e8913a", linewidth=2)
    ax.fill_between(hist.index, hist["Close"], y_bottom, alpha=0.15, color="#e8913a")

    ax.set_title(f"{ticker} — 6 Month", color="#ffffff", fontsize=13, pad=10)
    ax.tick_params(colors="#9fb3c8", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#334e68")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.yaxis.label.set_color("#9fb3c8")

    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ─── Event Logging ────────────────────────────────────────────────────────────

def _log_event(
    phone: str,
    event_type: str,
    ticker: str = None,
    query_text: str = None,
    metadata: dict = None,
    flagged: bool = False,
):
    try:
        phone_hash = _hash_phone(phone) if phone != "unknown" else "unknown"
        db.log_whatsapp_event(
            phone_hash=phone_hash,
            event_type=event_type,
            ticker=ticker,
            query_text=query_text,
            metadata=json.dumps(metadata) if metadata else None,
            flagged=flagged,
        )
    except Exception as e:
        logger.warning(f"Failed to log WhatsApp event {event_type}: {e}")
