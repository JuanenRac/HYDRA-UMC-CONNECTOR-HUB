# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/gate_server.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The capability gate as a small HTTP service, so a server written in another language (the OPC UA server, HYDRA-UMC-SERVER) can ask it before it forwards a
write or an abort, and every decision is recorded.

    POST /gate/evaluate   body: see below; answer 200 {"allowed": bool, "reason": ..., ...}   (a denial is also a 200: it is the answer)
    GET  /gate/audit      the head of the audit chain and the newest decisions
    GET  /health          {"status": "ok"}   (the only route without the bearer token)

It is the gate of `sdk_gate.py` (which is the gate of HYDRA-UMC-SDK) with three additions, none of which relaxes it:

  * A bearer token is REQUIRED (`--token-file`, at least 16 characters): the service decides whether a machine may move, so it does not answer anybody.
  * Every decision is appended to the audit chain (`gate_audit.py`) BEFORE the answer is given; if the line cannot be written the answer is a denial.
  * With a cell-state provider (`--cell-state-url`, the `GET /state` of HYDRA-UMC-SAFETY-ZONES or any service that answers
    `{"state": ..., "timestamp_utc": ...}`) the SDK cell state is READ by the service and the caller's own claim is ignored; a provider that is down,
    answers something unreadable or is older than `--cell-state-max-age-s` is a denial. Without a provider the caller's `cellState` is used and the
    answer says `cellStateSource: "attested"`, as the library gate always did.

Request body (JSON): `adapterId`, `capability`, `jobId`, `source` (who asks, for the audit), `idempotencyKey` (default: `<jobId>:<capability>`), `machineState`
(default `IDLE`), `observedMachineState`, `allowUnobserved` (bool), `cellState` (only without a provider), `grantedPermissions` (list), `cellMode`,
`humanConfirmed` (bool), `satisfiedSafetyGates` (list), `parameters` (object of strings), `evidence` (object). Nothing in a request can name a file, a path or
a URL: the manifest is looked up by `adapterId` in the registry directory the service was started with.

Optionally (`--datalake-url`) each decision is also sent to HYDRA-UMC-DATALAKE as a sample (`sourceId` `gate:<adapterId>`, `kind` `gate_decision`, fields
`allowed`, `capability.<name>`), best effort and without delay: the chain on disk is the record, the lake is the timeline.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlsplit

from . import __version__
from .gate_audit import GateAudit, GateAuditError
from .registry import load_full_manifest
from .sdk_gate import CapabilityCallRequest, CapabilityGateError, SdkUnavailableError, evaluate_capability_call
from .service_metrics import MetricsHandlerMixin

MAX_BODY_BYTES = 64 * 1024
MIN_TOKEN_LENGTH = 16
DEFAULT_CELL_STATE_MAX_AGE_S = 5.0

CellStateProvider = Callable[[], "tuple[str, float]"]


class CellStateError(RuntimeError):
    """The cell state could not be read or is too old."""


def http_cell_state_provider(url: str, token: str | None = None, *, timeout: float = 1.5, max_age_s: float = DEFAULT_CELL_STATE_MAX_AGE_S) -> CellStateProvider:
    """A provider that reads `url` (GET). Accepts `{"state", "timestamp_utc"}` or the `{"sdkSafetyState": {...}}` of HYDRA-UMC-SAFETY-ZONES."""

    def read() -> tuple[str, float]:
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - the operator chose this URL at start
                body = json.loads(response.read(64 * 1024).decode("utf-8"))
        except (OSError, ValueError) as exc:
            raise CellStateError(f"the cell state cannot be read: {exc}") from exc
        sdk = body.get("sdkSafetyState") if isinstance(body, dict) and isinstance(body.get("sdkSafetyState"), dict) else body
        state = sdk.get("state") if isinstance(sdk, dict) else None
        stamp = sdk.get("timestamp_utc") if isinstance(sdk, dict) else None
        if not isinstance(state, str) or not isinstance(stamp, str):
            raise CellStateError("the cell state answer has no state or no time")
        try:
            at = datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
        except ValueError as exc:
            raise CellStateError("the time of the cell state is not readable") from exc
        age = time.time() - at
        if age > max_age_s or age < -max_age_s:
            raise CellStateError(f"the cell state is {age:.1f} s old (at most {max_age_s:g} s)")
        return state, at

    return read


