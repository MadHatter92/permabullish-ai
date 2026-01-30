#!/usr/bin/env python3
"""
Token consumption analysis script.
Generates reports for 5 sample companies and measures token usage.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from report_generator import generate_ai_analysis
from yahoo_finance import fetch_stock_data
import json
from datetime import datetime

# 5 diverse Indian companies
TEST_COMPANIES = [
    ("TCS.NS", "Tata Consultancy Services", "IT"),
    ("RELIANCE.NS", "Reliance Industries", "Conglomerate"),
    ("HDFCBANK.NS", "HDFC Bank", "Banking"),
    ("BHARTIARTL.NS", "Bharti Airtel", "Telecom"),
    ("MARUTI.NS", "Maruti Suzuki", "Auto"),
]

def run_token_analysis():
    """Generate reports and collect token usage data."""
    results = []

    print("=" * 60)
    print("TOKEN CONSUMPTION ANALYSIS")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    for ticker, name, sector in TEST_COMPANIES:
        print(f"Generating report for {name} ({ticker})...")

        try:
            # Fetch stock data
            stock_data = fetch_stock_data(ticker)
            if not stock_data:
                print(f"  ERROR: Could not fetch data for {ticker}")
                continue

            # Generate AI analysis
            analysis = generate_ai_analysis(stock_data)

            # Extract token usage
            token_usage = analysis.get("_token_usage", {})

            result = {
                "company": name,
                "ticker": ticker,
                "sector": sector,
                "input_tokens": token_usage.get("input_tokens", 0),
                "output_tokens": token_usage.get("output_tokens", 0),
                "total_tokens": token_usage.get("total_tokens", 0),
                "recommendation": analysis.get("recommendation", "N/A"),
            }
            results.append(result)

            print(f"  Recommendation: {result['recommendation']}")
            print(f"  Input tokens:  {result['input_tokens']:,}")
            print(f"  Output tokens: {result['output_tokens']:,}")
            print(f"  Total tokens:  {result['total_tokens']:,}")
            print()

        except Exception as e:
            print(f"  ERROR: {str(e)}")
            print()

    # Summary
    if results:
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)

        total_input = sum(r["input_tokens"] for r in results)
        total_output = sum(r["output_tokens"] for r in results)
        total_all = sum(r["total_tokens"] for r in results)

        avg_input = total_input / len(results)
        avg_output = total_output / len(results)
        avg_total = total_all / len(results)

        print(f"\nReports generated: {len(results)}")
        print(f"\nAverage per report:")
        print(f"  Input tokens:  {avg_input:,.0f}")
        print(f"  Output tokens: {avg_output:,.0f}")
        print(f"  Total tokens:  {avg_total:,.0f}")

        print(f"\nTotal across all reports:")
        print(f"  Input tokens:  {total_input:,}")
        print(f"  Output tokens: {total_output:,}")
        print(f"  Total tokens:  {total_all:,}")

        # Cost estimation (Claude Sonnet pricing as of 2024)
        # Input: $3 per 1M tokens, Output: $15 per 1M tokens
        input_cost = (total_input / 1_000_000) * 3
        output_cost = (total_output / 1_000_000) * 15
        total_cost = input_cost + output_cost
        cost_per_report = total_cost / len(results)

        print(f"\nCost estimation (Claude Sonnet 4):")
        print(f"  Input cost:  ${input_cost:.4f}")
        print(f"  Output cost: ${output_cost:.4f}")
        print(f"  Total cost:  ${total_cost:.4f}")
        print(f"  Per report:  ${cost_per_report:.4f}")

        # Save results to file
        output_file = os.path.join(os.path.dirname(__file__), "token_analysis_results.json")
        with open(output_file, "w") as f:
            json.dump({
                "date": datetime.now().isoformat(),
                "reports": results,
                "summary": {
                    "count": len(results),
                    "avg_input_tokens": avg_input,
                    "avg_output_tokens": avg_output,
                    "avg_total_tokens": avg_total,
                    "total_input_tokens": total_input,
                    "total_output_tokens": total_output,
                    "total_tokens": total_all,
                    "estimated_cost_per_report_usd": cost_per_report,
                }
            }, f, indent=2)
        print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    run_token_analysis()
