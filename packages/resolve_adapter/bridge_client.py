"""
CutPilot In-App Resolve Bridge Client
Transparent proxy client connecting to the in-Resolve loopback bridge over 127.0.0.1:49632.
Adapted from samuelgursky/davinci-resolve-mcp (c) 2026 Samuel Gursky under MIT License.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cutpilot.resolve-bridge")

DEFAULT_CONFIG_PATH = Path.home() / ".config/davinci-resolve-mcp/bridge.json"
APP_DATA_RUNTIME_CONFIG = (
    Path(os.environ.get("APPDATA", ""))
    / "Blackmagic Design"
    / "DaVinci Resolve"
    / "Support"
    / "Fusion"
    / ".davinci_mcp_runtime"
    / "bridge.json"
)

PROTOCOL_VERSION = "1.0"
DEFAULT_TIMEOUT_SECONDS = 30.0

class BridgeUnavailable(RuntimeError):
    """The in-Resolve bridge could not be reached."""
    pass

class BridgeCallError(RuntimeError):
    """The bridge refused or failed a call."""
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.details = details or {}

def get_bridge_config() -> Dict[str, Any]:
    """Finds and loads the bridge configuration from local AppData or ~/.config."""
    if APP_DATA_RUNTIME_CONFIG.is_file():
        cfg_path = APP_DATA_RUNTIME_CONFIG
    elif DEFAULT_CONFIG_PATH.is_file():
        cfg_path = DEFAULT_CONFIG_PATH
    else:
        raise BridgeUnavailable(
            f"Bridge configuration not found at {APP_DATA_RUNTIME_CONFIG} or {DEFAULT_CONFIG_PATH}. "
            "Please start the bridge from DaVinci Resolve: Workspace > Scripts > resolve_bridge."
        )

    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

def canonical_request(request: Dict[str, Any]) -> bytes:
    unsigned = {k: v for k, v in request.items() if k != "signature"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

def sign_request(token: str, request: Dict[str, Any]) -> str:
    return hmac.new(token.encode("utf-8"), canonical_request(request), hashlib.sha256).hexdigest()

def _encode_argument(value: Any) -> Any:
    if isinstance(value, BridgeProxy):
        return {"__handle__": value._handle}
    if isinstance(value, dict):
        return {k: _encode_argument(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode_argument(v) for v in value]
    return value

def _decode_value(transport: BridgeTransport, value: Any) -> Any:
    if isinstance(value, dict):
        handle = value.get("__handle__")
        if handle is not None:
            return BridgeProxy(
                transport,
                handle,
                type_name=value.get("__type__"),
                shape=value.get("__shape__")
            )
        return {k: _decode_value(transport, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode_value(transport, v) for v in value]
    return value

class BridgeTransport:
    def __init__(self, host: str, port: int, token: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.timeout = timeout
        self.method_cache: Dict[str, frozenset] = {}
        self.cache_lock = threading.Lock()
        self._socket_lock = threading.Lock()

    def request(self, operation: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        payload = {
            "protocol": PROTOCOL_VERSION,
            "id": str(uuid.uuid4()),
            "timestamp": int(time.time()),
            "nonce": secrets.token_urlsafe(16),
            "operation": operation,
            "arguments": arguments or {},
        }
        payload["signature"] = sign_request(self.token, payload)
        line = json.dumps(payload).encode("utf-8") + b"\n"

        with self._socket_lock:
            try:
                with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                    sock.settimeout(self.timeout)
                    sock.sendall(line)
                    raw = sock.makefile("rb").readline(1_048_576 + 1)
            except (TimeoutError, socket.timeout) as exc:
                raise BridgeCallError("bridge_timeout", "Resolve did not answer in time — check for open modal dialogs") from exc
            except OSError as exc:
                raise BridgeUnavailable(f"Cannot reach Resolve bridge on {self.host}:{self.port}: {exc}") from exc

        if not raw:
            raise BridgeCallError("bridge_protocol_error", "Bridge closed without replying")

        response = json.loads(raw.decode("utf-8"))
        if response.get("ok") is not True:
            err = response.get("error") or {}
            raise BridgeCallError(err.get("code", "bridge_error"), err.get("message", "Bridge refused call"), err.get("details"))

        return response.get("result")

class _BoundMethod:
    __slots__ = ("_transport", "_handle", "_name")

    def __init__(self, transport: BridgeTransport, handle: str, name: str) -> None:
        self._transport = transport
        self._handle = handle
        self._name = name

    def __call__(self, *args: Any) -> Any:
        result = self._transport.request(
            "call",
            {"target": self._handle, "method": self._name, "args": [_encode_argument(a) for a in args]}
        )
        return _decode_value(self._transport, (result or {}).get("value"))

class BridgeProxy:
    __slots__ = ("_transport", "_handle", "_type_name", "_shape")

    def __init__(self, transport: BridgeTransport, handle: str, *, type_name: Optional[str] = None, shape: Optional[str] = None) -> None:
        object.__setattr__(self, "_transport", transport)
        object.__setattr__(self, "_handle", handle)
        object.__setattr__(self, "_type_name", type_name)
        object.__setattr__(self, "_shape", shape)

    def _methods(self) -> frozenset:
        cache = self._transport.method_cache
        key = self._shape or self._handle
        cached = cache.get(key)
        if cached is not None:
            return cached
        res = self._transport.request("list_methods", {"target": self._handle}) or {}
        names = frozenset(res.get("methods") or ())
        with self._transport.cache_lock:
            cache[key] = names
        return names

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        methods = self._methods()
        if name not in methods:
            # Re-verify without cache
            refreshed = frozenset((self._transport.request("list_methods", {"target": self._handle}) or {}).get("methods") or ())
            with self._transport.cache_lock:
                self._transport.method_cache[self._shape or self._handle] = refreshed
            if name not in refreshed:
                raise AttributeError(f"{self._shape or 'Proxy'} has no attribute '{name}' in this Resolve build")
        return _BoundMethod(self._transport, self._handle, name)

    def __repr__(self) -> str:
        return f"<ResolveBridgeProxy handle={self._handle} shape={self._shape}>"

def connect_resolve(timeout: float = 10.0) -> BridgeProxy:
    """Connects to the running in-app DaVinci Resolve bridge and returns the resolve proxy object."""
    cfg = get_bridge_config()
    transport = BridgeTransport(cfg["host"], cfg["port"], cfg["token"], timeout=timeout)
    # Ping health
    transport.request("health")
    return BridgeProxy(transport, "resolve", shape="resolve")
