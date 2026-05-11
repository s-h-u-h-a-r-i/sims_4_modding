import http.client
import json
import typing

from ..logutil import log_error
from ..schemas import (
    TickPayload,
    TickResponse,
    parse_tick_response,
    tick_payload_to_wire,
)
from .constants import HOST, PATH, PORT, TIMEOUT_SEC

__all__ = ("post_tick",)


def post_tick(
    payload: TickPayload,
) -> typing.Optional[TickResponse]:
    body = json.dumps(tick_payload_to_wire(payload))
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
                f"HTTP {response.status} {response.reason!r} http://{HOST}:{PORT}{PATH} body={snippet!r}",
            )

            return None
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            log_error(
                "bridge.post_tick",
                "response JSON is not an object",
            )
            return None
        return parse_tick_response(parsed)
    except (
        OSError,
        http.client.HTTPException,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        log_error(
            "bridge.post_tick",
            f"{HOST}:{PORT}{PATH} request failed",
            exc,
        )
        return None
    finally:
        conn.close()
