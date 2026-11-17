"""Common helpers.
Provides basic utilities shared across modules."""


def safe_text(value):
    """Safely convert a value to text; return an empty string for None."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "none" else text


def safe_bool(value):
    """Safely convert a value to a boolean."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in {'true', '1', 'yes', 'y', '是'}
