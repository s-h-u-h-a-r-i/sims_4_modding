from datetime import datetime, timezone

__all__ = ("iso_utc_now",)


def iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
