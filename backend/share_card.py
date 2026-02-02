"""
Share Card Generator for Permabullish
Generates social media preview images for stock reports
"""

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os


# Color palette matching the app
COLORS = {
    'bg': '#102a43',
    'white': '#ffffff',
    'orange': '#e8913a',
    'gray': '#9fb3c8',
    'divider': '#334e68',
    # Recommendation colors
    'strong_buy': '#22c55e',
    'buy': '#4ade80',
    'hold': '#f59e0b',
    'sell': '#f87171',
    'strong_sell': '#ef4444',
}


def get_recommendation_color(recommendation: str) -> str:
    """Get color based on recommendation."""
    rec = recommendation.lower().replace('_', ' ').strip()
    if 'strong buy' in rec:
        return COLORS['strong_buy']
    elif 'buy' in rec:
        return COLORS['buy']
    elif 'hold' in rec:
        return COLORS['hold']
    elif 'strong sell' in rec:
        return COLORS['strong_sell']
    elif 'sell' in rec:
        return COLORS['sell']
    return COLORS['gray']


def format_price(price: float) -> str:
    """Format price with Indian number system."""
    if price is None:
        return '-'
    if price >= 10000000:  # 1 crore+
        return f"Rs {price/10000000:.1f}Cr"
    elif price >= 100000:  # 1 lakh+
        return f"Rs {price/100000:.1f}L"
    else:
        return f"Rs {price:,.0f}"


def calculate_upside(current: float, target: float) -> tuple:
    """Calculate upside percentage and return formatted string with sign."""
    if not current or not target:
        return '-', COLORS['gray']
    upside = ((target - current) / current) * 100
    if upside >= 0:
        return f"+{upside:.0f}%", COLORS['strong_buy']
    else:
        return f"{upside:.0f}%", COLORS['sell']


def get_font(size: int, bold: bool = False):
    """Get font with fallback."""
    # Try common font paths
    font_paths = [
        'arial.ttf',
        'Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        'C:\\Windows\\Fonts\\arial.ttf',
    ]

    if bold:
        font_paths = [
            'arialbd.ttf',
            'Arial Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            'C:\\Windows\\Fonts\\arialbd.ttf',
        ] + font_paths

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue

    # Fallback to default
    return ImageFont.load_default()


def generate_share_card(
    company_name: str,
    ticker: str,
    exchange: str,
    sector: str,
    recommendation: str,
    current_price: float,
    target_price: float,
) -> bytes:
    """
    Generate a share card image for a stock report.

    Returns: PNG image as bytes
    """
    width, height = 1200, 630
    img = Image.new('RGB', (width, height), color=COLORS['bg'])
    draw = ImageDraw.Draw(img)

    # Load fonts
    font_large = get_font(72, bold=True)
    font_medium = get_font(48)
    font_small = get_font(32)
    font_rec = get_font(44, bold=True)

    # Company name (truncate if too long)
    display_name = company_name.upper()
    if len(display_name) > 28:
        display_name = display_name[:25] + '...'
    draw.text((60, 50), display_name, fill=COLORS['white'], font=font_large)

    # Sector and exchange
    sector_text = f"{sector} | {exchange}" if sector else exchange
    draw.text((60, 140), sector_text, fill=COLORS['gray'], font=font_small)

    # Recommendation badge
    rec_color = get_recommendation_color(recommendation)
    rec_text = recommendation.upper().replace('_', ' ')

    # Calculate badge width based on text
    bbox = draw.textbbox((0, 0), rec_text, font=font_rec)
    badge_width = bbox[2] - bbox[0] + 60
    draw.rounded_rectangle([60, 200, 60 + badge_width, 280], radius=15, fill=rec_color)
    draw.text((90, 212), rec_text, fill=COLORS['white'], font=font_rec)

    # Price section
    y_label = 320
    y_value = 365

    # AI Target Price
    draw.text((60, y_label), 'AI Target Price', fill=COLORS['gray'], font=font_small)
    draw.text((60, y_value), format_price(target_price), fill=COLORS['white'], font=font_large)

    # Potential Upside
    upside_text, upside_color = calculate_upside(current_price, target_price)
    draw.text((420, y_label), 'Potential Upside', fill=COLORS['gray'], font=font_small)
    draw.text((420, y_value), upside_text, fill=upside_color, font=font_large)

    # Current Price
    draw.text((720, y_label), 'Current Price', fill=COLORS['gray'], font=font_small)
    draw.text((720, y_value), format_price(current_price), fill=COLORS['white'], font=font_large)

    # Divider line
    draw.line([(60, 490), (1140, 490)], fill=COLORS['divider'], width=2)

    # Branding
    draw.text((60, 520), 'AI-Powered Stock Research', fill=COLORS['gray'], font=font_small)
    draw.text((60, 560), 'permabullish.com', fill=COLORS['orange'], font=font_medium)

    # Ticker badge on right side
    ticker_text = f"{ticker}"
    bbox = draw.textbbox((0, 0), ticker_text, font=font_medium)
    ticker_width = bbox[2] - bbox[0] + 40
    ticker_x = width - ticker_width - 60
    draw.rounded_rectangle([ticker_x, 540, width - 60, 600], radius=10, fill=COLORS['divider'])
    draw.text((ticker_x + 20, 555), ticker_text, fill=COLORS['white'], font=font_medium)

    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    buffer.seek(0)
    return buffer.getvalue()


