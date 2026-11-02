# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/health_probe.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Runs the `healthCheck` an adapter manifest declares, for real, against the place an operator says the adapter is.

A manifest says HOW to check an adapter (`{"type": "http-get", "path": "/probe"}`); it does not say WHERE the adapter is, and that is on purpose:
the place comes from a deployment profile the operator writes (`--endpoints-file`), never from a manifest and never from a request. A profile is
a JSON object whose keys are adapter ids and whose values are `{"host": ..., "port": ..., "scheme": "http"|"https"}` (the scheme only for
`http-get`). The hub therefore opens a connection only to a host the operator listed, and only for an adapter that is in the registry.

What is run, and what each one proves (nothing more):

  * `http-get`   a GET of the declared `path`; healthy on a 2xx answer.
  * `tcp-connect` the port accepts a connection.
  * `mqtt-ping`  an MQTT 3.1.1 CONNECT is answered with a CONNACK; healthy only on "accepted". The declared `topic` is not read: a broker that
                 accepts a connection is alive, which is what the check can honestly say without credentials.
  * `opcua-read` an OPC UA Hello is answered with an Acknowledge. The declared node is NOT read (that needs a session with a certificate): the
                 result says `checked: "opcua-hello"`, so nobody takes a handshake for a value.
  * every other type (`serial-probe`, `gpio-read`, `rpc-ping`, `ros2-node-alive`, `mavlink-heartbeat`, `mqtt-topic-recent`, ...) needs hardware or a
    library this hub does not carry: the result is `supported: false`, never "healthy".

The check never raises for a network problem (that is an unhealthy result with the reason); it raises only for a profile or a manifest that is not
usable. TLS is certificate-verified; there is no switch to skip that.
"""
from __future__ import annotations

import json
import re
import socket
import ssl
import struct
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_HOST_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$|^\[[0-9A-Fa-f:.]+\]$")
_PATH_RE = re.compile(r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/-]{0,255}$")
DEFAULT_TIMEOUT_S = 3.0
MAX_TIMEOUT_S = 30.0
MAX_ANSWER_BYTES = 4096

SUPPORTED_TYPES = ("http-get", "tcp-connect", "mqtt-ping", "opcua-read")


class ProbeProfileError(ValueError):
    """The deployment profile (the places adapters are) cannot be used."""


@dataclass(frozen=True)
class Place:
    host: str
    port: int
    scheme: str = "http"


@dataclass(frozen=True)
class HealthResult:
    adapter_id: str
    check_type: str
    supported: bool
    healthy: bool
    detail: str
    latency_ms: float | None = None
    # what the check actually proved, in one word: "http", "tcp", "mqtt-connack", "opcua-hello"
    checked: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "adapterId": self.adapter_id,
            "type": self.check_type,
            "supported": self.supported,
            "healthy": self.healthy,
            "detail": self.detail,
        }
        if self.latency_ms is not None:
            out["latencyMs"] = round(self.latency_ms, 1)
        if self.checked is not None:
            out["checked"] = self.checked
        return out


def load_profile(path: str) -> dict[str, Place]:
    """The places from a profile file. An entry that is not a usable place stops the load: a half-read profile would probe the wrong thing."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProbeProfileError(f"the endpoints file cannot be read: {exc}") from exc
    if not isinstance(data, dict) or not data:
        raise ProbeProfileError("the endpoints file must be a JSON object with one entry per adapterId")
    places: dict[str, Place] = {}
    for adapter_id, entry in data.items():
        where = f"endpoints[{adapter_id!r}]"
        if not isinstance(entry, dict):
            raise ProbeProfileError(f"{where} must be an object")
        host, port, scheme = entry.get("host"), entry.get("port"), entry.get("scheme", "http")
        if not isinstance(host, str) or not _HOST_RE.match(host):
            raise ProbeProfileError(f"{where}.host must be a host name or an address")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ProbeProfileError(f"{where}.port must be a whole number from 1 to 65535")
        if scheme not in ("http", "https"):
            raise ProbeProfileError(f"{where}.scheme must be http or https")
        places[adapter_id] = Place(host=host, port=port, scheme=scheme)
    return places


def _timeout(manifest: dict[str, Any], override: float | None) -> float:
    if override is not None:
        return max(0.1, min(float(override), MAX_TIMEOUT_S))
    declared = manifest.get("timeoutMs")
    if isinstance(declared, int) and not isinstance(declared, bool) and declared > 0:
        return max(0.1, min(declared / 1000.0, MAX_TIMEOUT_S))
    return DEFAULT_TIMEOUT_S


def _read_exact(sock: socket.socket, count: int) -> bytes:
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            break
        data += chunk
    return data


def _probe_tcp(place: Place, timeout: float) -> tuple[bool, str]:
    with socket.create_connection((place.host.strip("[]"), place.port), timeout=timeout):
        return True, f"{place.host}:{place.port} accepts connections"


