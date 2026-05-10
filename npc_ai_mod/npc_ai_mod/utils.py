from datetime import datetime, timezone


def iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
