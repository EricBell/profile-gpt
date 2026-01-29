import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


def convert_date_shortcut(date_str: str) -> str:
    """Convert 'today' or 'yesterday' to YYMMDD format.

    Args:
        date_str: Either 'today', 'yesterday', or YYMMDD format

    Returns:
        YYMMDD formatted date string
    """
    if date_str.lower() == 'today':
        return datetime.now().strftime('%y%m%d')
    elif date_str.lower() == 'yesterday':
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday.strftime('%y%m%d')
    else:
        return date_str


def validate_date_format(date_str: str) -> bool:
    """Validate YYMMDD date format.

    Args:
        date_str: Date string to validate

    Returns:
        True if valid YYMMDD format, False otherwise
    """
    if not date_str:
        return True  # Empty is valid (means no filter)

    # Check if it's a shortcut
    if date_str.lower() in ['today', 'yesterday']:
        return True

    # Check YYMMDD format (6 digits)
    if not re.match(r'^\d{6}$', date_str):
        return False

    # Try to parse as date
    try:
        datetime.strptime(date_str, '%y%m%d')
        return True
    except ValueError:
        return False


def list_log_files(log_path: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> List[Tuple[str, str]]:
    """List log files in date range.

    Args:
        log_path: Directory containing log files
        start_date: Start date in YYMMDD format (inclusive), None for no start limit
        end_date: End date in YYMMDD format (inclusive), None for no end limit

    Returns:
        List of tuples: (filename, filepath) sorted by date descending (newest first)
    """
    if not os.path.exists(log_path):
        return []

    # Convert date shortcuts
    if start_date:
        start_date = convert_date_shortcut(start_date)
    if end_date:
        end_date = convert_date_shortcut(end_date)

    files = []
    pattern = re.compile(r'^(\d{6})-Queries\.ndjson$')

    try:
        for filename in os.listdir(log_path):
            match = pattern.match(filename)
            if match:
                file_date = match.group(1)

                # Check date range
                if start_date and file_date < start_date:
                    continue
                if end_date and file_date > end_date:
                    continue

                filepath = os.path.join(log_path, filename)
                # Verify it's actually a file and within the log_path (security check)
                if os.path.isfile(filepath) and os.path.abspath(filepath).startswith(os.path.abspath(log_path)):
                    files.append((filename, filepath))
    except Exception:
        return []

    # Sort by date descending (newest first)
    files.sort(key=lambda x: x[0], reverse=True)
    return files


def filter_by_session(entries: List[Dict], session_id: str) -> List[Dict]:
    """Filter entries by session ID.

    Args:
        entries: List of log entries
        session_id: Session ID to filter by

    Returns:
        Filtered list of entries
    """
    if not session_id:
        return entries

    return [entry for entry in entries if entry.get('session_id') == session_id]


def filter_by_status(entries: List[Dict], filtered: str) -> List[Dict]:
    """Filter entries by filtered_pre_llm status.

    Args:
        entries: List of log entries
        filtered: 'true' for filtered only, 'false' for full LLM only, 'all' for no filter

    Returns:
        Filtered list of entries
    """
    if filtered == 'all':
        return entries

    filter_value = filtered.lower() == 'true'
    return [entry for entry in entries if entry.get('filtered_pre_llm', False) == filter_value]


def parse_log_entries(log_path: str, start_date: Optional[str] = None,
                      end_date: Optional[str] = None, session_id: Optional[str] = None,
                      filtered: str = 'all', limit: int = 100, offset: int = 0) -> Dict:
    """Parse NDJSON log files and apply filters.

    Args:
        log_path: Directory containing log files
        start_date: Start date in YYMMDD format or 'today'/'yesterday'
        end_date: End date in YYMMDD format or 'today'/'yesterday'
        session_id: Filter by session ID (optional)
        filtered: 'true', 'false', or 'all' (default)
        limit: Maximum entries to return (default 100, max 1000)
        offset: Pagination offset (default 0)

    Returns:
        Dictionary with 'entries', 'total', 'limit', 'offset', 'has_more'
    """
    # Validate and cap limit
    limit = min(max(1, limit), 1000)
    offset = max(0, offset)

    # Get log files in date range
    log_files = list_log_files(log_path, start_date, end_date)

    all_entries = []

    # Parse each file
    for filename, filepath in log_files:
        try:
            with open(filepath, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)
                        # Add filename for reference
                        entry['filename'] = filename
                        all_entries.append(entry)
                    except json.JSONDecodeError:
                        # Skip malformed entries
                        continue
        except Exception:
            # Skip files that can't be read
            continue

    # Apply filters
    filtered_entries = filter_by_session(all_entries, session_id)
    filtered_entries = filter_by_status(filtered_entries, filtered)

    # Sort by timestamp descending (newest first)
    filtered_entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    # Calculate pagination
    total = len(filtered_entries)
    has_more = (offset + limit) < total
    page_entries = filtered_entries[offset:offset + limit]

    return {
        'entries': page_entries,
        'total': total,
        'limit': limit,
        'offset': offset,
        'has_more': has_more
    }
