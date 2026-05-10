from datetime import datetime, timezone


def iso_utc_now():
    return datetime.now(timezone.utc).isoformat()
