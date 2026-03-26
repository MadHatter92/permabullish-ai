"""
WhatsApp Bot for Permabullish
Handles incoming messages via Meta WhatsApp Cloud API webhook.
"""

import os
import re
import json
import hmac
import hashlib
import asyncio
import logging
from io import BytesIO
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

WHATSAPP_ACCESS_TOKEN   = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_APP_SECRET     = os.getenv("WHATSAPP_APP_SECRET", "")
WHATSAPP_VERIFY_TOKEN   = os.getenv("WHATSAPP_VERIFY_TOKEN", "pb_whatsapp_2026")

GRAPH_API_URL = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
SEND_HEADERS  = {
    "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

SESSION_TTL_MINUTES = 5

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

        else:
            asyncio.create_task(_send_unhandled_type(phone))
            _log_event(phone, "unhandled_message_type",
                       metadata={"type": msg_type}, flagged=True)

    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}", exc_info=True)
        _log_event("unknown", "api_error", metadata={"error": str(e)}, flagged=True)

    return {"status": "ok"}


# ─── Message Handlers ─────────────────────────────────────────────────────────

async def _handle_text(phone: str, text: str):
    """Route incoming text: email linking or stock search."""
    if _looks_like_email(text):
        await _handle_account_link(phone, text.strip().lower())
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
    """Handle a disambiguation selection. selection_id format: TICKER_EXCHANGE"""
    parts = selection_id.split("_", 1)
    if len(parts) != 2:
        await _send_text(phone, "Sorry, I didn't understand that. Please send the stock name again.")
        return

    ticker, exchange = parts[0], parts[1]
    db.clear_whatsapp_session(_hash_phone(phone))
    _log_event(phone, "disambiguation_selected", ticker=ticker,
               metadata={"exchange": exchange})
    await _send_report(phone, ticker, exchange)


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

    db.link_whatsapp_account(phone_hash, user["id"])
    _log_event(phone, "account_linked", metadata={"user_id": user["id"]})
    await _send_text(
        phone,
        f"✅ Linked! Your WhatsApp is now connected to your Permabullish account ({email}).\n\n"
        "Send any stock name or ticker to get an analysis."
    )


async def _send_report(phone: str, ticker: str, exchange: str):
    """Fetch (or generate) report and send 3-message response."""
    ticker   = ticker.upper()
    exchange = exchange.upper()

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

    _log_event(phone, "report_sent", ticker=ticker)

    api_base  = "https://api.permabullish.com"
    card_url  = f"{api_base}/whatsapp/card/{ticker}.png?exchange={exchange}"
    chart_url = f"{api_base}/whatsapp/chart/{ticker}.png?exchange={exchange}"

    # 3-message sequence
    rec = cached.get("recommendation", "HOLD").replace("_", " ").title()
    await _send_image(phone, card_url, f"*{ticker}* — {rec}")
    await asyncio.sleep(0.8)

    await _send_image(phone, chart_url)
    await asyncio.sleep(0.8)

    await _send_text(phone, _format_report_text(cached, ticker, exchange))

    # One-time account linking prompt for new phone numbers
    phone_hash = _hash_phone(phone)
    if not db.get_whatsapp_account(phone_hash):
        db.create_whatsapp_account(phone_hash)  # Mark prompt as sent (user_id=None)
        await asyncio.sleep(1.5)
        await _send_text(
            phone,
            "💼 Have a Permabullish account? Reply with your email to link it "
            "and access your report history on the web."
        )


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


def _format_report_text(cached: dict, ticker: str, exchange: str) -> str:
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
        parts.append(
            f"🎯 *Target Price:* {currency}{ai_target_price:,.0f}{upside}"
        )
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

    report_url = (
        f"{FRONTEND_URL}/generate.html"
        f"?symbol={ticker}&exchange={exchange}"
        f"&utm_source=whatsapp&utm_medium=bot"
    )
    parts += [
        "⚠️ _Not financial advice. DYOR._",
        f"🔗 Full report: {report_url}",
    ]

    return "\n".join(parts)


async def _send_unhandled_type(phone: str):
    await _send_text(
        phone,
        "I can only look up stocks by name or ticker. "
        "Send a stock name or NSE/BSE symbol (e.g. RELIANCE, TCS, INFY).\n\n"
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
    """Generate and serve a recommendation card PNG."""
    cached = db.get_cached_report(ticker.upper(), exchange.upper(), language="en")
    if not cached:
        raise HTTPException(status_code=404, detail="No cached report found")

    img_bytes = generate_share_card(
        company_name=cached.get("company_name", ticker),
        ticker=ticker.upper(),
        exchange=exchange.upper(),
        sector=cached.get("sector", ""),
        recommendation=cached.get("recommendation", "HOLD"),
        current_price=cached.get("current_price", 0),
        target_price=cached.get("ai_target_price", 0),
    )
    return Response(content=img_bytes, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=3600"})


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

    ax.plot(hist.index, hist["Close"], color="#e8913a", linewidth=2)
    ax.fill_between(hist.index, hist["Close"], alpha=0.15, color="#e8913a")

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
