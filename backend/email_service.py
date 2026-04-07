"""
Email Service for Permabullish
Handles transactional and re-engagement emails via Resend.
"""

import re
import resend
from typing import Optional, List, Dict
from datetime import datetime
import pytz
import logging

from config import RESEND_API_KEY, FEATURED_REPORT_IDS

logger = logging.getLogger(__name__)

# Initialize Resend
resend.api_key = RESEND_API_KEY

# India timezone
IST = pytz.timezone('Asia/Kolkata')

# Email configuration
FROM_EMAIL = "Maya from Permabullish <hello@permabullish.com>"
REPLY_TO_EMAIL = "mail@mayaskara.com"
BASE_URL = "https://permabullish.com"

# Disclaimer (required on all emails)
DISCLAIMER = """
<p style="font-size: 11px; color: #666; line-height: 1.5; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
<strong>Disclaimer:</strong> This is not financial advice. All information provided by Permabullish is for educational purposes only.
We do not guarantee accuracy or completeness of any information. Always do your own research and consult a qualified
financial advisor before making investment decisions. Past performance is not indicative of future results.
Investments in securities are subject to market risks.
</p>
"""


def get_footer(email: str = "") -> str:
    """
    Generate email footer with unsubscribe link.
    The unsubscribe link includes the email for identification.
    """
    import urllib.parse
    encoded_email = urllib.parse.quote(email) if email else ""
    unsubscribe_url = f"{BASE_URL}/unsubscribe.html?email={encoded_email}"

    return f"""
<p style="font-size: 12px; color: #888; margin-top: 20px;">
    <a href="mailto:{REPLY_TO_EMAIL}" style="color: #e8913a;">Contact Us</a>
    &nbsp;|&nbsp;
    <a href="{unsubscribe_url}" style="color: #888;">Unsubscribe</a>
</p>
{DISCLAIMER}
"""


# Default footer (for backward compatibility)
FOOTER = f"""
<p style="font-size: 12px; color: #888; margin-top: 20px;">
    <a href="mailto:{REPLY_TO_EMAIL}" style="color: #e8913a;">Contact Us</a>
</p>
{DISCLAIMER}
"""


def get_email_styles() -> str:
    """Common email styles."""
    return """
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; padding: 20px 0; }
        .logo { font-size: 24px; font-weight: bold; color: #1e3a5f; }
        .logo span { color: #e8913a; }
        .content { padding: 20px 0; }
        .button { display: inline-block; background: #e8913a; color: white !important; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 600; margin: 10px 0; }
        .button:hover { background: #d97316; }
        .button-wa { display: inline-block; background: #25D366; color: white !important; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 600; margin: 10px 0; }
        .button-wa:hover { background: #1ebe5a; }
        .report-card { background: #f8f9fa; border-radius: 8px; padding: 15px; margin: 10px 0; border-left: 4px solid #e8913a; }
        .report-card h4 { margin: 0 0 5px 0; color: #1e3a5f; }
        .report-card p { margin: 0; font-size: 14px; color: #666; }
        .recommendation { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
        .rec-buy, .rec-strong-buy { background: #d4edda; color: #155724; }
        .rec-hold { background: #fff3cd; color: #856404; }
        .rec-sell, .rec-strong-sell { background: #f8d7da; color: #721c24; }
    </style>
    """


def get_header() -> str:
    """Email header with logo."""
    return """
    <div class="header">
        <div class="logo">Perma<span>bullish</span></div>
        <p style="color: #666; font-size: 14px; margin: 5px 0 0 0;">AI-Powered Stock Research</p>
    </div>
    """


def format_report_cards(reports: List[Dict], email_type: str = "transactional") -> str:
    """Format report cards for email."""
    if not reports:
        return ""

    cards_html = ""
    for report in reports[:3]:
        rec = report.get('recommendation', 'HOLD').lower().replace(' ', '-')
        rec_class = f"rec-{rec}"
        cards_html += f"""
            <div class="report-card">
                <h4>{report.get('company_name', report.get('ticker', 'Unknown'))}</h4>
                <p>
                    <span class="recommendation {rec_class}">{report.get('recommendation', 'HOLD')}</span>
                    &nbsp; AI Target: ₹{report.get('ai_target_price', 0):,.0f}
                </p>
            </div>
        """
    return cards_html