def _text(body: dict[str, Any], key: str, default: str = "") -> str:
    value = body.get(key)
    return value if isinstance(value, str) else default


def _string_list(value: Any, name: str) -> frozenset[str]:
    if value is None:
        return frozenset()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CapabilityGateError(f"{name!r} must be a list of strings")
    return frozenset(value)


def _decide(config: "GateServiceConfig", body: dict[str, Any]) -> dict[str, Any]:
    """The decision for one request body, as the dict that is audited and answered. Never raises."""
    adapter_id = body.get("adapterId")
    capability = body.get("capability")
    decision: dict[str, Any] = {
        "adapterId": adapter_id if isinstance(adapter_id, str) else None,
        "capability": capability if isinstance(capability, str) else None,
        "jobId": body.get("jobId") if isinstance(body.get("jobId"), str) else None,
        "source": body.get("source") if isinstance(body.get("source"), str) else None,
        "allowed": False,
        "reason": "",
        "evidenceErrors": [],
        "observed": False,
        "cellStateSource": None,
    }
    if not isinstance(adapter_id, str) or not isinstance(capability, str) or not adapter_id or not capability:
        decision["reason"] = "adapterId and capability are required strings"
        return decision
    try:
        manifest = load_full_manifest(config.registry_dir, adapter_id)
    except (OSError, ValueError):
        manifest = None
    if manifest is None:
        decision["reason"] = f"no registered adapter {adapter_id!r}"
        return decision
    if config.cell_state is not None:
        try:
            cell_state, _at = config.cell_state()
        except CellStateError as exc:
            decision["reason"] = str(exc)
            decision["cellStateSource"] = "observed"
            return decision
        decision["cellStateSource"] = "observed"
    else:
        cell_state = _text(body, "cellState")
        decision["cellStateSource"] = "attested"
    try:
        job_id = body.get("jobId")
        request = CapabilityCallRequest(
            job_id=job_id if isinstance(job_id, str) else "",
            idempotency_key=_text(body, "idempotencyKey", f"{job_id}:{capability}"),
            source=_text(body, "source"),
            capability_name=capability,
            cell_state=cell_state,
            machine_state=_text(body, "machineState", "IDLE"),
            parameters={str(k): str(v) for k, v in body["parameters"].items()} if isinstance(body.get("parameters"), dict) else {},
            evidence=body["evidence"] if isinstance(body.get("evidence"), dict) else None,
            granted_permissions=_string_list(body.get("grantedPermissions"), "grantedPermissions"),
            cell_mode=body.get("cellMode") if isinstance(body.get("cellMode"), str) else None,
            human_confirmed=body.get("humanConfirmed") is True,
            satisfied_safety_gates=_string_list(body.get("satisfiedSafetyGates"), "satisfiedSafetyGates"),
            observed_machine_state=body.get("observedMachineState") if isinstance(body.get("observedMachineState"), str) else None,
            allow_unobserved=body.get("allowUnobserved") is True,
        )
        result = evaluate_capability_call(manifest, request)
    except (CapabilityGateError, SdkUnavailableError) as exc:
        decision["reason"] = f"{type(exc).__name__}: {exc}"
        return decision
    decision.update(allowed=result.allowed, reason=result.reason, evidenceErrors=list(result.evidence_errors), observed=result.observed)
    return decision


class GateServiceConfig:
    def __init__(
        self,
        registry_dir: str,
        token: str,
        audit: GateAudit,
        cell_state: CellStateProvider | None = None,
        datalake_url: str | None = None,
        datalake_token: str | None = None,
    ) -> None:
        if len(token) < MIN_TOKEN_LENGTH:
            raise ValueError(f"the token must have at least {MIN_TOKEN_LENGTH} characters")
        self.registry_dir = registry_dir
        self.token = token
        self.audit = audit
        self.cell_state = cell_state
        self.datalake_url = datalake_url.rstrip("/") if datalake_url else None
        self.datalake_token = datalake_token
        self.decisions_made = 0
        self.denials_made = 0
        self._lock = threading.Lock()

    def count(self, allowed: bool) -> None:
        with self._lock:
            self.decisions_made += 1
            if not allowed:
                self.denials_made += 1


