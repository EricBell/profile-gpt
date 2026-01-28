import json
import os
from datetime import datetime


def log_interaction(
    log_path: str,
    session_id: str,
    query: str,
    response: str,
    filtered_pre_llm: bool = False,
    filter_category: str = None
) -> None:
    """Log a chat interaction in NDJSON format.

    Args:
        log_path: Directory path for log files
        session_id: Unique session identifier
        query: User's query text
        response: Assistant's response text
        filtered_pre_llm: Whether query was filtered before LLM call
        filter_category: Category of filter that caught the query (if filtered)
    """
    try:
        # Ensure log directory exists
        os.makedirs(log_path, exist_ok=True)

        # Daily filename: YYMMDD-Queries.ndjson
        filename = datetime.now().strftime('%y%m%d') + '-Queries.ndjson'
        filepath = os.path.join(log_path, filename)

        # Build log entry
        entry = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "filtered_pre_llm": filtered_pre_llm,
            "filter_category": filter_category
        }

        # Append NDJSON line
        with open(filepath, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        # Don't let logging failures break the app
        pass