def html_to_plain_text(html: str) -> str:
    """Convert HTML email content to plain text for multipart sending."""
    text = html
    # Strip <style> blocks entirely (content + tags) before processing
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Convert links to "text (url)" format
    text = re.sub(r'<a[^>]+href="([^"]*)"[^>]*>(.*?)</a>', r'\2 (\1)', text)
    # Convert line breaks and block elements to newlines
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>', '\n\n', text)
    text = re.sub(r'</li>', '\n', text)
    text = re.sub(r'<li[^>]*>', '  - ', text)
    text = re.sub(r'</h[1-6]>', '\n\n', text)
    text = re.sub(r'<hr[^>]*>', '\n---\n', text)
    # Strip all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send an email via Resend with proper headers for deliverability."""
    import urllib.parse

    if not RESEND_API_KEY:
        print(f"[EMAIL] Skipping (no API key): {subject} -> {to_email}")
        return False

    try:
        # Build unsubscribe URL for headers
        encoded_email = urllib.parse.quote(to_email)
        unsubscribe_url = f"{BASE_URL}/unsubscribe.html?email={encoded_email}"

        params = {
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
            "text": html_to_plain_text(html_content),
            "headers": {
                # List-Unsubscribe header helps with Gmail deliverability
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            }
        }

        response = resend.Emails.send(params)
        print(f"[EMAIL] Sent: {subject} -> {to_email} (ID: {response.get('id', 'unknown')})")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed: {subject} -> {to_email} - {e}")
        return False


# =============================================================================
# WELCOME EMAIL
# =============================================================================

def send_welcome_email(user_email: str, first_name: str, sample_reports: List[Dict]) -> bool:
    """Send welcome email to new user."""

    report_cards = format_report_cards(sample_reports, "welcome")
    footer = get_footer(user_email)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{get_email_styles()}</head>
    <body>
    <div class="container">
        {get_header()}

        <div class="content">
            <h2>Hi {first_name},</h2>

            <p>Welcome to Permabullish.</p>

            <p>You've just taken a step toward becoming a more informed investor. Our AI-powered research
            reports give you institutional-quality analysis on 3,000+ Indian stocks and 500+ US stocks (S&P 500) — the kind of insights
            that were once available only to professional fund managers.</p>

            <p><strong>What you can do now:</strong></p>
            <ul>
                <li>Generate AI research reports on any Indian or US stock</li>
                <li>Get AI-recommended target prices backed by fundamental analysis</li>
                <li>Build a watchlist to track stocks you're interested in</li>
            </ul>

            <p><strong>Your free account includes 5 research reports</strong> to help you explore the platform.</p>

            <p style="text-align: center;">
                <a href="{utm_url(BASE_URL + '/generate.html', 'welcome', 'first_report')}" class="button">Generate Your First Report</a>
            </p>

            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

            <h3>Also available on WhatsApp</h3>
            <p>No browser needed. Message <strong>+91 72598 91109</strong> on WhatsApp with any stock
            name or ticker and get a full AI research report in seconds — straight in your chat.</p>

            <p style="text-align: center;">
                <a href="https://wa.me/917259891109?text=Hi" class="button-wa">Try on WhatsApp</a>
            </p>

            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

            <h3>See what Permabullish can do:</h3>
            <p>Here are some recent AI research reports to explore:</p>

            {report_cards}

            <p>Happy researching,<br><strong>The Permabullish Team</strong></p>
        </div>

        {footer}
    </div>
    </body>
    </html>
    """

    return send_email(user_email, "Welcome to Permabullish - Your AI Research Partner", html)


# =============================================================================
# EMAIL VERIFICATION
# =============================================================================

def send_verification_email(user_email: str, first_name: str, verification_url: str) -> bool:
    """Send email verification link to new user."""

    footer = get_footer(user_email)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{get_email_styles()}</head>
    <body>
    <div class="container">
        {get_header()}

        <div class="content">
            <h2>Hi {first_name},</h2>

            <p>Welcome to Permabullish! Please verify your email address to get started.</p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" class="button">Verify Email Address</a>
            </p>

            <p style="font-size: 14px; color: #666;">This link expires in 24 hours.</p>

            <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 15px; margin: 20px 0;">
                <p style="margin: 0; font-size: 14px; color: #856404;">
                    <strong>Can't find the email?</strong> Check your spam or promotions folder.
                    If you use Gmail, look in the "Promotions" tab.
                </p>
            </div>

            <p style="font-size: 13px; color: #999;">
                If you didn't create an account on Permabullish, you can safely ignore this email.
            </p>

            <p style="font-size: 13px; color: #999;">
                If the button doesn't work, copy and paste this URL into your browser:<br>
                <span style="word-break: break-all;">{verification_url}</span>
            </p>
        </div>

        {footer}
    </div>
    </body>
    </html>
    """

    return send_email(user_email, "Verify your email - Permabullish", html)


