"""
Persistent WebSocket tick client (RFC 6455 text frames). stdlib only; Python 3.7.

Each successful ``exchange_tick`` sends one JSON text frame and reads one text
response (with automatic ping/pong handling). The socket is reused across ticks.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import struct
import typing

from ..logutil import log_error
from ..schemas import (
    TickPayload,
    TickResponse,
    parse_tick_response,
    tick_payload_to_wire,
)
from .constants import HOST, PORT, TICK_WEBSOCKET_PATH, TIMEOUT_SEC

__all__ = ("exchange_tick", "reset_persistent_connection")


_OP_TEXT = 0x1
_OP_PING = 0x9
_OP_PONG = 0xA
_OP_CLOSE = 0x8

_session: typing.Optional[_WsSession] = None


def reset_persistent_connection() -> None:
    """Close the reused WebSocket; call when leaving a zone or after errors."""
    global _session
    sess = _session
    _session = None
    if sess is not None:
        sess.close()


def exchange_tick(payload: TickPayload) -> typing.Optional[TickResponse]:
    """Send one JSON text frame and parse one JSON reply; reuse the TCP session."""
    global _session
    body_b = json.dumps(tick_payload_to_wire(payload)).encode("utf-8")
    try:
        sess = _session
        if sess is None:
            sess = _open_session()
            _session = sess
        _send_client_frame(sess, _OP_TEXT, body_b)
        raw = _recv_text_message(sess)
    except (OSError, UnicodeDecodeError) as exc:
        log_error("bridge.ws_tick", "WebSocket tick request failed", exc)
        reset_persistent_connection()
        return None
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        log_error("bridge.ws_tick", "WebSocket tick response is not valid JSON", exc)
        reset_persistent_connection()
        return None
    if not isinstance(parsed, dict):
        log_error(
            "bridge.ws_tick", "WebSocket tick response JSON is not an object", None
        )
        reset_persistent_connection()
        return None
    return parse_tick_response(parsed)


def _open_session() -> _WsSession:
    sock = socket.create_connection((HOST, PORT), TIMEOUT_SEC)
    sock.settimeout(TIMEOUT_SEC)
    try:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            "GET {path} HTTP/1.1\r\n"
            "Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        ).format(path=TICK_WEBSOCKET_PATH, host=HOST, port=PORT, key=key)
        sock.sendall(req.encode("latin-1"))
        tail = _consume_http_upgrade_head(sock)
        return _WsSession(sock, tail)
    except BaseException:
        sock.close()
        raise


def _send_client_frame(sess: _WsSession, opcode: int, payload: bytes) -> None:
    sess.sendall_raw(_encode_client_frame(opcode, payload))


def _recv_text_message(sess: _WsSession) -> str:
    while True:
        opcode, data = _read_frame(sess)
        if opcode == _OP_TEXT:
            return data.decode("utf-8")
        if opcode == _OP_PING:
            _send_client_frame(sess, _OP_PONG, data)
            continue
        if opcode == _OP_PONG:
            continue
        if opcode == _OP_CLOSE:
            raise OSError("WebSocket closed by peer")
        raise OSError("unsupported WebSocket frame opcode={}".format(opcode))


def _read_frame(sess: _WsSession) -> typing.Tuple[int, bytes]:
    h0, h1 = struct.unpack("!BB", sess.read_exactly(2))
    opcode = h0 & 0x0F
    masked = (h1 >> 7) & 1
    raw_len = h1 & 0x7F
    if raw_len == 126:
        raw_len = struct.unpack("!H", sess.read_exactly(2))[0]
    elif raw_len == 127:
        raw_len = struct.unpack("!Q", sess.read_exactly(8))[0]
    if masked:
        mask = sess.read_exactly(4)
        data = bytearray(sess.read_exactly(raw_len))
        for idx in range(len(data)):
            data[idx] ^= mask[idx % 4]
        return opcode, bytes(data)
    return opcode, sess.read_exactly(raw_len)


def _consume_http_upgrade_head(sock: socket.socket) -> bytes:
    buf = bytearray()
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise OSError("connection closed before WebSocket handshake completed")
        buf += chunk
    sep = buf.index(b"\r\n\r\n")
    head = buf[:sep].decode("latin-1", errors="replace")
    tail = bytes(buf[sep + 4 :])
    first_line = head.split("\r\n", 1)[0]
    parts = first_line.split()
    if len(parts) < 2 or parts[1] != "101":
        raise OSError(
            "WebSocket handshake expected HTTP 101, got {!r}".format(first_line)
        )
    return tail


def _encode_client_frame(opcode: int, payload: bytes) -> bytes:
    """One RFC 6455 client data frame with masking (FIN bit set)."""
    byte0 = 0x80 | (opcode & 0x0F)
    ln = len(payload)
    if ln < 126:
        first = bytes([byte0, 0x80 | ln])
    elif ln < 65536:
        first = bytes([byte0, 0x80 | 126]) + struct.pack("!H", ln)
    else:
        first = bytes([byte0, 0x80 | 127]) + struct.pack("!Q", ln)
    mask_key = os.urandom(4)
    masked = bytearray(payload)
    for idx in range(len(masked)):
        masked[idx] ^= mask_key[idx % 4]
    return first + mask_key + bytes(masked)


class _WsSession:
    __slots__ = ("_sock", "_buf")

    def __init__(self, sock: socket.socket, pending: bytes = b"") -> None:
        self._sock = sock
        self._buf = bytearray(pending)

    def close(self) -> None:
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self._sock.close()
        except OSError:
            pass
        self._buf.clear()

    def read_exactly(self, n: int) -> bytes:
        while len(self._buf) < n:
            self._fill()
        out = bytes(self._buf[:n])
        del self._buf[:n]
        return out

    def sendall_raw(self, data: bytes) -> None:
        self._sock.sendall(data)

    def _fill(self) -> None:
        chunk = self._sock.recv(65536)
        if not chunk:
            raise OSError("WebSocket connection closed")
        self._buf += chunk
