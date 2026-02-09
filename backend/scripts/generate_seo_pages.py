#!/usr/bin/env python3
"""
Generate static SEO landing pages for Nifty 50 stocks.

Fetches cached report data from the public production API,
generates static HTML pages into frontend/stocks/{ticker}/index.html.

Usage:
    python scripts/generate_seo_pages.py                  # All Nifty 50
    python scripts/generate_seo_pages.py --ticker RELIANCE  # Single stock
    python scripts/generate_seo_pages.py --dry-run          # Preview without writing
"""

import argparse
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from html import escape

# Fix Windows console encoding for rupee symbol etc.
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_FILE = BACKEND_DIR / "data" / "nifty50_stocks.json"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "frontend" / "stocks"
DEFAULT_API_BASE = "https://api.permabullish.com/api"
SITE_URL = "https://www.permabullish.com"


def load_stocks():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        stocks = json.load(f)
    # Deduplicate by ticker
    seen = set()
    unique = []
    for s in stocks:
        if s["ticker"] not in seen:
            seen.add(s["ticker"])
            unique.append(s)
    return unique


def fetch_cached_report(ticker, api_base, exchange="NSE"):
    url = f"{api_base}/reports/cached/{ticker}?exchange={exchange}"
    req = Request(url, headers={"User-Agent": "PermabullishSEOGenerator/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            return None
        print(f"  HTTP {e.code} for {ticker}")
        return None
    except (URLError, Exception) as e:
        print(f"  Error fetching {ticker}: {e}")
        return None


def get_recommendation_color(rec):
    rec = (rec or "").upper()
    if rec in ("STRONG BUY", "BUY"):
        return "green"
    elif rec == "HOLD":
        return "amber"
    else:
        return "red"


def get_badge_classes(color):
    if color == "green":
        return "bg-green-500/20 text-green-400"
    elif color == "amber":
        return "bg-amber-500/20 text-amber-400"
    else:
        return "bg-red-500/20 text-red-400"


def get_probability_classes(prob):
    prob = (prob or "").upper()
    if prob == "HIGH":
        return "bg-red-500/20 text-red-400"
    elif prob == "MEDIUM":
        return "bg-amber-500/20 text-amber-400"
    else:
        return "bg-green-500/20 text-green-400"


def format_price(price):
    if price is None:
        return "N/A"
    try:
        p = float(price)
        if p >= 100:
            return f"\u20b9{p:,.0f}"
        else:
            return f"\u20b9{p:,.2f}"
    except (ValueError, TypeError):
        return "N/A"


def calculate_upside(current, target):
    try:
        current = float(current)
        target = float(target)
        if current <= 0:
            return None
        return ((target - current) / current) * 100
    except (ValueError, TypeError):
        return None


def e(text):
    """HTML-escape helper."""
    return escape(str(text)) if text else ""


def generate_nav_html():
    return """
    <nav class="py-4 px-4 sm:px-6">
        <div class="max-w-6xl mx-auto flex justify-between items-center">
            <a href="/" class="text-2xl font-display text-white no-underline">
                Perma<span class="text-[#e8913a]">bullish</span>
            </a>
            <div class="flex items-center gap-3 sm:gap-4">
                <a href="/pricing.html" class="text-sm text-[#9fb3c8] hover:text-white transition-colors">Pricing</a>
                <a href="/stocks/" class="text-sm text-[#9fb3c8] hover:text-white transition-colors">Stocks</a>
                <a href="/?utm_source=seo&utm_medium=nav" class="bg-[#e8913a] hover:bg-[#d97316] text-white px-4 py-2 rounded-lg text-sm font-medium transition-all no-underline">
                    Get Started Free
                </a>
            </div>
        </div>
    </nav>"""


def generate_footer_html():
    return """
    <footer class="py-8 text-center px-4">
        <div class="mb-4">
            <a href="/stocks/" class="text-sm text-[#9fb3c8] hover:text-white transition-colors">Browse All Stocks</a>
            <span class="text-[#334e68] mx-2">|</span>
            <a href="/pricing.html" class="text-sm text-[#9fb3c8] hover:text-white transition-colors">Pricing</a>
            <span class="text-[#334e68] mx-2">|</span>
            <a href="/" class="text-sm text-[#9fb3c8] hover:text-white transition-colors">Home</a>
        </div>
        <p class="text-xs text-[#627d98] leading-relaxed max-w-2xl mx-auto">
            <span class="font-medium">Disclaimer:</span> This is not financial advice. All information is for educational purposes only. We do not guarantee accuracy or completeness. Always do your own research and consult a qualified financial advisor before making investment decisions.
        </p>
        <p class="text-xs text-[#829ab1] mt-3">
            <a href="mailto:mail@mayaskara.com" class="hover:text-white transition-colors">Contact Us</a>
        </p>
    </footer>"""


def generate_stock_page(stock_info, report, all_stocks):
    ticker = stock_info["ticker"]
    company = stock_info["company_name"]
    sector = stock_info["sector"]
    ticker_lower = ticker.lower()
    canonical = f"{SITE_URL}/stocks/{ticker_lower}/"

    if report:
        return _generate_full_page(stock_info, report, all_stocks, canonical)
    else:
        return _generate_placeholder_page(stock_info, canonical)


def _generate_full_page(stock_info, report, all_stocks, canonical):
    ticker = stock_info["ticker"]
    company = stock_info["company_name"]
    sector = stock_info["sector"]
    ticker_lower = ticker.lower()

    # Extract data
    recommendation = report.get("recommendation", "")
    current_price = report.get("current_price")
    ai_target = report.get("ai_target_price")
    report_id = report.get("id")
    generated_at = report.get("generated_at", "")

    report_data = report.get("report_data")
    if isinstance(report_data, str):
        try:
            report_data = json.loads(report_data)
        except json.JSONDecodeError:
            report_data = {}
    if not report_data:
        report_data = {}

    analysis = report_data.get("analysis", {})

    opening_hook = analysis.get("opening_hook", "")
    investment_thesis = analysis.get("investment_thesis", "")
    bull_case = analysis.get("bull_case", [])
    bear_case = analysis.get("bear_case", [])
    key_risks = analysis.get("key_risks", [])
    catalysts = analysis.get("catalysts", [])
    conviction = analysis.get("conviction_level", "")

    upside = calculate_upside(current_price, ai_target)
    rec_color = get_recommendation_color(recommendation)
    badge_cls = get_badge_classes(rec_color)

    upside_str = f"+{upside:.0f}%" if upside and upside > 0 else (f"{upside:.0f}%" if upside else "N/A")
    upside_color = "text-green-400" if upside and upside > 0 else "text-red-400"

    # Meta description
    meta_parts = [f"AI analysis of {e(company)}"]
    if recommendation:
        meta_parts.append(f"{recommendation} recommendation")
    if ai_target:
        meta_parts.append(f"with {format_price(ai_target)} target price")
    if upside and upside > 0:
        meta_parts.append(f"(+{upside:.0f}% upside)")
    meta_desc = ": ".join(meta_parts[:2])
    if len(meta_parts) > 2:
        meta_desc += " " + " ".join(meta_parts[2:])
    meta_desc += ". Investment thesis, bull/bear case, key risks."

    # OG image
    og_image = f"https://api.permabullish.com/api/reports/{report_id}/og-image" if report_id else f"{SITE_URL}/og-home.png"

    # Generated date for schema
    date_str = generated_at[:10] if generated_at else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Related stocks (same sector, exclude self)
    related = [s for s in all_stocks if s["sector"] == sector and s["ticker"] != ticker][:6]

    # Build bull/bear HTML
    bull_html = ""
    for point in bull_case:
        bull_html += f'<li class="flex items-start gap-2"><svg class="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg><span>{e(point)}</span></li>\n'

    bear_html = ""
    for point in bear_case:
        bear_html += f'<li class="flex items-start gap-2"><svg class="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg><span>{e(point)}</span></li>\n'

    # Key risks HTML
    risks_html = ""
    for risk in key_risks:
        if isinstance(risk, dict):
            prob = risk.get("probability", "MEDIUM")
            prob_cls = get_probability_classes(prob)
            risks_html += f"""
            <div class="bg-[#1e3a5f]/40 border border-[#334e68] rounded-xl p-4">
                <div class="flex items-center justify-between mb-2">
                    <h4 class="text-white font-medium">{e(risk.get('title', ''))}</h4>
                    <span class="{prob_cls} text-xs px-2 py-0.5 rounded-full font-medium">{e(prob)}</span>
                </div>
                <p class="text-[#9fb3c8] text-sm">{e(risk.get('description', ''))}</p>
            </div>"""

    # Catalysts HTML
    catalysts_html = ""
    for cat in catalysts:
        catalysts_html += f"""
        <div class="flex items-start gap-3">
            <div class="w-2 h-2 bg-[#e8913a] rounded-full mt-2 flex-shrink-0"></div>
            <p class="text-[#9fb3c8]">{e(cat)}</p>
        </div>"""

    # Related stocks HTML
    related_html = ""
    for rel in related:
        rel_lower = rel["ticker"].lower()
        related_html += f'<a href="/stocks/{rel_lower}/" class="bg-[#1e3a5f]/40 border border-[#334e68] rounded-xl p-4 hover:border-[#e8913a]/50 transition-colors block no-underline"><div class="text-white font-medium">{e(rel["company_name"])}</div><div class="text-[#829ab1] text-sm">{e(rel["ticker"])} &middot; {e(rel["sector"])}</div></a>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-75Y271369Q"></script>
    <script src="/analytics.js"></script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{e(company)} Stock Analysis \u2014 AI Target Price & Recommendation | Permabullish</title>
    <meta name="description" content="{e(meta_desc)}">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    <link rel="canonical" href="{canonical}">

    <meta property="og:type" content="article">
    <meta property="og:url" content="{canonical}">
    <meta property="og:title" content="{e(company)} Stock Analysis \u2014 AI Target Price | Permabullish">
    <meta property="og:description" content="{e(meta_desc)}">
    <meta property="og:site_name" content="Permabullish">
    <meta property="og:image" content="{og_image}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">

    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{e(company)} \u2014 AI Stock Analysis | Permabullish">
    <meta name="twitter:description" content="{e(meta_desc)}">
    <meta name="twitter:image" content="{og_image}">

    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "{e(company)} Stock Analysis \u2014 AI Target Price & Recommendation",
        "description": "{e(meta_desc)}",
        "datePublished": "{date_str}",
        "dateModified": "{date_str}",
        "publisher": {{
            "@type": "Organization",
            "name": "Permabullish",
            "url": "{SITE_URL}"
        }},
        "about": {{
            "@type": "Corporation",
            "name": "{e(company)}",
            "tickerSymbol": "{e(ticker)}",
            "exchange": "NSE"
        }},
        "mainEntityOfPage": "{canonical}"
    }}
    </script>

    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        .gradient-bg {{ background: linear-gradient(135deg, #102a43 0%, #1e3a5f 50%, #243b53 100%); }}
        body {{ font-family: 'DM Sans', 'Inter', system-ui, sans-serif; }}
        .font-display {{ font-family: 'DM Serif Display', Georgia, serif; }}
        .gradient-text {{ background: linear-gradient(135deg, #e8913a, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
        a {{ transition: all 0.2s ease-out; }}
    </style>
</head>
<body class="gradient-bg min-h-screen">
    {generate_nav_html()}

    <!-- Breadcrumbs -->
    <div class="max-w-4xl mx-auto px-4 sm:px-6 pt-4">
        <nav class="text-sm text-[#829ab1]">
            <a href="/" class="hover:text-white transition-colors">Home</a>
            <span class="mx-2">/</span>
            <a href="/stocks/" class="hover:text-white transition-colors">Stocks</a>
            <span class="mx-2">/</span>
            <span class="text-[#9fb3c8]">{e(company)}</span>
        </nav>
    </div>

    <!-- Stock Header Card -->
    <section class="py-8 sm:py-12 px-4 sm:px-6">
        <div class="max-w-4xl mx-auto">
            <div class="bg-[#1e3a5f]/60 border border-[#334e68] rounded-2xl overflow-hidden">
                <div class="p-6 sm:p-8">
                    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                        <div>
                            <h1 class="text-2xl sm:text-3xl font-display text-white mb-1">{e(company)}</h1>
                            <p class="text-[#829ab1]">{e(ticker)} &middot; NSE &middot; {e(sector)}</p>
                        </div>
                        <div class="flex items-center gap-3">
                            <span class="{badge_cls} px-4 py-1.5 rounded-full text-sm font-semibold">{e(recommendation)}</span>
                            {"<span class='text-[#829ab1] text-sm'>Conviction: " + e(conviction) + "</span>" if conviction else ""}
                        </div>
                    </div>
                    <div class="grid grid-cols-3 gap-4 sm:gap-8">
                        <div class="text-center">
                            <div class="text-sm text-[#829ab1] mb-1">Current Price</div>
                            <div class="text-xl sm:text-2xl font-bold text-white">{format_price(current_price)}</div>
                        </div>
                        <div class="text-center">
                            <div class="text-sm text-[#829ab1] mb-1">AI Target</div>
                            <div class="text-xl sm:text-2xl font-bold text-[#e8913a]">{format_price(ai_target)}</div>
                        </div>
                        <div class="text-center">
                            <div class="text-sm text-[#829ab1] mb-1">Upside</div>
                            <div class="text-xl sm:text-2xl font-bold {upside_color}">{upside_str}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    {"<!-- Opening Hook -->" + '''
    <section class="px-4 sm:px-6 pb-8">
        <div class="max-w-4xl mx-auto">
            <p class="text-lg sm:text-xl text-[#9fb3c8] leading-relaxed">''' + e(opening_hook) + '''</p>
        </div>
    </section>''' if opening_hook else ""}

    {"<!-- Investment Thesis -->" + '''
    <section class="px-4 sm:px-6 pb-8">
        <div class="max-w-4xl mx-auto">
            <h2 class="text-2xl font-display text-white mb-4">Investment Thesis</h2>
            <p class="text-[#9fb3c8] leading-relaxed">''' + e(investment_thesis) + '''</p>
        </div>
    </section>''' if investment_thesis else ""}

    {"<!-- Bull vs Bear Case -->" + '''
    <section class="px-4 sm:px-6 pb-8">
        <div class="max-w-4xl mx-auto">
            <h2 class="text-2xl font-display text-white mb-6">Bull vs Bear Case</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="bg-green-500/5 border border-green-500/20 rounded-xl p-6">
                    <h3 class="text-green-400 font-semibold mb-4 flex items-center gap-2">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path></svg>
                        Bull Case
                    </h3>
                    <ul class="space-y-3">''' + bull_html + '''</ul>
                </div>
                <div class="bg-red-500/5 border border-red-500/20 rounded-xl p-6">
                    <h3 class="text-red-400 font-semibold mb-4 flex items-center gap-2">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"></path></svg>
                        Bear Case
                    </h3>
                    <ul class="space-y-3">''' + bear_html + '''</ul>
                </div>
            </div>
        </div>
    </section>''' if bull_case or bear_case else ""}

    {"<!-- Key Risks -->" + '''
    <section class="px-4 sm:px-6 pb-8">
        <div class="max-w-4xl mx-auto">
            <h2 class="text-2xl font-display text-white mb-6">Key Risks</h2>
            <div class="space-y-4">''' + risks_html + '''</div>
        </div>
    </section>''' if key_risks else ""}

    {"<!-- Catalysts -->" + '''
    <section class="px-4 sm:px-6 pb-8">
        <div class="max-w-4xl mx-auto">
            <h2 class="text-2xl font-display text-white mb-6">Upcoming Catalysts</h2>
            <div class="space-y-4">''' + catalysts_html + '''</div>
        </div>
    </section>''' if catalysts else ""}

    <!-- CTA -->
    <section class="py-12 px-4 sm:px-6">
        <div class="max-w-2xl mx-auto text-center">
            <div class="bg-[#1e3a5f]/60 border border-[#334e68] rounded-2xl p-8">
                <h2 class="text-2xl font-display text-white mb-3">Get the Full Report</h2>
                <p class="text-[#9fb3c8] mb-6">Detailed financials, valuation analysis, technical levels, shareholding pattern, and more.</p>
                <a href="/?utm_source=seo&utm_medium=stock_page&utm_campaign={ticker_lower}" class="inline-block bg-[#e8913a] hover:bg-[#d97316] text-white font-semibold px-8 py-3.5 rounded-xl text-lg transition-all shadow-lg shadow-orange-900/20 no-underline">
                    Get Full Report &mdash; Free
                </a>
                <p class="text-[#829ab1] text-sm mt-4">No credit card required. 5 free reports.</p>
            </div>
        </div>
    </section>

    {"<!-- Related Stocks -->" + '''
    <section class="px-4 sm:px-6 pb-12">
        <div class="max-w-4xl mx-auto">
            <h2 class="text-2xl font-display text-white mb-6">Related Stocks</h2>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">''' + related_html + '''</div>
        </div>
    </section>''' if related else ""}

    {generate_footer_html()}
</body>
</html>"""


def _generate_placeholder_page(stock_info, canonical):
    ticker = stock_info["ticker"]
    company = stock_info["company_name"]
    sector = stock_info["sector"]
    ticker_lower = ticker.lower()

    meta_desc = f"AI-powered stock analysis for {company} ({ticker}). Get recommendation, target price, investment thesis, and risk assessment."

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-75Y271369Q"></script>
    <script src="/analytics.js"></script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{e(company)} Stock Analysis \u2014 AI Research Report | Permabullish</title>
    <meta name="description" content="{e(meta_desc)}">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    <link rel="canonical" href="{canonical}">

    <meta property="og:type" content="article">
    <meta property="og:url" content="{canonical}">
    <meta property="og:title" content="{e(company)} \u2014 AI Stock Analysis | Permabullish">
    <meta property="og:description" content="{e(meta_desc)}">
    <meta property="og:site_name" content="Permabullish">
    <meta property="og:image" content="{SITE_URL}/og-home.png">

    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{e(company)} \u2014 AI Stock Analysis | Permabullish">
    <meta name="twitter:description" content="{e(meta_desc)}">

    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "{e(company)} Stock Analysis \u2014 AI Research Report",
        "description": "{e(meta_desc)}",
        "publisher": {{
            "@type": "Organization",
            "name": "Permabullish",
            "url": "{SITE_URL}"
        }},
        "about": {{
            "@type": "Corporation",
            "name": "{e(company)}",
            "tickerSymbol": "{e(ticker)}",
            "exchange": "NSE"
        }},
        "mainEntityOfPage": "{canonical}"
    }}
    </script>

    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        .gradient-bg {{ background: linear-gradient(135deg, #102a43 0%, #1e3a5f 50%, #243b53 100%); }}
        body {{ font-family: 'DM Sans', 'Inter', system-ui, sans-serif; }}
        .font-display {{ font-family: 'DM Serif Display', Georgia, serif; }}
        .gradient-text {{ background: linear-gradient(135deg, #e8913a, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
        a {{ transition: all 0.2s ease-out; }}
    </style>
</head>
<body class="gradient-bg min-h-screen">
    {generate_nav_html()}

    <div class="max-w-4xl mx-auto px-4 sm:px-6 pt-4">
        <nav class="text-sm text-[#829ab1]">
            <a href="/" class="hover:text-white transition-colors">Home</a>
            <span class="mx-2">/</span>
            <a href="/stocks/" class="hover:text-white transition-colors">Stocks</a>
            <span class="mx-2">/</span>
            <span class="text-[#9fb3c8]">{e(company)}</span>
        </nav>
    </div>

    <section class="py-16 sm:py-24 px-4 sm:px-6">
        <div class="max-w-2xl mx-auto text-center">
            <h1 class="text-3xl sm:text-4xl font-display text-white mb-2">{e(company)}</h1>
            <p class="text-[#829ab1] mb-8">{e(ticker)} &middot; NSE &middot; {e(sector)}</p>

            <div class="bg-[#1e3a5f]/60 border border-[#334e68] rounded-2xl p-8 mb-8">
                <div class="w-16 h-16 bg-[#e8913a]/10 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg class="w-8 h-8 text-[#e8913a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                    </svg>
                </div>
                <p class="text-[#9fb3c8] text-lg mb-6">AI analysis for {e(company)} is being prepared.</p>
                <a href="/?utm_source=seo&utm_medium=stock_page&utm_campaign={ticker_lower}" class="inline-block bg-[#e8913a] hover:bg-[#d97316] text-white font-semibold px-8 py-3.5 rounded-xl text-lg transition-all shadow-lg shadow-orange-900/20 no-underline">
                    Generate {e(ticker)} Report Now &mdash; Free
                </a>
                <p class="text-[#829ab1] text-sm mt-4">No credit card required. 5 free reports.</p>
            </div>
        </div>
    </section>

    {generate_footer_html()}
</body>
</html>"""


def generate_index_page(all_stocks, reports_data):
    """Generate the stocks browse index page."""
    sectors = sorted(set(s["sector"] for s in all_stocks))

    # Build stock cards
    cards_html = ""
    for stock in sorted(all_stocks, key=lambda s: s["company_name"]):
        ticker = stock["ticker"]
        ticker_lower = ticker.lower()
        company = stock["company_name"]
        sector = stock["sector"]
        report = reports_data.get(ticker)

        if report:
            rec = report.get("recommendation", "")
            price = format_price(report.get("current_price"))
            target = format_price(report.get("ai_target_price"))
            rec_color = get_recommendation_color(rec)
            badge_cls = get_badge_classes(rec_color)
            badge_html = f'<span class="{badge_cls} text-xs px-2 py-0.5 rounded-full font-medium">{e(rec)}</span>'
            price_html = f"""
                <div class="flex justify-between text-sm mt-3 pt-3 border-t border-[#334e68]">
                    <span class="text-[#829ab1]">Price: <span class="text-white">{price}</span></span>
                    <span class="text-[#829ab1]">Target: <span class="text-[#e8913a]">{target}</span></span>
                </div>"""
        else:
            badge_html = '<span class="bg-[#334e68]/50 text-[#829ab1] text-xs px-2 py-0.5 rounded-full">Pending</span>'
            price_html = ""

        cards_html += f"""
        <a href="/stocks/{ticker_lower}/" class="stock-card bg-[#1e3a5f]/60 border border-[#334e68] rounded-xl p-5 hover:border-[#e8913a]/50 transition-all block no-underline" data-sector="{e(sector)}">
            <div class="flex items-start justify-between mb-2">
                <div>
                    <div class="text-white font-semibold">{e(company)}</div>
                    <div class="text-[#829ab1] text-sm">{e(ticker)} &middot; {e(sector)}</div>
                </div>
                {badge_html}
            </div>
            {price_html}
        </a>"""

    # Sector filter tabs
    tabs_html = '<button class="sector-tab active bg-[#e8913a] text-white px-4 py-1.5 rounded-full text-sm font-medium transition-all" data-sector="all">All</button>\n'
    for sector in sectors:
        tabs_html += f'<button class="sector-tab bg-[#1e3a5f]/60 text-[#9fb3c8] border border-[#334e68] px-4 py-1.5 rounded-full text-sm font-medium hover:border-[#e8913a]/50 transition-all" data-sector="{e(sector)}">{e(sector)}</button>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-75Y271369Q"></script>
    <script src="/analytics.js"></script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Indian Stock Analysis \u2014 AI Research for Nifty 50 Stocks | Permabullish</title>
    <meta name="description" content="AI-powered stock analysis for Nifty 50 Indian stocks. Get buy/sell recommendations, target prices, investment thesis, and risk assessment for top Indian companies.">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    <link rel="canonical" href="{SITE_URL}/stocks/">

    <meta property="og:type" content="website">
    <meta property="og:url" content="{SITE_URL}/stocks/">
    <meta property="og:title" content="Indian Stock Analysis \u2014 AI Research for Nifty 50 Stocks">
    <meta property="og:description" content="AI-powered stock analysis for Nifty 50 Indian stocks. Buy/sell recommendations, target prices, and risk assessment.">
    <meta property="og:site_name" content="Permabullish">
    <meta property="og:image" content="{SITE_URL}/og-home.png">

    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Indian Stock Analysis \u2014 AI Research for Nifty 50">
    <meta name="twitter:description" content="AI-powered stock analysis for Nifty 50 Indian stocks.">

    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        .gradient-bg {{ background: linear-gradient(135deg, #102a43 0%, #1e3a5f 50%, #243b53 100%); }}
        body {{ font-family: 'DM Sans', 'Inter', system-ui, sans-serif; }}
        .font-display {{ font-family: 'DM Serif Display', Georgia, serif; }}
        .gradient-text {{ background: linear-gradient(135deg, #e8913a, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
        a {{ transition: all 0.2s ease-out; }}
        .sector-tab.active {{ background: #e8913a; color: white; border-color: #e8913a; }}
    </style>
</head>
<body class="gradient-bg min-h-screen">
    {generate_nav_html()}

    <section class="py-12 sm:py-16 px-4 sm:px-6">
        <div class="max-w-6xl mx-auto">
            <div class="text-center mb-10">
                <h1 class="text-3xl sm:text-4xl font-display text-white mb-4">
                    AI Stock Analysis for <span class="gradient-text">Nifty 50</span>
                </h1>
                <p class="text-[#9fb3c8] max-w-2xl mx-auto">Browse AI-powered research reports for India's top 50 stocks. Each report includes a recommendation, target price, investment thesis, and risk assessment.</p>
            </div>

            <!-- Sector filters -->
            <div class="flex flex-wrap gap-2 justify-center mb-8">
                {tabs_html}
            </div>

            <!-- Stock grid -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" id="stockGrid">
                {cards_html}
            </div>
        </div>
    </section>

    {generate_footer_html()}

    <script>
        document.querySelectorAll('.sector-tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                document.querySelectorAll('.sector-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const sector = tab.dataset.sector;
                document.querySelectorAll('.stock-card').forEach(card => {{
                    if (sector === 'all' || card.dataset.sector === sector) {{
                        card.style.display = '';
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});
            }});
        }});
    </script>
</body>
</html>"""


def generate_sitemap(all_stocks, reports_data):
    """Generate sitemap.xml."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    urls = []
    # Homepage
    urls.append(f"""  <url>
    <loc>{SITE_URL}/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>""")

    # Pricing
    urls.append(f"""  <url>
    <loc>{SITE_URL}/pricing.html</loc>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>""")

    # Stock index
    urls.append(f"""  <url>
    <loc>{SITE_URL}/stocks/</loc>
    <lastmod>{now}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""")

    # Individual stocks
    for stock in all_stocks:
        ticker_lower = stock["ticker"].lower()
        report = reports_data.get(stock["ticker"])
        if report and report.get("generated_at"):
            lastmod = report["generated_at"][:10]
        else:
            lastmod = now
        # XML-escape the URL (handles & in tickers like M&M)
        loc = escape(f"{SITE_URL}/stocks/{ticker_lower}/")
        urls.append(f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>
"""


def generate_robots_txt():
    return f"""User-agent: *
Allow: /
Allow: /stocks/

Disallow: /dashboard.html
Disallow: /generate.html
Disallow: /report.html
Disallow: /checkout.html
Disallow: /payment-status.html
Disallow: /subscription.html
Disallow: /verify-email.html
Disallow: /reset-password.html
Disallow: /unsubscribe.html

Sitemap: {SITE_URL}/sitemap.xml
"""


def main():
    parser = argparse.ArgumentParser(description="Generate SEO stock landing pages")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR),
                        help="Output directory for stock pages")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE,
                        help="API base URL")
    parser.add_argument("--ticker", help="Generate for a single ticker (for testing)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print summary without writing files")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    frontend_dir = output_dir.parent  # frontend/

    # Load stocks
    all_stocks = load_stocks()
    print(f"Loaded {len(all_stocks)} stocks from {DATA_FILE.name}")

    # Filter if single ticker
    if args.ticker:
        target = args.ticker.upper()
        stocks_to_process = [s for s in all_stocks if s["ticker"] == target]
        if not stocks_to_process:
            print(f"Error: Ticker {target} not found in nifty50_stocks.json")
            sys.exit(1)
    else:
        stocks_to_process = all_stocks

    # Fetch reports
    reports_data = {}
    count_reports = 0
    count_placeholders = 0
    count_errors = 0

    print(f"\nFetching reports for {len(stocks_to_process)} stocks...")
    for i, stock in enumerate(stocks_to_process):
        ticker = stock["ticker"]
        print(f"  [{i+1}/{len(stocks_to_process)}] {ticker}...", end=" ", flush=True)

        report = fetch_cached_report(ticker, args.api_base)
        if report:
            reports_data[ticker] = report
            rec = report.get("recommendation", "?")
            price = format_price(report.get("current_price"))
            print(f"{rec} @ {price}")
            count_reports += 1
        elif report is None:
            print("no cached report (placeholder)")
            count_placeholders += 1
        else:
            count_errors += 1

        # Rate limit
        if i < len(stocks_to_process) - 1:
            time.sleep(0.5)

    print(f"\n--- Summary ---")
    print(f"  Reports:      {count_reports}")
    print(f"  Placeholders: {count_placeholders}")
    print(f"  Errors:       {count_errors}")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return

    # Generate individual stock pages
    print(f"\nWriting stock pages to {output_dir}/...")
    for stock in stocks_to_process:
        ticker = stock["ticker"]
        ticker_lower = ticker.lower()
        page_dir = output_dir / ticker_lower
        page_dir.mkdir(parents=True, exist_ok=True)

        html = generate_stock_page(stock, reports_data.get(ticker), all_stocks)
        page_file = page_dir / "index.html"
        page_file.write_text(html, encoding="utf-8")
        print(f"  {page_file.relative_to(PROJECT_DIR)}")

    # Generate index page
    index_html = generate_index_page(all_stocks, reports_data)
    output_dir.mkdir(parents=True, exist_ok=True)
    index_file = output_dir / "index.html"
    index_file.write_text(index_html, encoding="utf-8")
    print(f"  {index_file.relative_to(PROJECT_DIR)}")

    # Generate sitemap
    sitemap_content = generate_sitemap(all_stocks, reports_data)
    sitemap_file = frontend_dir / "sitemap.xml"
    sitemap_file.write_text(sitemap_content, encoding="utf-8")
    print(f"  {sitemap_file.relative_to(PROJECT_DIR)}")

    # Generate robots.txt
    robots_content = generate_robots_txt()
    robots_file = frontend_dir / "robots.txt"
    robots_file.write_text(robots_content, encoding="utf-8")
    print(f"  {robots_file.relative_to(PROJECT_DIR)}")

    print(f"\nDone! Generated {len(stocks_to_process)} stock pages + index + sitemap + robots.txt")


if __name__ == "__main__":
    main()
