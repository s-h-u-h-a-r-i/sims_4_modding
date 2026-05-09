import http.client
import json
from typing import Any, Dict, Optional

from .logutil import log_error

__all__ = ("post_tick",)

HOST = "127.0.0.1"
PATH = "/v1/tick"
PORT = 8765
TIMEOUT_SEC = 5


def post_tick(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    body = json.dumps(payload)
    conn = http.client.HTTPConnection(HOST, PORT, timeout=TIMEOUT_SEC)
    try:
        conn.request(
            "POST",
            PATH,
            body=body.encode("UTF-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
        )
        response = conn.getresponse()
        raw = response.read()
        if response.status != 200:
            snippet = raw.decode("utf-8", errors="replace")[:500]
            log_error(
                "bridge.post_tick",
                "HTTP {} {!r} http://{}:{}{} body={!r}".format(
                    response.status,
                    response.reason,
                    HOST,
                    PORT,
                    PATH,
                    snippet,
                ),
            )
            return None
        return json.loads(raw.decode("utf-8"))
    except (OSError, http.client.HTTPException, ValueError, json.JSONDecodeError) as exc:
        log_error(
            "bridge.post_tick",
            "{}:{}{} request failed".format(HOST, PORT, PATH),
            exc,
        )
        return None
    finally:
        conn.close()