# =============================================================================
# PASSWORD RESET
# =============================================================================

def send_password_reset_email(user_email: str, first_name: str, reset_url: str) -> bool:
    """Send password reset link to user."""

    footer = get_footer(user_email)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{get_email_styles()}</head>
    <body>
    <div class="container">
        {get_header()}

        <div class="content">
            <h2>Hi {first_name},</h2>

            <p>We received a request to reset your password. Click the button below to set a new password.</p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>

            <p style="font-size: 14px; color: #666;">This link expires in 1 hour for security.</p>

            <div style="background: #f8f9fa; border-radius: 8px; padding: 15px; margin: 20px 0;">
                <p style="margin: 0; font-size: 14px; color: #666;">
                    <strong>Didn't request this?</strong> If you didn't request a password reset,
                    you can safely ignore this email. Your password will not be changed.
                </p>
            </div>

            <p style="font-size: 13px; color: #999;">
                If the button doesn't work, copy and paste this URL into your browser:<br>
                <span style="word-break: break-all;">{reset_url}</span>
            </p>
        </div>

        {footer}
    </div>
    </body>
    </html>
    """

    return send_email(user_email, "Reset your password - Permabullish", html)


# =============================================================================
# PURCHASE CONFIRMATION EMAIL
# =============================================================================

def send_purchase_email(
    user_email: str,
    first_name: str,
    plan_name: str,
    reports_per_month: int,
    expiry_date: str
) -> bool:
    """Send purchase confirmation email."""

    footer = get_footer(user_email)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{get_email_styles()}</head>
    <body>
    <div class="container">
        {get_header()}

        <div class="content">
            <h2>Hi {first_name},</h2>

            <p>Thank you for subscribing to Permabullish <strong>{plan_name}</strong>.</p>

            <p>Your investment in better research is an investment in better decisions. You now have
            access to <strong>{reports_per_month} AI research reports per month</strong> — enough to
            thoroughly analyze your portfolio and discover new opportunities.</p>

            <div style="background: #f0f7ff; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <h4 style="margin: 0 0 10px 0; color: #1e3a5f;">Your subscription details:</h4>
                <p style="margin: 5px 0;"><strong>Plan:</strong> {plan_name}</p>
                <p style="margin: 5px 0;"><strong>Reports:</strong> {reports_per_month} per month</p>
                <p style="margin: 5px 0;"><strong>Valid until:</strong> {expiry_date}</p>
            </div>

            <p style="text-align: center;">
                <a href="{utm_url(BASE_URL + '/dashboard.html', 'purchase', 'go_to_dashboard')}" class="button">Go to Dashboard</a>
            </p>

            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

            <div style="background: #f0fff4; border: 1px solid #25D366; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <h4 style="margin: 0 0 8px 0; color: #1e3a5f;">Also works on WhatsApp</h4>
                <p style="margin: 0 0 12px 0; font-size: 14px; color: #444;">
                    Your {plan_name} plan includes <strong>{reports_per_month} reports/month on WhatsApp</strong> too.
                    Message <strong>+91 72598 91109</strong>, link your account email, and research stocks
                    without opening a browser.
                </p>
                <p style="margin: 0; text-align: center;">
                    <a href="https://wa.me/917259891109?text=Hi" class="button-wa">Open WhatsApp</a>
                </p>
            </div>

            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

            <p><strong>Make the most of your subscription:</strong></p>
            <ol>
                <li><strong>Deep-dive into your holdings</strong> — Generate reports on Indian or US stocks you already own to validate your thesis</li>
                <li><strong>Discover new opportunities</strong> — Research stocks across both markets</li>
                <li><strong>Track with watchlists</strong> — Save interesting stocks for later analysis</li>
            </ol>

            <p>Thank you for trusting Permabullish.</p>

            <p>The Permabullish Team</p>
        </div>

        {footer}
    </div>
    </body>
    </html>
    """

    return send_email(user_email, f"You're now a Permabullish {plan_name} member", html)


# =============================================================================
# SUBSCRIPTION EXPIRY EMAILS
# =============================================================================

