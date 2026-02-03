#!/usr/bin/env python3
"""
FUTFW Trader Hub - Automated Trading Analysis
Runs FUTFW v1 analysis hourly for all symbols and sends to dashboard
"""

import os
import requests
import json
import sys
from openai import OpenAI
from datetime import datetime

# Configuration
SYMBOLS = ["MGC1", "MYM1", "MNQ1", "XAUTUSDT.P"]
WEBHOOK_URL = "https://urrkdejorxotrheccirl.supabase.co/functions/v1/trading-analysis"
WEBHOOK_API_KEY = "ftw_sk_live_9x8h4j2k6m3n5p7q1r4t6u8v2w9y1z3b5c7d9e1f3g5h7j9k1m3n5p7q9r1s3t5u7v9w1x3y5z7"

# Initialize Perplexity AI client (OpenAI-compatible)
client = OpenAI(
    api_key=os.environ.get('PERPLEXITY_API_KEY'),
    base_url="https://api.perplexity.ai"
)

FUTFW_PROMPT_TEMPLATE = """
FUTFW v1 - Futures Trade For Wins Analysis for {symbol}

Analyze {symbol} for trading opportunities using 1-hour and 15-minute timeframes:

**Context Analysis:**
- 1-hour trend: Identify overall market direction (bullish/bearish/neutral)
- 15-minute trend: Identify immediate momentum direction

**Entry Criteria:**
- Identify best 1-minute and 5-minute entry points with technical confluence
- List current support and resistance levels
- Calculate entry price, stop loss, and take profit levels based on current market structure

**Current Market Data:**
- Get the latest price for {symbol}
- Analyze recent price action and volume

**Output Requirements:**
Provide a valid JSON object with this exact structure:
{{
  "symbol": "{symbol}",
  "trend_1h": "bullish|bearish|neutral",
  "trend_15m": "bullish|bearish|neutral",
  "current_price": <number>,
  "entry_price": <number>,
  "stop_loss": <number>,
  "take_profit": <number>,
  "support_levels": [<number>, <number>],
  "resistance_levels": [<number>, <number>],
  "entry_signal": "<brief description of the trade setup>"
}}

IMPORTANT: Return ONLY valid JSON, no markdown formatting or extra text.
"""


def log_message(message, symbol="SYSTEM"):
    """Print timestamped log messages"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{symbol}] {message}")


def run_futfw_analysis(symbol):
    """
    Run FUTFW v1 analysis for a symbol using Perplexity AI
    Returns parsed JSON or None if failed
    """
    try:
        log_message(f"Starting analysis...", symbol)
        
        response = client.chat.completions.create(
            model="llama-3.1-sonar-large-128k-online",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional futures trading analyst with expertise in technical analysis. You MUST respond with valid JSON only, no markdown formatting."
                },
                {
                    "role": "user",
                    "content": FUTFW_PROMPT_TEMPLATE.format(symbol=symbol)
                }
            ],
            temperature=0.2,
            max_tokens=1500
        )
        
        analysis_text = response.choices[0].message.content.strip()
        log_message(f"Received response from Perplexity AI", symbol)
        
        # Extract JSON from response (handles markdown code blocks)
        if "```json" in analysis_text:
            start = analysis_text.find("```json") + 7
            end = analysis_text.find("```", start)
            analysis_text = analysis_text[start:end].strip()
        elif "```" in analysis_text:
            start = analysis_text.find("```") + 3
            end = analysis_text.find("```", start)
            analysis_text = analysis_text[start:end].strip()
        
        # Find JSON object boundaries
        start_idx = analysis_text.find('{')
        end_idx = analysis_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != 0:
            json_str = analysis_text[start_idx:end_idx]
            analysis_json = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['symbol', 'trend_1h', 'trend_15m', 'current_price', 
                             'entry_price', 'stop_loss', 'take_profit', 
                             'support_levels', 'resistance_levels']
            
            for field in required_fields:
                if field not in analysis_json:
                    log_message(f"Missing required field: {field}", symbol)
                    return None
            
            log_message(f"✓ Analysis completed successfully", symbol)
            return analysis_json
        else:
            log_message(f"✗ No valid JSON found in response", symbol)
            return None
            
    except json.JSONDecodeError as e:
        log_message(f"✗ JSON parsing error: {str(e)}", symbol)
        return None
    except Exception as e:
        log_message(f"✗ Analysis error: {str(e)}", symbol)
        return None


def send_to_webhook(analysis):
    """
    Send analysis data to FUTFW Trader Hub webhook
    Returns True if successful, False otherwise
    """
    symbol = analysis.get('symbol', 'UNKNOWN')
    
    try:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": WEBHOOK_API_KEY
        }
        
        log_message(f"Sending to dashboard...", symbol)
        
        response = requests.post(
            WEBHOOK_URL,
            headers=headers,
            json=analysis,
            timeout=30
        )
        
        if response.status_code == 200:
            log_message(f"✓ Successfully sent to dashboard", symbol)
            return True
        else:
            log_message(f"✗ Webhook error: HTTP {response.status_code}", symbol)
            return False
            
    except requests.exceptions.Timeout:
        log_message(f"✗ Webhook timeout after 30 seconds", symbol)
        return False
    except Exception as e:
        log_message(f"✗ Webhook error: {str(e)}", symbol)
        return False


def main():
    """Main execution function"""
    log_message("=" * 60)
    log_message("🚀 FUTFW HOURLY ANALYSIS STARTED")
    log_message("=" * 60)
    
    # Check for API key
    if not os.environ.get('PERPLEXITY_API_KEY'):
        log_message("✗ ERROR: PERPLEXITY_API_KEY environment variable not set")
        sys.exit(1)
    
    success_count = 0
    failure_count = 0
    
    for symbol in SYMBOLS:
        log_message(f"Processing {symbol}...")
        
        # Run analysis
        analysis = run_futfw_analysis(symbol)
        
        if analysis:
            # Send to webhook
            if send_to_webhook(analysis):
                success_count += 1
            else:
                failure_count += 1
        else:
            log_message(f"⚠️  Skipping {symbol} - analysis failed", symbol)
            failure_count += 1
        
        log_message("-" * 60)
    
    log_message("=" * 60)
    log_message(f"✅ Analysis Complete! Success: {success_count}/{len(SYMBOLS)} | Failed: {failure_count}/{len(SYMBOLS)}")
    log_message("=" * 60)
    
    # Exit with error code if all failed
    if failure_count == len(SYMBOLS):
        sys.exit(1)


if __name__ == "__main__":
    main()