def _forward_to_lake(config: GateServiceConfig, decision: dict[str, Any], at_ms: int) -> None:
    if not config.datalake_url or not decision.get("adapterId"):
        return
    sample = {
        "sourceId": f"gate:{decision['adapterId']}"[:128],
        "kind": "gate_decision",
        "timestamp": at_ms,
        "fields": {"allowed": 1 if decision["allowed"] else 0, f"capability.{decision.get('capability') or 'unknown'}"[:128]: 1},
    }

    def send() -> None:
        headers = {"Content-Type": "application/json"}
        if config.datalake_token:
            headers["Authorization"] = f"Bearer {config.datalake_token}"
        request = urllib.request.Request(f"{config.datalake_url}/ingest", data=json.dumps(sample).encode("utf-8"), headers=headers, method="POST")
        try:
            urllib.request.urlopen(request, timeout=2).close()  # noqa: S310 - the operator chose this URL at start
        except OSError:
            pass  # best effort: the chain on disk is the record

    threading.Thread(target=send, daemon=True).start()


def make_handler(config: GateServiceConfig) -> type[BaseHTTPRequestHandler]:
    class GateHandler(MetricsHandlerMixin, BaseHTTPRequestHandler):
        server_version = "HydraUmcConnectorHubGate"
        metrics_service = "hydra-umc-connector-hub"
        metrics_version = __version__
        timeout = 15.0

        def _send_json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            header = self.headers.get("Authorization", "")
            import hmac

            return header.startswith("Bearer ") and hmac.compare_digest(header[len("Bearer "):].strip().encode("utf-8"), config.token.encode("utf-8"))

        def metrics_checks(self) -> dict[str, bool]:
            return {"audit_chain": True}

        def do_GET(self) -> None:  # noqa: N802
            route = urlsplit(self.path).path.rstrip("/") or "/"
            if route == "/health":
                self._send_json(200, {"status": "ok", "signed": config.audit.signed})
                return
            if not self._authorized():
                self._send_json(401, {"error": "a valid bearer token is required"})
                return
            if self.serve_metrics(authorized=True):
                return
            if route == "/gate/audit":
                self._send_json(200, {"head": config.audit.head(), "signed": config.audit.signed, "decisions": config.decisions_made, "denials": config.denials_made, "recent": config.audit.recent(50)})
                return
            self._send_json(404, {"error": "unknown route"})

        def do_POST(self) -> None:  # noqa: N802
            route = urlsplit(self.path).path.rstrip("/")
            if not self._authorized():
                self._send_json(401, {"error": "a valid bearer token is required"})
                return
            if route != "/gate/evaluate":
                self._send_json(404, {"error": "unknown route"})
                return
            if "application/json" not in self.headers.get("Content-Type", ""):
                self._send_json(415, {"error": "the body must be application/json"})
                return
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                length = -1
            if length < 0 or length > MAX_BODY_BYTES:
                self._send_json(413 if length > MAX_BODY_BYTES else 411, {"error": f"a Content-Length of at most {MAX_BODY_BYTES} bytes is required"})
                return
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                self._send_json(400, {"error": "the body is not valid JSON"})
                return
            if not isinstance(body, dict):
                self._send_json(400, {"error": "the body must be a JSON object"})
                return
            decision = _decide(config, body)
            try:
                record = config.audit.append(decision)
            except GateAuditError as exc:
                config.count(False)
                self._send_json(503, {"allowed": False, "reason": f"the decision could not be recorded, so it is a denial: {exc}"})
                return
            config.count(bool(decision["allowed"]))
            _forward_to_lake(config, decision, int(time.time() * 1000))
            answer = {k: decision[k] for k in ("allowed", "reason", "evidenceErrors", "observed", "cellStateSource")}
            answer["auditSeq"] = record["seq"]
            self._send_json(200, answer)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            import sys

            print(f"{self.address_string()} - {format % args}", file=sys.stderr)

    return GateHandler


def serve_gate(config: GateServiceConfig, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    """A bound server; the caller runs `serve_forever()`. Loopback unless told otherwise: the token is the only door, and a plain-HTTP token should not cross a network."""
    return ThreadingHTTPServer((host, port), make_handler(config))
