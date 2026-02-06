"""
Email Service for Permabullish
Handles transactional and re-engagement emails via Resend.
"""

import resend
from typing import Optional, List, Dict
from datetime import datetime
import pytz
import logging

from config import RESEND_API_KEY, FEATURED_REPORT_TICKERS

logger = logging.getLogger(__name__)

# Initialize Resend
resend.api_key = RESEND_API_KEY

# India timezone
IST = pytz.timezone('Asia/Kolkata')

# Email configuration
FROM_EMAIL = "Permabullish <noreply@permabullish.com>"
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


def format_report_cards(reports: List[Dict]) -> str:
    """Format report cards for email."""
    if not reports:
        return ""

    cards_html = ""
    for report in reports[:3]:
        rec = report.get('recommendation', 'HOLD').lower().replace(' ', '-')
        rec_class = f"rec-{rec}"
        cards_html += f"""
        <a href="{BASE_URL}/report.html?id={report['id']}" style="text-decoration: none; color: inherit;">
            <div class="report-card">
                <h4>{report.get('company_name', report.get('ticker', 'Unknown'))}</h4>
                <p>
                    <span class="recommendation {rec_class}">{report.get('recommendation', 'HOLD')}</span>
                    &nbsp; AI Target: ₹{report.get('ai_target_price', 0):,.0f}
                </p>
            </div>
        </a>
        """
    return cards_html


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send an email via Resend."""
    if not RESEND_API_KEY:
        print(f"[EMAIL] Skipping (no API key): {subject} -> {to_email}")
        return False

    try:
        params = {
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
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

    report_cards = format_report_cards(sample_reports)

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
            reports give you institutional-quality analysis on 3,000+ Indian stocks — the kind of insights
            that were once available only to professional fund managers.</p>

            <p><strong>What you can do now:</strong></p>
            <ul>
                <li>Generate AI research reports on any NSE-listed stock</li>
                <li>Get AI-recommended target prices backed by fundamental analysis</li>
                <li>Build a watchlist to track stocks you're interested in</li>
            </ul>

            <p><strong>Your free account includes 5 research reports</strong> to help you explore the platform.</p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html" class="button">Generate Your First Report</a>
            </p>

            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

            <h3>See what Permabullish can do:</h3>
            <p>Here are some recent AI research reports to explore:</p>

            {report_cards}

            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

            <p><strong>Why Permabullish?</strong></p>
            <p>Making investment decisions without proper research is like driving blindfolded.
            Permabullish helps you see clearly — analyzing financials, quarterly trends, news impact,
            and valuations so you can make decisions with confidence.</p>

            <p>Happy researching,<br><strong>The Permabullish Team</strong></p>
        </div>

        {FOOTER}
    </div>
    </body>
    </html>
    """

    return send_email(user_email, "Welcome to Permabullish - Your AI Research Partner", html)


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
                <a href="{BASE_URL}/dashboard.html" class="button">Go to Dashboard</a>
            </p>

            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

            <p><strong>Make the most of your subscription:</strong></p>
            <ol>
                <li><strong>Deep-dive into your holdings</strong> — Generate reports on stocks you already own to validate your thesis</li>
                <li><strong>Discover new opportunities</strong> — Research stocks you've been curious about</li>
                <li><strong>Track with watchlists</strong> — Save interesting stocks for later analysis</li>
            </ol>

            <p>Thank you for trusting Permabullish.</p>

            <p>The Permabullish Team</p>
        </div>

        {FOOTER}
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
                <li>Fresh AI analysis on any stock</li>
                <li>Updated market insights</li>
                <li>Your watchlist, right where you left it</li>
            </ul>
        """
        cta_text = "Reactivate My Account"

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
                <a href="{BASE_URL}/pricing.html" class="button">{cta_text}</a>
            </p>

            <div style="background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <h4 style="margin: 0 0 10px 0; color: #1e3a5f;">Why renew?</h4>
                <ul style="margin: 0; padding-left: 20px; color: #666;">
                    <li>AI-generated equity research in seconds</li>
                    <li>Coverage of 3000+ Indian stocks</li>
                    <li>Target prices, risk analysis, and more</li>
                    <li>Plans starting at just ₹625/month</li>
                </ul>
            </div>

            <p>Questions? Just reply to this email.</p>

            <p>The Permabullish Team</p>
        </div>

        {FOOTER}
    </div>
    </body>
    </html>
    """

    return send_email(user_email, subject, html)


