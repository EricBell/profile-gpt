#!/usr/bin/env python3
"""
Analytics script for intent classification logs.

Calculates:
- Filter rate (% queries classified as OUT_OF_SCOPE)
- Token cost comparison (with vs without classification)
- Recent filtered queries for review

Usage:
    python analyze_logs.py [log_directory]
"""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

# Token cost estimates
TOKENS_CLASSIFICATION = 100  # Classification call (system prompt + user message)
TOKENS_FULL_CONVERSATION = 500  # Full conversation with history
TOKENS_WITH_CLASSIFICATION_IN_SCOPE = TOKENS_CLASSIFICATION + TOKENS_FULL_CONVERSATION  # 600
TOKENS_WITHOUT_CLASSIFICATION = TOKENS_FULL_CONVERSATION  # 500

def parse_log_file(filepath: Path) -> list[dict]:
    """Parse NDJSON log file."""
    entries = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        pass
    return entries

def calculate_statistics(entries: list[dict]) -> dict:
    """Calculate analytics from log entries."""
    if not entries:
        return {
            'total_queries': 0,
            'filtered_queries': 0,
            'llm_queries': 0,
            'filter_rate': 0.0,
            'old_cost': 0,
            'new_cost': 0,
            'cost_change': 0,
            'sessions': 0
        }

    total = len(entries)
    filtered = sum(1 for e in entries if e.get('filtered_pre_llm', False))
    llm = total - filtered

    # Token cost calculations
    old_cost = total * TOKENS_WITHOUT_CLASSIFICATION
    new_cost = (filtered * TOKENS_CLASSIFICATION) + (llm * TOKENS_WITH_CLASSIFICATION_IN_SCOPE)
    cost_change = new_cost - old_cost

    sessions = len(set(e.get('session_id') for e in entries if e.get('session_id')))

    return {
        'total_queries': total,
        'filtered_queries': filtered,
        'llm_queries': llm,
        'filter_rate': (filtered / total * 100) if total > 0 else 0,
        'old_cost': old_cost,
        'new_cost': new_cost,
        'cost_change': cost_change,
        'cost_change_pct': (cost_change / old_cost * 100) if old_cost > 0 else 0,
        'sessions': sessions
    }

def get_recent_filtered(entries: list[dict], limit: int = 10) -> list[dict]:
    """Get most recent filtered queries."""
    filtered = [
        {
            'timestamp': e.get('timestamp', 'unknown'),
            'query': e.get('query', ''),
            'response': e.get('response', '')
        }
        for e in entries
        if e.get('filtered_pre_llm', False)
    ]
    filtered.sort(key=lambda x: x['timestamp'], reverse=True)
    return filtered[:limit]

def format_report(stats: dict, recent: list[dict]) -> str:
    """Format analytics report."""
    lines = [
        "=" * 70,
        "INTENT CLASSIFICATION ANALYTICS",
        "=" * 70,
        "",
        "SUMMARY",
        "-" * 70,
        f"Total queries:        {stats['total_queries']}",
        f"Filtered (OUT):       {stats['filtered_queries']} ({stats['filter_rate']:.1f}%)",
        f"Full conversation:    {stats['llm_queries']} ({100 - stats['filter_rate']:.1f}%)",
        f"Unique sessions:      {stats['sessions']}",
        "",
        "TOKEN COST ANALYSIS",
        "-" * 70,
        f"Without classification:  {stats['old_cost']:,} tokens",
        f"With classification:     {stats['new_cost']:,} tokens",
        f"Change:                  {stats['cost_change']:+,} tokens ({stats['cost_change_pct']:+.1f}%)",
        "",
    ]

    if stats['cost_change'] < 0:
        lines.append(f"✅ Token savings: {abs(stats['cost_change']):,} tokens")
    else:
        lines.append(f"⚠️  Additional cost: {stats['cost_change']:,} tokens")

    if recent:
        lines.extend([
            "",
            "RECENT FILTERED QUERIES",
            "-" * 70
        ])
        for i, item in enumerate(recent, 1):
            lines.append(f"\n{i}. {item['timestamp']}")
            lines.append(f"   Q: {item['query']}")
            lines.append(f"   A: {item['response'][:80]}...")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description='Analyze intent classification logs')
    parser.add_argument('log_directory', nargs='?', default='./logs',
                        help='Directory containing log files (default: ./logs)')
    args = parser.parse_args()

    log_dir = Path(args.log_directory)
    if not log_dir.exists():
        print(f"Error: Log directory not found: {log_dir}")
        return

    log_files = sorted(log_dir.glob('*-Queries.ndjson'))
    if not log_files:
        print(f"No log files found in {log_dir}")
        return

    print(f"Analyzing {len(log_files)} log file(s)...\n")

    all_entries = []
    for log_file in log_files:
        entries = parse_log_file(log_file)
        all_entries.extend(entries)
        print(f"  {log_file.name}: {len(entries)} entries")

    print()

    if not all_entries:
        print("No log entries found.")
        return

    stats = calculate_statistics(all_entries)
    recent = get_recent_filtered(all_entries, limit=10)

    print(format_report(stats, recent))

if __name__ == '__main__':
    main()