def send_subscription_expiry_email(
    user_email: str,
    first_name: str,
    plan_name: str,
    days_since_expiry: int,
    reports_generated: int = 0
) -> bool:
    """
    Send subscription expiry reminder email.
    Different messaging based on how long ago it expired.
    """

    # Determine urgency and messaging based on days since expiry
    if days_since_expiry == 0:
        subject = f"Your {plan_name} subscription expires today"
        headline = "Your subscription expires today"
        message = """
            <p>Just a heads up — your Permabullish subscription expires today.</p>
            <p>To keep your uninterrupted access to AI-powered research reports, renew now.</p>
        """
        cta_text = "Renew Now"
    elif days_since_expiry <= 3:
        subject = f"Your {plan_name} subscription has expired"
        headline = "Your subscription has expired"
        message = f"""
            <p>Your Permabullish {plan_name} subscription has expired.</p>
            <p>You've generated <strong>{reports_generated} reports</strong> during your subscription.
            Don't lose momentum — renew now to continue your research.</p>
        """
        cta_text = "Renew Now"
    elif days_since_expiry <= 7:
        subject = "We miss you at Permabullish"
        headline = "Your AI research awaits"
        message = f"""
            <p>It's been a few days since your {plan_name} subscription ended.</p>
            <p>The markets keep moving, and there are always new opportunities to analyze.
            Come back and let AI do the heavy lifting on your stock research.</p>
        """
        cta_text = "Reactivate Now"
    else:
        subject = "Come back to Permabullish"
        headline = "Ready to resume your research?"
        message = f"""
            <p>Your {plan_name} subscription ended a while ago, but your account is still here waiting for you.</p>
            <p>When you're ready to dive back into AI-powered stock research, we'll be here.</p>
            <p><strong>As a returning member, you'll get:</strong></p>
            <ul>
                <li>Fresh AI analysis on any Indian or US stock</li>
                <li>Updated market insights across both markets</li>
                <li>Your watchlist, right where you left it</li>
            </ul>
        """
        cta_text = "Reactivate My Account"

    footer = get_footer(user_email)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{get_email_styles()}</head>
    <body>
    <div class="container">
        {get_header()}

        <div class="content">
            <h2>Hi {first_name},</h2>

            <h3 style="color: #1e3a5f;">{headline}</h3>

            {message}

            <p style="text-align: center; margin: 30px 0;">
                <a href="{utm_url(BASE_URL + '/pricing.html', 'expiry', 'renew')}" class="button">{cta_text}</a>
            </p>

            <div style="background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <h4 style="margin: 0 0 10px 0; color: #1e3a5f;">Why renew?</h4>
                <ul style="margin: 0; padding-left: 20px; color: #666;">
                    <li>AI-generated equity research in seconds</li>
                    <li>Coverage of 3,000+ Indian and 500+ US stocks</li>
                    <li>Target prices, risk analysis, and more</li>
                    <li>Plans starting at just ₹417/month</li>
                </ul>
            </div>

            <div style="background: #f0fff4; border: 1px solid #25D366; border-radius: 8px; padding: 15px; margin: 20px 0;">
                <p style="margin: 0; font-size: 14px; color: #444;">
                    <strong>Still have WhatsApp access:</strong> Even on a free account, you can get
                    stock research reports by messaging <strong>+91 72598 91109</strong> on WhatsApp.
                    No subscription needed.
                </p>
            </div>

            <p>Questions? Just reply to this email.</p>

            <p>The Permabullish Team</p>
        </div>

        {footer}
    </div>
    </body>
    </html>
    """

    return send_email(user_email, subject, html)


# =============================================================================
# RE-ENGAGEMENT EMAILS (9 WhatsApp-Focused Templates + Weekly)
# Mix: Generic, Broker-focused, Hindi, Gujarati, Kannada — all WhatsApp-led
# =============================================================================

def get_reengagement_template(template_num: int, first_name: str, sample_reports: List[Dict], user_email: str = "") -> tuple:
    """
    Get re-engagement email template by number.
    Returns (subject, html_content).

    Templates 1-10 for daily rotation, template 11 for weekly.
    All templates direct users to use Permabullish on WhatsApp.
    """
    report_cards = format_report_cards(sample_reports, "reengagement")
    footer = get_footer(user_email)

    # WhatsApp CTA URL (pre-filled greeting opens the conversation)
    wa_url = "https://wa.me/917259891109?text=Hi"

    # Pre-build UTM-tagged URLs for templates
    gen_url = utm_url(f"{BASE_URL}/generate.html", "reengagement", f"t{template_num}")
    gen_hi_url = utm_url(f"{BASE_URL}/generate.html?lang=hi", "reengagement", f"t{template_num}")
    gen_gu_url = utm_url(f"{BASE_URL}/generate.html?lang=gu", "reengagement", f"t{template_num}")
    gen_kn_url = utm_url(f"{BASE_URL}/generate.html?lang=kn", "reengagement", f"t{template_num}")

    templates = {
        # Template 1: Generic - WhatsApp Discovery
        1: (
            "Stock research on WhatsApp. Just type a ticker.",
            f"""
            <h2>Hi {first_name},</h2>

            <p>You might not know this, but Permabullish now works on WhatsApp.</p>

            <p>No browser. No login. Just open WhatsApp, send us a stock name or ticker,
            and get a full AI research report in seconds — recommendation, target price,
            bull and bear cases, key risks.</p>

            <p>Here's how it works:</p>
            <ol>
                <li>Open WhatsApp and message <strong>+91 72598 91109</strong></li>
                <li>Type any stock name or ticker — RELIANCE, TCS, INFY, HDFC</li>
                <li>Get your full AI research report instantly</li>
            </ol>

            <p>That's it. No steps after that.</p>

            <p style="text-align: center;">
                <a href="{wa_url}" class="button-wa">Open WhatsApp</a>
            </p>

            <h3>What other investors are researching:</h3>
            {report_cards}
            """
        ),

        # Template 2: Broker - The Client Moment
        2: (
            "Your client asks about a stock. Here's how to answer in 30 seconds.",
            f"""
            <h2>Hi {first_name},</h2>

            <p>Picture this: you're on a call with a client. They ask about HDFC Bank.
            You're not at your desk. You don't have a terminal open.</p>

            <p>Here's what you do now:</p>

            <p>Open WhatsApp. Type <strong>HDFCBANK</strong>. In 20-30 seconds, you have a full
            AI research report — recommendation, target price, quarterly results, bull and bear cases.</p>

            <p>Forward it to your client right there in WhatsApp. Done.</p>

            <p>No browser. No login. No "let me get back to you."</p>

            <p style="text-align: center;">
                <a href="{wa_url}" class="button-wa">Try It on WhatsApp</a>
            </p>

            <h3>Sample AI research:</h3>
            {report_cards}
            """
        ),

        # Template 3: Generic - Zero Friction
        3: (
            "No app download. No login. Stock research where you already are.",
            f"""
            <h2>Hi {first_name},</h2>

            <p>Most research tools make you work for it. Open a browser, log in, search,
            wait for the page to load. By then you've lost the moment.</p>

            <p>Permabullish on WhatsApp is different. You're already in WhatsApp.
            Just type a stock name and the report comes to you.</p>

            <p>It feels like texting a research analyst who knows every listed stock on NSE, BSE, NYSE, and NASDAQ.</p>

            <p style="text-align: center;">
                <a href="{wa_url}" class="button-wa">Message on WhatsApp</a>
            </p>

            <p style="text-align: center; margin-top: 8px;">
                <a href="{gen_url}" style="color: #888; font-size: 13px;">Or use the web version</a>
            </p>

            <h3>What the AI covers in each report:</h3>
            {report_cards}
            """
        ),

        # Template 4: Broker - Forward Ready
        4: (
            "Research you can send your clients — on WhatsApp",
            f"""
            <h2>Hi {first_name},</h2>

            <p>Your clients are on WhatsApp all day. When you want to share research with them,
            the smoothest path is the one that's already open.</p>

            <p>Here's the workflow that works:</p>
            <ol>
                <li>Message Permabullish on WhatsApp with any stock ticker</li>
                <li>Receive the full AI research report in your chat</li>
                <li>Forward it to your client — right from the same app</li>
            </ol>

            <p>No PDFs to attach. No "check your email." No portal login for your client.
            The research lands where they already are.</p>

            <p style="text-align: center;">
                <a href="{wa_url}" class="button-wa">Start on WhatsApp</a>
            </p>

            <h3>See what the reports look like:</h3>
            {report_cards}
            """
        ),

        # Template 5: Hindi - WhatsApp + Hindi
        5: (
            "WhatsApp पर हिंदी में स्टॉक रिसर्च",
            f"""
            <h2>नमस्ते,</h2>

            <p>अब आपको browser खोलने की जरूरत नहीं है।</p>

            <p>Permabullish अब WhatsApp पर भी उपलब्ध है — और रिपोर्ट्स <strong>हिंदी में</strong> मिलती हैं।</p>

            <p>बस इतना करें:</p>
            <ol>
                <li>WhatsApp पर <strong>+91 72598 91109</strong> को message करें</li>
                <li>कोई भी stock का नाम या ticker type करें — जैसे RELIANCE, TCS, HDFC</li>
                <li>हिंदी में पूरी AI research report पाएं — recommendation, target price, risks सब कुछ</li>
            </ol>

            <p>अपने clients को हिंदी में research forward करें। वो भाषा जिसमें वे सोचते हैं।</p>

            <p style="text-align: center;">
                <a href="{wa_url}" class="button-wa">WhatsApp पर शुरू करें</a>
            </p>

            <p style="text-align: center; margin-top: 8px;">
                <a href="{gen_hi_url}" style="color: #888; font-size: 13px;">वेबसाइट पर हिंदी में रिपोर्ट बनाएं</a>
            </p>

            <h3>देखें AI रिसर्च कैसी दिखती है:</h3>
            {report_cards}
            """
        ),

        # Template 6: Gujarati - WhatsApp + Gujarati
        6: (
            "WhatsApp પર ગુજરાતીમાં AI સ્ટૉક રિસર્ચ",
            f"""
            <h2>નમસ્તે,</h2>

            <p>હવે browser ખોલવાની જરૂર નથી।</p>

            <p>Permabullish હવે WhatsApp પર ઉપલબ્ધ છે — અને reports <strong>ગુજરાતીમાં</strong> મળે છે.</p>

            <p>બસ આ કરો:</p>
            <ol>
                <li>WhatsApp પર <strong>+91 72598 91109</strong> ને message કરો</li>
                <li>કોઈ પણ stock નું નામ અથવા ticker type કરો — RELIANCE, TCS, HDFC</li>
                <li>ગુજરાતીમાં પૂરી AI research report મળશે — recommendation, target price, risks — બધું</li>
            </ol>

            <p>તમારા clients ને ગુજરાતીમાં research forward કરો। તેઓ જે ભાષામાં વિચારે છે તેમાં.</p>

            <p style="text-align: center;">
                <a href="{wa_url}" class="button-wa">WhatsApp પર શરૂ કરો</a>
            </p>

            <p style="text-align: center; margin-top: 8px;">
                <a href="{gen_gu_url}" style="color: #888; font-size: 13px;">વેબસાઇટ પર ગુજરાતીમાં રિપોર્ટ બનાવો</a>
            </p>

            <h3>જુઓ AI રિસર્ચ કેવી દેખાય છે:</h3>
            {report_cards}
            """
        ),

        # Template 7: Kannada - WhatsApp + Kannada
        7: (
            "WhatsApp ನಲ್ಲಿ ಕನ್ನಡದಲ್ಲಿ AI ಸ್ಟಾಕ್ ರಿಸರ್ಚ್",
            f"""
            <h2>ನಮಸ್ಕಾರ,</h2>

            <p>ಈಗ browser ತೆರೆಯುವ ಅಗತ್ಯವಿಲ್ಲ.</p>

            <p>Permabullish ಈಗ WhatsApp ನಲ್ಲಿ ಲಭ್ಯವಿದೆ — ಮತ್ತು reports <strong>ಕನ್ನಡದಲ್ಲಿ</strong> ಸಿಗುತ್ತವೆ.</p>

            <p>ಇಷ್ಟು ಮಾಡಿ:</p>
            <ol>
                <li>WhatsApp ನಲ್ಲಿ <strong>+91 72598 91109</strong> ಗೆ message ಮಾಡಿ</li>
                <li>ಯಾವುದೇ stock ಹೆಸರು ಅಥವಾ ticker type ಮಾಡಿ — RELIANCE, TCS, INFY</li>
                <li>ಕನ್ನಡದಲ್ಲಿ ಪೂರ್ಣ AI research report ಪಡೆಯಿರಿ — recommendation, target price, risks — ಎಲ್ಲವೂ</li>
            </ol>

            <p>ನಿಮ್ಮ clients ಗೆ ಕನ್ನಡದಲ್ಲಿ research forward ಮಾಡಿ. ಅವರು ಯೋಚಿಸುವ ಭಾಷೆಯಲ್ಲಿ.</p>

            <p style="text-align: center;">
                <a href="{wa_url}" class="button-wa">WhatsApp ನಲ್ಲಿ ಪ್ರಾರಂಭಿಸಿ</a>
            </p>

            <p style="text-align: center; margin-top: 8px;">
                <a href="{gen_kn_url}" style="color: #888; font-size: 13px;">ವೆಬ್‌ಸೈಟ್‌ನಲ್ಲಿ ಕನ್ನಡದಲ್ಲಿ ರಿಪೋರ್ಟ್ ರಚಿಸಿ</a>
            </p>

            <h3>AI ರಿಸರ್ಚ್ ಹೇಗಿರುತ್ತದೆ ನೋಡಿ:</h3>
            {report_cards}
            """
        ),

        # Template 8: Hindi Broker - Hindi clients on WhatsApp
        8: (
            "आपके clients WhatsApp पर हैं। Research भी।",
            f"""
            <h2>नमस्ते,</h2>

            <p>आपके clients दिनभर WhatsApp पर हैं। जब आप उन्हें कोई stock pitch करते हैं,
            सबसे असरदार तरीका वही है जो वो पहले से use कर रहे हैं।</p>

            <p>अब यह possible है:</p>
            <ol>
                <li>WhatsApp पर Permabullish को कोई stock ticker भेजें</li>
                <li>हिंदी में पूरी AI research report पाएं</li>
                <li>सीधे अपने client को forward करें — same app में</li>
            </ol>

            <p>जब client हिंदी में research पढ़ते हैं — अपनी भाषा में, अपने WhatsApp पर —
            वे ज्यादा confident होते हैं और faster decide करते हैं।</p>

            <p style="text-align: center;">
                <a href="{wa_url}" class="button-wa">WhatsApp पर try करें</a>
            </p>

            <h3>देखें AI रिसर्च:</h3>
            {report_cards}
            """
        ),

        # Template 9: Broker - Preparation / Morning Routine
        9: (
            "Walk into every client meeting already prepared",
            f"""
            <h2>Hi {first_name},</h2>

            <p>Here's a routine that takes 5 minutes and changes how your client meetings go.</p>

            <p>In the morning, while commuting, open WhatsApp and message us the tickers
            your clients have been asking about. By the time you sit down, you have full
            AI research on each one — recommendation, target price, bull and bear cases.</p>

            <p>Walk in prepared. Answer questions with conviction. Your clients notice.</p>

            <p>The whole thing runs through WhatsApp. No extra apps, no browser tabs,
            no time carved out of your day.</p>

            <p style="text-align: center;">
                <a href="{wa_url}" class="button-wa">Open WhatsApp</a>
            </p>

            <h3>What your clients will see:</h3>
            {report_cards}
            """
        ),

        # Template 10: Gujarati Broker - WhatsApp + Gujarati clients
        10: (
            "તમારા clients WhatsApp પર છે. Research પણ.",
            f"""
            <h2>નમસ્તે,</h2>

            <p>ગુજરાતની trading community ઊંડી છે — Ahmedabad, Surat, Rajkot, Vadodara ના
            investors markets ને સારી રીતે સમજે છે.</p>

            <p>તમારા clients આખો દિવસ WhatsApp પર છે. હવે તમે તેમને ત્યાં જ research
            deliver કરી શકો — ગુજરાતીમાં.</p>

            <p>આ workflow try કરો:</p>
            <ol>
                <li>WhatsApp પર <strong>+91 72598 91109</strong> ને stock ticker message કરો</li>
                <li>ગુજરાતીમાં full AI research report મળશે</li>
                <li>સીધા તમારા client ને forward કરો — same app માં</li>
            </ol>

            <p>Client ગુજરાતીમાં research વાંચે — સમજે — faster decide કરે.</p>

            <p style="text-align: center;">
                <a href="{wa_url}" class="button-wa">WhatsApp પર try કરો</a>
            </p>

            <p style="text-align: center; margin-top: 8px;">
                <a href="{gen_gu_url}" style="color: #888; font-size: 13px;">વેબ પર ગુજરાતીમાં રિપોર્ટ બનાવો</a>
            </p>

            <h3>AI રિસર્ચ જુઓ:</h3>
            {report_cards}
            """
        ),

        # Template 11: Weekly - WhatsApp focused
        11: (
            "3 stocks. 3 minutes. WhatsApp.",
            f"""
            <h2>Hi {first_name},</h2>

            <p>Here's a quick challenge for this week.</p>

            <p>Pick 3 stocks you've been curious about or your clients have been asking about.
            Message them to Permabullish on WhatsApp — one at a time.
            Each report takes under 30 seconds.</p>

            <p>You'll have research on all three before your next coffee is done.</p>

            <p style="text-align: center;">
                <a href="{wa_url}" class="button-wa">Open WhatsApp</a>
            </p>

            <h3>Some recent research to get you thinking:</h3>
            {report_cards}

            <p style="margin-top: 20px;">
                <a href="{gen_url}" style="color: #888; font-size: 13px;">Prefer the website? Generate reports here.</a>
            </p>
            """
        ),
    }

    # Default to template 1 if invalid
    subject, body = templates.get(template_num, templates[1])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{get_email_styles()}</head>
    <body>
    <div class="container">
        {get_header()}

        <div class="content">
            {body}

            <p>Happy investing,<br><strong>The Permabullish Team</strong></p>
        </div>

        {footer}
    </div>
    </body>
    </html>
    """

    return subject, html


