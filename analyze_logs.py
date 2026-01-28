#!/usr/bin/env python3
"""
Analytics script for query logs.

Parses NDJSON log files to calculate:
- Filter rate (% queries caught by pre-filter)
- Estimated token savings
- Filter breakdown by category
- Recent queries for manual false positive review

Usage:
    python analyze_logs.py [log_directory]

Default log directory: ./logs
"""

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


# Token cost estimates (conservative)
TOKENS_PER_LLM_CALL = 500  # Average for full context + response
TOKENS_PER_FILTERED_CALL = 0  # Pre-filter uses no API tokens


def parse_log_file(filepath: Path) -> list[dict]:
    """Parse NDJSON log file into list of entries."""
    entries = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Skip malformed lines
                        continue
    except FileNotFoundError:
        pass
    return entries


def calculate_statistics(entries: list[dict]) -> dict:
    """Calculate analytics statistics from log entries."""
    if not entries:
        return {
            'total_queries': 0,
            'filtered_queries': 0,
            'llm_queries': 0,
            'filter_rate': 0.0,
            'tokens_saved': 0,
            'filter_categories': {},
            'sessions': 0
        }

    total = len(entries)
    filtered = sum(1 for e in entries if e.get('filtered_pre_llm', False))
    llm = total - filtered

    # Calculate token savings
    tokens_saved = filtered * TOKENS_PER_LLM_CALL

    # Category breakdown
    filter_categories = Counter(
        e.get('filter_category', 'unknown')
        for e in entries
        if e.get('filtered_pre_llm', False)
    )

    # Unique sessions
    sessions = len(set(e.get('session_id') for e in entries if e.get('session_id')))

    return {
        'total_queries': total,
        'filtered_queries': filtered,
        'llm_queries': llm,
        'filter_rate': (filtered / total * 100) if total > 0 else 0,
        'tokens_saved': tokens_saved,
        'filter_categories': dict(filter_categories),
        'sessions': sessions
    }


def get_recent_filtered_queries(entries: list[dict], limit: int = 10) -> list[dict]:
    """Get most recent filtered queries for manual review."""
    filtered = [
        {
            'timestamp': e.get('timestamp', 'unknown'),
            'query': e.get('query', ''),
            'response': e.get('response', ''),
            'category': e.get('filter_category', 'unknown')
        }
        for e in entries
        if e.get('filtered_pre_llm', False)
    ]

    # Sort by timestamp (newest first)
    filtered.sort(key=lambda x: x['timestamp'], reverse=True)

    return filtered[:limit]


def format_report(stats: dict, recent_filtered: list[dict]) -> str:
    """Format analytics report as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("QUERY ANALYTICS REPORT")
    lines.append("=" * 70)
    lines.append("")

    lines.append("SUMMARY")
    lines.append("-" * 70)
    lines.append(f"Total queries:        {stats['total_queries']}")
    lines.append(f"Filtered queries:     {stats['filtered_queries']} ({stats['filter_rate']:.1f}%)")
    lines.append(f"LLM queries:          {stats['llm_queries']} ({100 - stats['filter_rate']:.1f}%)")
    lines.append(f"Unique sessions:      {stats['sessions']}")
    lines.append(f"Tokens saved:         {stats['tokens_saved']:,}")
    lines.append("")

    if stats['filter_categories']:
        lines.append("FILTER BREAKDOWN")
        lines.append("-" * 70)
        for category, count in sorted(
            stats['filter_categories'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            pct = (count / stats['filtered_queries'] * 100) if stats['filtered_queries'] > 0 else 0
            lines.append(f"  {category:20s}  {count:4d} ({pct:5.1f}%)")
        lines.append("")

    if recent_filtered:
        lines.append("RECENT FILTERED QUERIES (for false positive review)")
        lines.append("-" * 70)
        for i, item in enumerate(recent_filtered, 1):
            lines.append(f"\n{i}. [{item['category']}] {item['timestamp']}")
            lines.append(f"   Q: {item['query']}")
            lines.append(f"   A: {item['response'][:80]}...")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def analyze_directory(log_dir: Path, days: int = None) -> None:
    """Analyze all log files in directory."""
    if not log_dir.exists():
        print(f"Error: Log directory not found: {log_dir}")
        return

    # Find all NDJSON files
    log_files = sorted(log_dir.glob('*-Queries.ndjson'))

    if not log_files:
        print(f"No log files found in {log_dir}")
        return

    # Filter by date if specified
    if days is not None:
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.strftime('%y%m%d')
        log_files = [f for f in log_files if f.stem[:6] >= cutoff_str]

    print(f"Analyzing {len(log_files)} log file(s)...")
    print()

    # Parse all entries
    all_entries = []
    for log_file in log_files:
        entries = parse_log_file(log_file)
        all_entries.extend(entries)
        print(f"  {log_file.name}: {len(entries)} entries")

    print()

    if not all_entries:
        print("No log entries found.")
        return

    # Calculate statistics
    stats = calculate_statistics(all_entries)
    recent_filtered = get_recent_filtered_queries(all_entries, limit=10)

    # Print report
    print(format_report(stats, recent_filtered))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze query logs for filtering statistics',
        epilog="""
Examples:
  %(prog)s                    # Analyze ./logs (default)
  %(prog)s /path/to/logs      # Analyze specific directory
  %(prog)s --days 7           # Analyze last 7 days only
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'log_directory',
        nargs='?',
        default='./logs',
        help='Directory containing log files (default: ./logs)'
    )
    parser.add_argument(
        '--days',
        type=int,
        help='Only analyze logs from last N days'
    )

    args = parser.parse_args()

    # Validate log directory path
    if args.log_directory in ['-', '--']:
        print("Error: Invalid log directory path. Use one of these:")
        print("  python analyze_logs.py              # Use default ./logs")
        print("  python analyze_logs.py /path/to/dir # Use specific directory")
        print("  python analyze_logs.py --days 7     # Analyze last 7 days")
        return

    log_dir = Path(args.log_directory)

    analyze_directory(log_dir, args.days)


if __name__ == '__main__':
    main()