def generate_share_html(
    report_id: int,
    company_name: str,
    ticker: str,
    recommendation: str,
    current_price: float,
    target_price: float,
    api_base: str,
    frontend_url: str,
) -> str:
    """
    Generate HTML page with OG meta tags for social sharing.
    Redirects to the actual report page after a brief delay.
    """
    upside_text, _ = calculate_upside(current_price, target_price)

    title = f"{ticker}: {recommendation.replace('_', ' ').title()} - {upside_text} Upside"
    description = f"AI Target: {format_price(target_price)} | Current: {format_price(current_price)} | {company_name}"
    image_url = f"{api_base}/reports/{report_id}/og-image"
    report_url = f"{frontend_url}/report.html?id={report_id}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Permabullish</title>

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="article">
    <meta property="og:url" content="{api_base}/reports/{report_id}/share">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{image_url}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:site_name" content="Permabullish">

    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{image_url}">

    <!-- WhatsApp specific -->
    <meta property="og:image:type" content="image/png">

    <!-- Telegram specific -->
    <meta property="telegram:channel" content="@permabullish">

    <!-- Delayed fallback redirect (gives crawlers time to read OG tags) -->
    <noscript>
        <meta http-equiv="refresh" content="2;url={report_url}">
    </noscript>

    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #102a43 0%, #1e3a5f 100%);
            color: white;
        }}
        .loading {{
            text-align: center;
        }}
        .spinner {{
            border: 3px solid #334e68;
            border-top: 3px solid #e8913a;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        a {{
            color: #e8913a;
        }}
    </style>
</head>
<body>
    <div class="loading">
        <div class="spinner"></div>
        <p>Loading report...</p>
        <p><a href="{report_url}">Click here if not redirected</a></p>
    </div>
    <script>
        // Use JS redirect so crawlers can read OG tags (they ignore JS)
        window.location.replace("{report_url}");
    </script>
