import json
from typing import Any


def safe_json_load(value: str | None, default: Any = None) -> Any:
    """Parse a JSON string, returning `default` on any error or empty input."""
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default