def send_reengagement_email(
    user_email: str,
    first_name: str,
    template_num: int,
    sample_reports: List[Dict]
) -> bool:
    """Send re-engagement email using specified template."""
    subject, html = get_reengagement_template(template_num, first_name, sample_reports, user_email)
    return send_email(user_email, subject, html)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_template_for_day(days_since_signup: int, email_count: int) -> int:
    """
    Determine which template to use based on days since signup and emails sent.

    Days 1-14: Daily emails, rotate templates 1-10 (WhatsApp-focused: generic, broker, Hindi, Gujarati, Kannada)
    Days 15+: Weekly emails, use template 11
    """
    # Daily templates: 1-10, all WhatsApp-focused
    daily_templates = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    if days_since_signup <= 14:
        # Daily phase: rotate through daily templates
        return daily_templates[email_count % len(daily_templates)]
    else:
        # Weekly phase: use template 11
        return 11


def should_send_reengagement(
    days_since_signup: int,
    days_since_last_email: Optional[int],
    days_since_last_activity: Optional[int],
    is_paid_user: bool
) -> bool:
    """
    Determine if user should receive re-engagement email.

    Rules:
    - Not a paid user
    - Within 6 months of signup (180 days)
    - Not active in last 7 days
    - Timing:
      - Days 1-14: Daily (if no email sent today)
      - Days 15-180: Weekly (if no email in last 7 days)
    """
    # Exclude paid users
    if is_paid_user:
        return False

    # Only within 6 months
    if days_since_signup > 180:
        return False

    # Must be inactive for 1 day
    if days_since_last_activity is not None and days_since_last_activity < 1:
        return False

    # Check email frequency
    if days_since_signup <= 14:
        # Daily phase: send if no email today
        if days_since_last_email is None or days_since_last_email >= 1:
            return True
    else:
        # Weekly phase: send if no email in 7 days
        if days_since_last_email is None or days_since_last_email >= 7:
            return True

    return False