def _probe_http(place: Place, path: str, timeout: float) -> tuple[bool, str]:
    if not _PATH_RE.match(path) or ".." in path:
        raise ProbeProfileError(f"the healthCheck path {path!r} is not a usable path")
    url = f"{place.scheme}://{place.host}:{place.port}{path}"
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "hydra-umc-connector-hub-probe"})
    context = ssl.create_default_context() if place.scheme == "https" else None
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:  # noqa: S310 - scheme is http/https by construction
            response.read(MAX_ANSWER_BYTES)
            return 200 <= response.status < 300, f"GET {path} answered {response.status}"
    except urllib.error.HTTPError as exc:
        return False, f"GET {path} answered {exc.code}"


def _probe_mqtt(place: Place, timeout: float) -> tuple[bool, str]:
    client_id = b"hydra-hub-probe"
    variable = b"\x00\x04MQTT" + bytes([4, 0x02]) + struct.pack(">H", 10)
    payload = struct.pack(">H", len(client_id)) + client_id
    body = variable + payload
    packet = bytes([0x10, len(body)]) + body
    with socket.create_connection((place.host.strip("[]"), place.port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(packet)
        answer = _read_exact(sock, 4)
        try:
            sock.sendall(b"\xe0\x00")  # DISCONNECT, politely
        except OSError:
            pass
    if len(answer) < 4 or answer[0] != 0x20 or answer[1] != 0x02:
        return False, "the peer did not answer the MQTT CONNECT with a CONNACK"
    code = answer[3]
    return (True, "the broker accepted the connection") if code == 0 else (False, f"the broker refused the connection (return code {code})")


def _probe_opcua(place: Place, timeout: float) -> tuple[bool, str]:
    endpoint = f"opc.tcp://{place.host}:{place.port}".encode("ascii")
    body = struct.pack("<IIIII", 0, 65536, 65536, 0, 0) + struct.pack("<i", len(endpoint)) + endpoint
    message = b"HELF" + struct.pack("<I", 8 + len(body)) + body
    with socket.create_connection((place.host.strip("[]"), place.port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(message)
        answer = _read_exact(sock, 8)
    kind = answer[:4]
    if kind == b"ACKF":
        return True, "the server acknowledged the OPC UA Hello (the declared node was not read)"
    if kind == b"ERRF":
        return False, "the server answered the OPC UA Hello with an error"
    return False, "the peer did not answer the OPC UA Hello"


def run_health_check(manifest: dict[str, Any], place: Place, *, timeout: float | None = None) -> HealthResult:
    """Runs the check the manifest declares against `place`. Never raises for a network problem."""
    adapter_id = str(manifest.get("adapterId", ""))
    check = manifest.get("healthCheck")
    if not isinstance(check, dict) or not isinstance(check.get("type"), str):
        return HealthResult(adapter_id, "", False, False, "the manifest declares no healthCheck type")
    check_type = check["type"]
    if check_type not in SUPPORTED_TYPES:
        return HealthResult(adapter_id, check_type, False, False, f"the hub cannot run a {check_type!r} check: it needs hardware or a library it does not carry")
    seconds = _timeout(manifest, timeout)
    started = time.perf_counter()
    try:
        if check_type == "http-get":
            healthy, detail = _probe_http(place, str(check.get("path", "/")), seconds)
            checked = "http"
        elif check_type == "tcp-connect":
            healthy, detail = _probe_tcp(place, seconds)
            checked = "tcp"
        elif check_type == "mqtt-ping":
            healthy, detail = _probe_mqtt(place, seconds)
            checked = "mqtt-connack"
        else:
            healthy, detail = _probe_opcua(place, seconds)
            checked = "opcua-hello"
    except ProbeProfileError:
        raise
    except (OSError, ssl.SSLError, ValueError) as exc:
        return HealthResult(adapter_id, check_type, True, False, f"the check failed: {type(exc).__name__}: {exc}", (time.perf_counter() - started) * 1000, None)
    return HealthResult(adapter_id, check_type, True, healthy, detail, (time.perf_counter() - started) * 1000, checked)


class ProbeCache:
    """Remembers the last result of each adapter for `ttl` seconds, so asking again and again cannot turn the hub into a flood against a plant device."""

    def __init__(self, ttl: float = 5.0, clock=time.monotonic) -> None:  # type: ignore[no-untyped-def]
        self._ttl = ttl
        self._clock = clock
        self._entries: dict[str, tuple[float, HealthResult]] = {}

    def get_or_run(self, adapter_id: str, run) -> HealthResult:  # type: ignore[no-untyped-def]
        now = self._clock()
        cached = self._entries.get(adapter_id)
        if cached is not None and now - cached[0] < self._ttl:
            return cached[1]
        result = run()
        self._entries[adapter_id] = (self._clock(), result)
        return result