</body>
</html>"""

    return html


def generate_comparison_share_card(
    ticker_a: str,
    ticker_b: str,
    verdict: str,
    verdict_stock: str,
    conviction: str,
    one_line_verdict: str,
) -> bytes:
    """
    Generate a share card image for a stock comparison.

    Returns: PNG image as bytes
    """
    width, height = 1200, 630
    img = Image.new('RGB', (width, height), color=COLORS['bg'])
    draw = ImageDraw.Draw(img)

    # Load fonts
    font_large = get_font(72, bold=True)
    font_medium = get_font(48)
    font_small = get_font(32)
    font_rec = get_font(44, bold=True)
    font_verdict = get_font(28)

    # Title: Stock A vs Stock B
    title_text = f"{ticker_a} vs {ticker_b}"
    draw.text((60, 50), title_text, fill=COLORS['white'], font=font_large)

    # Subtitle
    draw.text((60, 140), "AI-Powered Stock Comparison", fill=COLORS['gray'], font=font_small)

    # Winner badge
    winner_color = COLORS['strong_buy'] if conviction == 'HIGH' else COLORS['hold'] if conviction == 'MEDIUM' else COLORS['gray']
    winner_text = f"WINNER: {verdict_stock}" if verdict_stock and verdict != 'EITHER' else "EITHER"
    bbox = draw.textbbox((0, 0), winner_text, font=font_rec)
    badge_width = bbox[2] - bbox[0] + 60
    draw.rounded_rectangle([60, 200, 60 + badge_width, 280], radius=15, fill=winner_color)
    draw.text((90, 212), winner_text, fill=COLORS['white'], font=font_rec)

    # Conviction badge
    conviction_text = f"{conviction} CONVICTION" if conviction else "MEDIUM CONVICTION"
    bbox2 = draw.textbbox((0, 0), conviction_text, font=font_small)
    badge2_width = bbox2[2] - bbox2[0] + 40
    badge2_x = 60 + badge_width + 20
    conviction_color = COLORS['strong_buy'] if conviction == 'HIGH' else COLORS['hold'] if conviction == 'MEDIUM' else COLORS['gray']
    draw.rounded_rectangle([badge2_x, 205, badge2_x + badge2_width, 275], radius=10, fill=COLORS['divider'])
    draw.text((badge2_x + 20, 222), conviction_text, fill=conviction_color, font=font_small)

    # One-line verdict (wrap if needed)
    if one_line_verdict:
        verdict_display = one_line_verdict
        if len(verdict_display) > 80:
            verdict_display = verdict_display[:77] + '...'
        # Split into lines if too long
        words = verdict_display.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            bbox = draw.textbbox((0, 0), test_line, font=font_verdict)
            if bbox[2] - bbox[0] > 1000:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))

        y_pos = 320
        for line in lines[:3]:  # Max 3 lines
            draw.text((60, y_pos), line, fill=COLORS['white'], font=font_verdict)
            y_pos += 40

    # VS graphic in center
    vs_x, vs_y = 550, 440
    draw.ellipse([vs_x, vs_y, vs_x + 100, vs_y + 100], fill=COLORS['divider'])
    vs_bbox = draw.textbbox((0, 0), "VS", font=font_medium)
    vs_text_x = vs_x + 50 - (vs_bbox[2] - vs_bbox[0]) // 2
    vs_text_y = vs_y + 50 - (vs_bbox[3] - vs_bbox[1]) // 2 - 5
    draw.text((vs_text_x, vs_text_y), "VS", fill=COLORS['white'], font=font_medium)

    # Divider line
    draw.line([(60, 490), (1140, 490)], fill=COLORS['divider'], width=2)

    # Branding
    draw.text((60, 520), 'AI-Powered Stock Research', fill=COLORS['gray'], font=font_small)
    draw.text((60, 560), 'permabullish.com', fill=COLORS['orange'], font=font_medium)

    # Ticker badges on right side
    draw.rounded_rectangle([900, 520, 1000, 580], radius=10, fill='#3b82f6')  # Blue for A
    draw.text((920, 535), ticker_a, fill=COLORS['white'], font=font_small)

    draw.rounded_rectangle([1020, 520, 1140, 580], radius=10, fill='#8b5cf6')  # Purple for B
    draw.text((1040, 535), ticker_b, fill=COLORS['white'], font=font_small)

    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    buffer.seek(0)
    return buffer.getvalue()


def generate_comparison_share_html(
    comparison_id: int,
    ticker_a: str,
    ticker_b: str,
    verdict: str,
    verdict_stock: str,
    conviction: str,
    one_line_verdict: str,
    api_base: str,
    frontend_url: str,
) -> str:
    """
    Generate HTML page with OG meta tags for comparison social sharing.
    Redirects to the actual comparison page after a brief delay.
    """
    winner_text = verdict_stock if verdict_stock and verdict != 'EITHER' else 'Either'
    title = f"{ticker_a} vs {ticker_b}: {winner_text} Wins ({conviction})"
    description = one_line_verdict if one_line_verdict else f"AI-powered comparison between {ticker_a} and {ticker_b}"
    image_url = f"{api_base}/comparisons/{comparison_id}/og-image"
    compare_url = f"{frontend_url}/compare.html?a={ticker_a}&b={ticker_b}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Permabullish</title>

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="article">
    <meta property="og:url" content="{api_base}/comparisons/{comparison_id}/share">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{image_url}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:site_name" content="Permabullish">

    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{image_url}">

    <!-- WhatsApp specific -->
    <meta property="og:image:type" content="image/png">

    <!-- Telegram specific -->
    <meta property="telegram:channel" content="@permabullish">

    <!-- Delayed fallback redirect (gives crawlers time to read OG tags) -->
    <noscript>
        <meta http-equiv="refresh" content="2;url={compare_url}">
    </noscript>

    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #102a43 0%, #1e3a5f 100%);
            color: white;
        }}
        .loading {{
            text-align: center;
        }}
        .spinner {{
            border: 3px solid #334e68;
            border-top: 3px solid #e8913a;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        a {{
            color: #e8913a;
        }}
    </style>
</head>
<body>
    <div class="loading">
        <div class="spinner"></div>
        <p>Loading comparison...</p>
        <p><a href="{compare_url}">Click here if not redirected</a></p>
    </div>
    <script>
        // Use JS redirect so crawlers can read OG tags (they ignore JS)
        window.location.replace("{compare_url}");
    </script>
</body>
</html>"""

    return html
