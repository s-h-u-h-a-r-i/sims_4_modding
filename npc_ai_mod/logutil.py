import traceback
from typing import Optional

from sims4.log import Logger

__all__ = ("log_error",)

_logger = Logger("NPCAIMod")


def log_error(tag: str, detail: str, exc: Optional[BaseException] = None) -> None:
    """Record a bridge/runtime error to the Sims 4 logger."""
    body = f"[{tag}] {detail}"
    if exc is not None:
        body = f"{body}\n{exc!r}\n{traceback.format_exc()}"
    _logger.error(body)