# =============================================================================
# RE-ENGAGEMENT EMAILS (14 Templates + Weekly)
# Interspersed: Generic, Broker-focused, Hindi, and Gujarati
# =============================================================================

def get_reengagement_template(template_num: int, first_name: str, sample_reports: List[Dict]) -> tuple:
    """
    Get re-engagement email template by number.
    Returns (subject, html_content).

    Templates 1-14 for daily rotation, template 15 for weekly.
    """
    report_cards = format_report_cards(sample_reports)

    templates = {
        # Template 1: Generic - Reminder
        1: (
            "Your AI research reports are waiting",
            f"""
            <h2>Hi {first_name},</h2>

            <p>Your Permabullish account is ready and waiting.</p>

            <p>While you've been away, markets have moved and new opportunities have emerged.
            Our AI has been analyzing thousands of stocks — and your personalized insights are
            just a click away.</p>

            <p><strong>You still have free reports available.</strong> Why not use one to research
            a stock you've been curious about?</p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html" class="button">Generate a Report Now</a>
            </p>

            <h3>Popular reports this week:</h3>
            {report_cards}
            """
        ),

        # Template 2: Broker - Research That Closes Deals
        2: (
            "The research tool smart brokers are using",
            f"""
            <h2>Hi {first_name},</h2>

            <p>When a client asks <em>"Why should I buy this stock?"</em> — what do you show them?</p>

            <p>Most brokers rely on outdated reports, gut feeling, or whatever the terminal shows.
            But the best ones come prepared with real research.</p>

            <p><strong>Permabullish gives you AI-powered equity research in seconds:</strong></p>
            <ul>
                <li>Target prices backed by fundamental analysis</li>
                <li>Bull and bear cases for any stock</li>
                <li>Risk factors and catalysts to watch</li>
                <li>Coverage of 3,000+ NSE-listed stocks</li>
            </ul>

            <p>Generate a report before your next client call. Walk in with conviction.</p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html" class="button">Try It Free</a>
            </p>

            <h3>See AI research in action:</h3>
            {report_cards}
            """
        ),

        # Template 3: Generic - Value/Education
        3: (
            "What smart investors look for (and how AI helps)",
            f"""
            <h2>Hi {first_name},</h2>

            <p>Did you know that professional fund managers spend hours analyzing a single stock
            before making a decision?</p>

            <p>They look at:</p>
            <ul>
                <li>Quarterly earnings trends</li>
                <li>Valuation ratios vs. industry peers</li>
                <li>Management commentary and guidance</li>
                <li>Competitive positioning and moats</li>
            </ul>

            <p><strong>Permabullish does all of this in seconds.</strong></p>

            <p>Our AI analyzes fundamentals, news, and market data to give you the same insights
            that institutional investors rely on.</p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html" class="button">Try It Now - It's Free</a>
            </p>

            <h3>See AI analysis in action:</h3>
            {report_cards}
            """
        ),

        # Template 4: Broker - Time Savings
        4: (
            "2 hours of research in 30 seconds",
            f"""
            <h2>Hi {first_name},</h2>

            <p>How much time do you spend researching stocks before pitching them to clients?</p>

            <p>Digging through quarterly results, reading news, comparing valuations,
            understanding risks — it adds up. Time that could be spent actually talking to clients.</p>

            <p><strong>Permabullish does the heavy lifting:</strong></p>

            <p>Enter any stock → Get a comprehensive AI research report → Share insights with confidence</p>

            <p>No more scrambling before client meetings. No more <em>"let me get back to you on that."</em></p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html" class="button">Generate Your First Report</a>
            </p>

            <h3>Example reports:</h3>
            {report_cards}
            """
        ),

        # Template 5: Generic - Social Proof
        5: (
            "Investors are researching these stocks right now",
            f"""
            <h2>Hi {first_name},</h2>

            <p>Every day, investors use Permabullish to make smarter decisions.</p>

            <p>Here's what's trending on our platform this week:</p>

            {report_cards}

            <p>These reports show you exactly what our AI thinks — target prices, bull/bear cases,
            key risks, and catalysts to watch.</p>

            <p><strong>What stocks are you curious about?</strong></p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html" class="button">Research Any Stock Free</a>
            </p>
            """
        ),

        # Template 6: Broker - Client Value
        6: (
            "Institutional research for independent brokers",
            f"""
            <h2>Hi {first_name},</h2>

            <p>Large brokerages have teams of analysts producing research reports.
            Their clients get detailed stock analysis before making decisions.</p>

            <p><strong>Now you can offer the same.</strong></p>

            <p>Permabullish uses AI to generate equity research that rivals institutional reports:</p>
            <ul>
                <li>Quarterly earnings analysis</li>
                <li>Valuation comparisons</li>
                <li>News impact assessment</li>
                <li>AI-calculated target prices</li>
            </ul>

            <p>Your clients don't need to know you're not a large brokerage.
            They just need to see you come prepared.</p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html" class="button">See Sample Reports</a>
            </p>

            <h3>Level the playing field:</h3>
            {report_cards}
            """
        ),

        # Template 7: Hindi - Introduction
        7: (
            "अब हिंदी में AI स्टॉक रिसर्च",
            f"""
            <h2>नमस्ते,</h2>

            <p><strong>अब AI स्टॉक रिसर्च हिंदी में उपलब्ध है।</strong></p>

            <p>Permabullish अब हिंदी में comprehensive stock reports generate करता है।</p>

            <p>हमारी AI रिपोर्ट्स में शामिल है:</p>
            <ul>
                <li><strong>तिमाही नतीजों का विश्लेषण</strong> — Quarterly earnings analysis</li>
                <li><strong>वैल्यूएशन मेट्रिक्स</strong> — P/E, P/B और industry comparison</li>
                <li><strong>AI Target Price</strong> — 12 महीने का लक्ष्य मूल्य</li>
                <li><strong>रिस्क असेसमेंट</strong> — निवेश के जोखिम</li>
            </ul>

            <p>चाहे आप खुद के लिए रिसर्च कर रहे हों या clients के लिए — <strong>हिंदी में समझना आसान है।</strong></p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html?lang=hi" class="button">हिंदी में रिपोर्ट बनाएं</a>
            </p>

            <h3>देखें AI रिसर्च कैसे काम करती है:</h3>
            {report_cards}

            <p style="text-align: center; color: #1e3a5f; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                हर निवेशक को समझ में आने वाली रिसर्च मिलनी चाहिए।
            </p>
            """
        ),

        # Template 8: Gujarati - Introduction
        8: (
            "હવે ગુજરાતીમાં AI સ્ટોક રિસર્ચ",
            f"""
            <h2>નમસ્તે,</h2>

            <p><strong>હવે AI સ્ટોક રિસર્ચ ગુજરાતીમાં ઉપલબ્ધ છે.</strong></p>

            <p>Permabullish હવે ગુજરાતીમાં comprehensive stock reports generate કરે છે.</p>

            <p>અમારી AI રિપોર્ટ્સમાં શામેલ છે:</p>
            <ul>
                <li><strong>ત્રિમાસિક પરિણામોનું વિશ્લેષણ</strong> — Quarterly earnings analysis</li>
                <li><strong>વેલ્યુએશન મેટ્રિક્સ</strong> — P/E, P/B અને industry comparison</li>
                <li><strong>AI Target Price</strong> — 12 મહિનાનો લક્ષ્ય ભાવ</li>
                <li><strong>રિસ્ક એસેસમેન્ટ</strong> — રોકાણના જોખમો</li>
            </ul>

            <p>ગુજરાતના રોકાણકારો માટે — અમદાવાદ, સુરત, રાજકોટ, વડોદરા — <strong>તમારી ભાષામાં રિસર્ચ.</strong></p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html?lang=gu" class="button">ગુજરાતીમાં રિપોર્ટ બનાવો</a>
            </p>

            <h3>જુઓ AI રિસર્ચ કેવી રીતે કામ કરે છે:</h3>
            {report_cards}

            <p style="text-align: center; color: #1e3a5f; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                દરેક રોકાણકારને સમજાય એવું સંશોધન મળવું જોઈએ.
            </p>
            """
        ),

        # Template 9: Generic - Market FOMO
        9: (
            "Markets moved this week - here's what AI sees",
            f"""
            <h2>Hi {first_name},</h2>

            <p>The market doesn't wait for anyone.</p>

            <p>While you've been away, stocks have moved, earnings have been announced, and
            new opportunities have emerged. Are you keeping up?</p>

            <p><strong>Staying informed doesn't have to be hard.</strong> Generate an AI report
            on any stock and get:</p>
            <ul>
                <li>Current valuation analysis</li>
                <li>Recent quarterly performance</li>
                <li>News impact assessment</li>
                <li>AI-recommended target price</li>
            </ul>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html" class="button">Get AI Insights Now</a>
            </p>

            <h3>Recent AI analysis:</h3>
            {report_cards}
            """
        ),

        # Template 10: Broker - Competitive Edge
        10: (
            "Your competition is using AI research. Are you?",
            f"""
            <h2>Hi {first_name},</h2>

            <p>The brokers winning today aren't just good at selling — they're good at <em>informing</em>.</p>

            <p>When clients can Google any stock themselves, your value comes from insights
            they can't easily find. Analysis. Context. Conviction.</p>

            <p><strong>Permabullish gives you that edge:</strong></p>
            <ul>
                <li>AI research on any stock in seconds</li>
                <li>Professional reports you can share with clients</li>
                <li>Analysis that builds trust and closes deals</li>
            </ul>

            <p>Don't let competitors out-research you.</p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html" class="button">Get Your Edge</a>
            </p>

            <h3>See what AI research looks like:</h3>
            {report_cards}
            """
        ),

        # Template 11: Hindi - Broker Angle
        11: (
            "आपके Hindi-speaking clients के लिए",
            f"""
            <h2>नमस्ते,</h2>

            <p>आपके कितने clients हिंदी में stock analysis पढ़ना पसंद करेंगे?</p>

            <p>North India, UP, MP, Rajasthan के निवेशकों के लिए — हिंदी सिर्फ comfortable नहीं है,
            यह वो भाषा है जिसमें वे पैसों के बारे में सोचते हैं।</p>

            <p><strong>अब आप दे सकते हैं:</strong></p>
            <ul>
                <li>हिंदी में AI research reports</li>
                <li>Institutional-quality analysis</li>
                <li>Target prices और risk assessment जो वो समझ सकें</li>
            </ul>

            <p>जब clients research को सच में समझते हैं, तो वे faster decisions लेते हैं।</p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html?lang=hi" class="button">हिंदी में रिपोर्ट बनाएं</a>
            </p>

            <h3>देखें AI रिसर्च:</h3>
            {report_cards}

            <p style="text-align: center; color: #1e3a5f; margin: 20px 0;">
                अपने clients को वो research दीजिए जो वो समझ सकें।
            </p>
            """
        ),

        # Template 12: Gujarati - Broker Angle
        12: (
            "તમારા Gujarati-speaking clients માટે",
            f"""
            <h2>નમસ્તે,</h2>

            <p>ગુજરાતની trading culture ઊંડી છે. Dalal Street ના veterans થી લઈને નવા retail investors સુધી — ગુજરાતીઓ markets જાણે છે.</p>

            <p><strong>તેમને એ ભાષામાં research આપો જેમાં તેઓ વિચારે છે.</strong></p>

            <p>Permabullish હવે ગુજરાતીમાં AI stock reports generate કરે છે:</p>
            <ul>
                <li>Complete fundamental analysis</li>
                <li>AI-calculated target prices</li>
                <li>Risk factors અને catalysts</li>
                <li>Bull vs bear cases</li>
            </ul>

            <p>જ્યારે તમારા clients ગુજરાતીમાં research વાંચે છે, ત્યારે તેઓ વધુ deeply engage થાય છે અને faster decide કરે છે.</p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html?lang=gu" class="button">ગુજરાતીમાં રિપોર્ટ બનાવો</a>
            </p>

            <h3>જુઓ AI રિસર્ચ:</h3>
            {report_cards}

            <p style="text-align: center; color: #1e3a5f; margin: 20px 0;">
                તમારા clients ને એવું research આપો જે તેઓ સમજી શકે.
            </p>
            """
        ),

        # Template 13: Generic - Feature Highlight
        13: (
            "Did you know Permabullish can do this?",
            f"""
            <h2>Hi {first_name},</h2>

            <p>You might be surprised by everything Permabullish can help you with.</p>

            <p><strong>Beyond basic stock data, our AI provides:</strong></p>

            <p>📊 <strong>Quarterly Analysis</strong> — See if the company beat or missed expectations</p>
            <p>📰 <strong>News Impact</strong> — Understand how recent events affect the stock</p>
            <p>🎯 <strong>Target Prices</strong> — Get AI-calculated 12-month price targets</p>
            <p>⚖️ <strong>Bull vs Bear</strong> — See both sides of the investment case</p>
            <p>⚠️ <strong>Risk Assessment</strong> — Know what could go wrong</p>

            <p>All of this in a comprehensive report that takes seconds to generate.</p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html" class="button">Generate Your Free Report</a>
            </p>

            <h3>Example reports:</h3>
            {report_cards}
            """
        ),

        # Template 14: Broker - Revenue
        14: (
            "Better research = more client trades",
            f"""
            <h2>Hi {first_name},</h2>

            <p>Here's a simple truth: <strong>clients trade more when they feel confident.</strong></p>

            <p>And confidence comes from understanding. When you walk a client through solid research —
            showing them why a stock makes sense, what the risks are, what price to target —
            they're more likely to act.</p>

            <p><strong>Permabullish helps you build that confidence:</strong></p>
            <ul>
                <li>Generate AI research reports before client meetings</li>
                <li>Answer "why this stock?" with data, not opinion</li>
                <li>Share professional reports that build credibility</li>
            </ul>

            <p>Better conversations. More trades. Happier clients.</p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html" class="button">Start Free</a>
            </p>

            <h3>See AI research in action:</h3>
            {report_cards}
            """
        ),

        # Template 15: Weekly Digest
        15: (
            "Weekly: Your AI market insights",
            f"""
            <h2>Hi {first_name},</h2>

            <p>Here's your weekly roundup from Permabullish.</p>

            <p>Markets have been active, and our AI has been busy analyzing stocks.
            Here are some reports worth checking out:</p>

            {report_cards}

            <p><strong>Your account is still active</strong> with free reports available.
            Pick a stock you're interested in and see what AI thinks.</p>

            <p style="text-align: center;">
                <a href="{BASE_URL}/generate.html" class="button">Research a Stock</a>
            </p>

            <p>Or upgrade to Pro for unlimited AI insights:</p>
            <p style="text-align: center;">
                <a href="{BASE_URL}/pricing.html" style="color: #e8913a;">View Plans →</a>
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

        {FOOTER}
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
    subject, html = get_reengagement_template(template_num, first_name, sample_reports)
    return send_email(user_email, subject, html)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_template_for_day(days_since_signup: int, email_count: int) -> int:
    """
    Determine which template to use based on days since signup and emails sent.

    Days 1-14: Daily emails, rotate templates 1-14 (generic, broker, Hindi, Gujarati)
    Days 15+: Weekly emails, use template 15
    """
    if days_since_signup <= 14:
        # Daily phase: rotate templates 1-14
        return (email_count % 14) + 1
    else:
        # Weekly phase: use template 15
        return 15


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


def get_featured_reports_for_email() -> List[Dict]:
    """
    Get featured reports from database for use in emails.
    Returns formatted report data suitable for email templates.
    """
    # Import here to avoid circular imports
    import database as db

    reports = db.get_featured_reports(FEATURED_REPORT_TICKERS)

    # Format for email templates
    formatted = []
    for report in reports:
        formatted.append({
            "id": report.get("id"),
            "ticker": report.get("ticker"),
            "company_name": report.get("company_name", report.get("ticker", "Unknown")),
            "recommendation": report.get("recommendation", "HOLD"),
            "ai_target_price": report.get("ai_target_price", 0),
            "current_price": report.get("current_price", 0),
        })

    return formatted


def get_first_name(full_name: str) -> str:
    """Extract first name from full name."""
    if not full_name:
        return "there"
    return full_name.split()[0] if full_name else "there"
