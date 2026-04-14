def clamp_limit(limit: int, default: int = 20, maximum: int = 100) -> int:
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        return default

    if parsed < 1:
        return default
    if parsed > maximum:
        return maximum
    return parsed
