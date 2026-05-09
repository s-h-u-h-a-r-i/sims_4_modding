"""
bridge.py — HTTP bridge to the external AI service.

Sends world state snapshots to the AI server and receives back decisions.
Uses only stdlib (http.client + json) — no pip dependencies needed in-game.
"""
import http.client
import json
from typing import Any

_HOST = "localhost"
_PORT = 8765
_TIMEOUT_S = 5


def send_state(world_state: "dict[str, Any]") -> "dict[str, Any] | None":
    """
    POST world_state to the AI service, return the response payload.
    Returns None if the server is unreachable or returns an error.
    """
    # TODO: implement POST /state and handle response
    raise NotImplementedError


def fetch_decisions() -> "list[dict[str, Any]]":
    """
    GET pending AI decisions for NPCs from the AI service.
    Returns an empty list if nothing is ready or the server is down.
    """
    # TODO: implement GET /decisions
    raise NotImplementedError