def get_featured_reports_for_email(day_of_year: int = 1) -> List[Dict]:
    """
    Get featured reports from database for use in emails.
    Uses curated FEATURED_REPORT_IDS if enough exist, otherwise falls back
    to recent reports from report_cache. Rotates which 3 are shown daily.
    """
    # Import here to avoid circular imports
    import database as db

    # Try curated list first, fall back to recent reports
    all_reports = db.get_featured_reports_by_ids(FEATURED_REPORT_IDS)
    if len(all_reports) < 6:
        # Not enough curated reports survive — use recent reports instead
        recent = db.get_recent_reports(12)
        # Merge: curated first, then recent (deduplicated)
        seen_ids = {r["id"] for r in all_reports}
        for r in recent:
            if r["id"] not in seen_ids:
                all_reports.append(r)
                seen_ids.add(r["id"])

    # Rotate: pick 3 reports using sliding window based on day of year
    if len(all_reports) > 3:
        start = (day_of_year * 3) % len(all_reports)
        selected = [all_reports[(start + i) % len(all_reports)] for i in range(3)]
    else:
        selected = all_reports

    # Format for email templates
    formatted = []
    for report in selected:
        formatted.append({
            "id": report.get("id"),
            "ticker": report.get("ticker"),
            "company_name": report.get("company_name", report.get("ticker", "Unknown")),
            "recommendation": report.get("recommendation", "HOLD"),
            "ai_target_price": report.get("ai_target_price", 0),
            "current_price": report.get("current_price", 0),
        })

    return formatted


def utm_url(url: str, medium: str, campaign: str = "") -> str:
    """Append UTM parameters to a URL."""
    sep = "&" if "?" in url else "?"
    result = f"{url}{sep}utm_source=email&utm_medium={medium}"
    if campaign:
        result += f"&utm_campaign={campaign}"
    return result


def get_first_name(full_name: str) -> str:
    """Extract first name from full name."""
    if not full_name:
        return "there"
    return full_name.split()[0] if full_name else "there"
