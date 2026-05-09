"""Session file log + sims4.log for npc_ai_mod."""

import os
import traceback
from typing import Optional

from sims4.log import Logger

FILE_LOG_BASENAME = "npc_ai_mod_bridge.log"

_logger = Logger("NPCAIMod")


def _file_log_path() -> Optional[str]:
    try:
        from sims4 import paths

        root = str(paths.USER_DOC_PATH)
        return os.path.join(root, FILE_LOG_BASENAME)
    except (ImportError, AttributeError, TypeError, ValueError):
        return None


def clear_session_file_log() -> None:
    """Truncate the bridge log on package load (new game / new session start)."""
    path = _file_log_path()
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("npc_ai_mod — session log started (package load)\n")
    except OSError as exc:
        _logger.error(
            "npc_ai_mod: could not clear file log at {}: {!r}".format(path, exc)
        )


def _append_file(msg: str) -> None:
    path = _file_log_path()
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(msg)
            if not msg.endswith("\n"):
                fh.write("\n")
    except OSError as exc:
        _logger.error(
            "npc_ai_mod: could not append file log: {!r}".format(exc)
        )


def log_error(tag: str, detail: str, exc: Optional[BaseException] = None) -> None:
    """Record a bridge/runtime error to sims4.log and the session file."""
    body = "[{}] {}".format(tag, detail)
    if exc is not None:
        body = "{}\n{!r}\n{}".format(body, exc, traceback.format_exc())
    _logger.error(body)
    _append_file(body + "\n")
