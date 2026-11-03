# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_collect_and_gate_service.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Collecting the manifests that the bridges publish, and the capability gate served over HTTP with every decision recorded."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from hydra_umc_connector_hub.collect import collect_manifests
from hydra_umc_connector_hub.gate_audit import GateAudit, GateAuditError, load_key, verify_records
from hydra_umc_connector_hub.gate_server import CellStateError, GateServiceConfig, serve_gate

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
KEY = b"identity-key-of-the-server-0123456789"


def make_token(role="operator", key=KEY, *, alg="HS256", exp_in=300, username="ana", **extra) -> str:
    """A token shaped like the one HYDRA-UMC-SERVER issues (HS256, claims username, role, exp)."""
    import base64
    import hashlib
    import hmac
    import time

    def part(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()

    claims = {"username": username, "role": role, "exp": int(time.time()) + exp_in, "id": "u1", "tokenVersion": 1}
    claims.update(extra)
    claims = {k: v for k, v in claims.items() if v is not None}
    signing = f"{part({'alg': alg, 'typ': 'JWT'})}.{part(claims)}"
    signature = base64.urlsafe_b64encode(hmac.new(key, signing.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    return f"{signing}.{signature}"


TOKEN = make_token("operator")


def _sdk_available() -> bool:
    try:
        import hydra_umc_sdk.bridge_contract  # noqa: F401
    except ImportError:
        return False
    return True


def _project(root: Path, name: str, manifest: dict | None = None, *, claimed_name: str | None = None, where: str = "docs/adapter-manifest.json") -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "hydra-umc.project.json").write_text(json.dumps({"name": claimed_name or name}))
    if manifest is not None:
        target = directory / where
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest))
    return directory


def _manifest(adapter_id: str, owner: str) -> dict:
    data = json.loads((FIXTURES / "industrial-opcua.json").read_text(encoding="utf-8"))
    data["adapterId"] = adapter_id
    data["ownerProject"] = owner
    return data


class CollectTests(unittest.TestCase):
    def test_collects_what_a_project_publishes_about_itself_and_only_that(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, registry = Path(tmp) / "eco", Path(tmp) / "registry"
            root.mkdir()
            _project(root, "HYDRA-UMC-ONE", _manifest("one", "HYDRA-UMC-ONE"))
            _project(root, "HYDRA-UMC-TWO", _manifest("two-a", "HYDRA-UMC-TWO"), where="docs/adapter-manifests/a.json")
            _project(root, "HYDRA-UMC-LIAR", _manifest("liar", "HYDRA-UMC-ONE"))  # claims to be another project
            _project(root, "HYDRA-UMC-FAKE", _manifest("fake", "HYDRA-UMC-FAKE"), claimed_name="HYDRA-UMC-SOMEONE")  # its own manifest says another name
            _project(root, "HYDRA-UMC-THIEF", _manifest("one", "HYDRA-UMC-THIEF"))  # wants an adapterId already taken
            broken = _manifest("broken", "HYDRA-UMC-BROKEN")
            del broken["healthCheck"]
            _project(root, "HYDRA-UMC-BROKEN", broken)
            _project(root, "HYDRA-UMC-EMPTY")
            (root / "not-a-project").mkdir()

            dry = collect_manifests(str(root), str(registry))
            self.assertFalse(registry.exists())  # a plain run writes nothing
            self.assertEqual(dry.to_dict()["collected"], ["one", "two-a"])
            report = collect_manifests(str(root), str(registry), apply=True)
            self.assertEqual(sorted(p.name for p in registry.glob("*.json")), ["one.json", "two-a.json"])
            skipped = report.to_dict()["skipped"]
            self.assertEqual(len(skipped), 4)
            self.assertIn("not the checkout it was found in", skipped["HYDRA-UMC-LIAR/docs/adapter-manifest.json"][0])
            self.assertIn("does not say it is", skipped["HYDRA-UMC-FAKE/docs/adapter-manifest.json"][0])
            self.assertIn("already belongs to", skipped["HYDRA-UMC-THIEF/docs/adapter-manifest.json"][0])
            self.assertTrue(skipped["HYDRA-UMC-BROKEN/docs/adapter-manifest.json"])
            # a second run finds nothing new; an edited manifest of its owner replaces the file, the others are untouched
            again = collect_manifests(str(root), str(registry), apply=True)
            self.assertEqual(again.to_dict()["unchanged"], ["one", "two-a"])
            self.assertEqual(again.to_dict()["collected"], [])
            changed = _manifest("one", "HYDRA-UMC-ONE")
            changed["timeoutMs"] = 777
            (root / "HYDRA-UMC-ONE" / "docs" / "adapter-manifest.json").write_text(json.dumps(changed))
            third = collect_manifests(str(root), str(registry), apply=True)
            self.assertEqual(third.to_dict()["collected"], ["one"])
            self.assertEqual(json.loads((registry / "one.json").read_text())["timeoutMs"], 777)

    def test_a_folder_that_is_not_there_is_an_error(self):
        with self.assertRaises(NotADirectoryError):
            collect_manifests("/no/such/root", "/no/such/registry")


class GateAuditTests(unittest.TestCase):
    def test_the_chain_verifies_and_a_changed_or_cut_line_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            key = b"k" * 20
            audit = GateAudit(str(path), key)
            for n in range(3):
                audit.append({"allowed": n % 2 == 0, "reason": f"r{n}"})
            self.assertEqual(audit.head()["seq"], 3)
            # opened again, it continues the chain
            again = GateAudit(str(path), key)
            self.assertEqual(again.append({"allowed": True, "reason": "next"})["seq"], 4)
            lines = path.read_text().splitlines()
            # edited
            tampered = json.loads(lines[1])
            tampered["allowed"] = True
            edited = Path(tmp) / "edited.jsonl"
            edited.write_text("\n".join([lines[0], json.dumps(tampered), *lines[2:]]) + "\n")
            with self.assertRaises(GateAuditError):
                GateAudit(str(edited), key)
            # a line taken out of the middle
            cut = Path(tmp) / "cut.jsonl"
            cut.write_text("\n".join([lines[0], *lines[2:]]) + "\n")
            with self.assertRaises(GateAuditError):
                GateAudit(str(cut), key)
            # the right content under another key
            with self.assertRaises(GateAuditError):
                GateAudit(str(path), b"other-key-of-20-chars")
            # unsigned file opened unsigned
            plain = Path(tmp) / "plain.jsonl"
            GateAudit(str(plain)).append({"allowed": True, "reason": "x"})
            GateAudit(str(plain))
            with self.assertRaises(GateAuditError):
                verify_records([{"seq": 2}], None)

    def test_a_short_key_and_an_unwritable_file_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            short = Path(tmp) / "short.key"
            short.write_text("abc")
            with self.assertRaises(GateAuditError):
                load_key(str(short))
            audit = GateAudit(str(Path(tmp) / "a.jsonl"))
            audit._path = Path(tmp)  # a directory cannot be opened for appending
            with self.assertRaises(GateAuditError):
                audit.append({"allowed": True})


class GateServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.registry = self.dir / "registry"
        self.registry.mkdir()
        manifest = json.loads((FIXTURES / "industrial-mqtt.json").read_text(encoding="utf-8"))
        (self.registry / "industrial-mqtt.json").write_text(json.dumps(manifest))
        self.audit = GateAudit(str(self.dir / "audit.jsonl"), b"k" * 20)

    def _serve(self, **kwargs):
        config = GateServiceConfig(str(self.registry), kwargs.pop("audit", self.audit), **{"identity_key": KEY, **kwargs})
        server = serve_gate(config, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close()))
        return config, f"http://127.0.0.1:{server.server_port}"

    def _call(self, base, method, path, body=None, token=TOKEN, content_type="application/json", raw=None):
        data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
        headers = {"Content-Type": content_type} if data is not None else {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    GOOD = {
        "adapterId": "industrial-mqtt",
        "capability": "publishCommandTopic",
        "jobId": "job-1",
        "source": "test-suite",
        "cellState": "READY",
        "machineState": "IDLE",
        "observedMachineState": "IDLE",
        "grantedPermissions": ["mqtt.publish.command"],
        "cellMode": "operational",
        "satisfiedSafetyGates": ["cell.estop.clear"],
    }

    def test_it_needs_a_signed_token_and_answers_only_a_caller_that_holds_one(self):
        with self.assertRaises(ValueError):
            GateServiceConfig(str(self.registry), self.audit, identity_key=b"short")
        with self.assertRaises(ValueError):  # no key and no explicit loopback switch: it cannot answer anybody
            GateServiceConfig(str(self.registry), self.audit)
        _, base = self._serve()
        self.assertEqual(self._call(base, "GET", "/health", token=None)[0], 200)
        self.assertEqual(self._call(base, "POST", "/gate/evaluate", self.GOOD, token=None)[0], 401)
        self.assertEqual(self._call(base, "POST", "/gate/evaluate", self.GOOD, token="x" * 24)[0], 401)
        self.assertEqual(self._call(base, "GET", "/gate/audit", token=None)[0], 401)
        self.assertEqual(self._call(base, "POST", "/gate/other", {})[0], 404)
        self.assertEqual(self._call(base, "POST", "/gate/evaluate", raw=b"{", content_type="application/json")[0], 400)
        self.assertEqual(self._call(base, "POST", "/gate/evaluate", raw=b"[]", content_type="application/json")[0], 400)
        self.assertEqual(self._call(base, "POST", "/gate/evaluate", raw=b"{}", content_type="text/plain")[0], 415)
        self.assertEqual(self.audit.head(), None)  # nothing that was refused before the gate is a decision

    def test_a_missing_permission_is_denied_and_recorded_without_needing_the_sdk(self):
        config, base = self._serve()
        body = dict(self.GOOD, grantedPermissions=[])
        status, answer = self._call(base, "POST", "/gate/evaluate", body)
        self.assertEqual(status, 200)
        self.assertFalse(answer["allowed"])
        self.assertIn("lacks required permission", answer["reason"])
        self.assertEqual(answer["auditSeq"], 1)
        status, answer = self._call(base, "POST", "/gate/evaluate", {"adapterId": "nope", "capability": "x"})
        self.assertFalse(answer["allowed"])
        self.assertIn("no registered adapter", answer["reason"])
        status, answer = self._call(base, "POST", "/gate/evaluate", {"adapterId": "industrial-mqtt", "capability": "publishCommandTopic"})
        self.assertFalse(answer["allowed"])  # no jobId: the library refuses before any gate
        audit = self._call(base, "GET", "/gate/audit")[1]
        self.assertEqual(audit["head"]["seq"], 3)
        self.assertEqual((audit["decisions"], audit["denials"]), (3, 3))
        self.assertTrue(audit["signed"])
        verify_records(self.audit.recent(10), b"k" * 20)

    @unittest.skipUnless(_sdk_available(), "the optional hydra-umc-sdk is not installed")
    def test_an_allowed_call_goes_through_the_sdk_gate_and_is_recorded(self):
        _, base = self._serve()
        status, answer = self._call(base, "POST", "/gate/evaluate", self.GOOD)
        self.assertEqual(status, 200)
        self.assertTrue(answer["allowed"], answer)
        self.assertTrue(answer["observed"])
        self.assertEqual(answer["cellStateSource"], "attested")
        # the machine is not idle: the SDK gate says no
        busy = dict(self.GOOD, observedMachineState="RUNNING", jobId="job-2")
        self.assertFalse(self._call(base, "POST", "/gate/evaluate", busy)[1]["allowed"])
        # a claim without an observation is refused unless the caller says it could not observe
        claim = {k: v for k, v in self.GOOD.items() if k != "observedMachineState"}
        self.assertFalse(self._call(base, "POST", "/gate/evaluate", claim)[1]["allowed"])
        self.assertTrue(self._call(base, "POST", "/gate/evaluate", dict(claim, allowUnobserved=True))[1]["allowed"])
        lines = [json.loads(line) for line in (self.dir / "audit.jsonl").read_text().splitlines()]
        self.assertEqual([line["allowed"] for line in lines], [True, False, False, True])

    @unittest.skipUnless(_sdk_available(), "the optional hydra-umc-sdk is not installed")
    def test_a_cell_state_provider_is_believed_over_the_caller(self):
        state = {"value": "READY", "fail": False}

        def provider():
            if state["fail"]:
                raise CellStateError("the monitor is down")
            return state["value"], 0.0

        config, base = self._serve(cell_state=provider)
        answer = self._call(base, "POST", "/gate/evaluate", dict(self.GOOD, cellState="INHIBITED"))[1]
        self.assertTrue(answer["allowed"], answer)  # the caller claimed INHIBITED; the service read READY
        self.assertEqual(answer["cellStateSource"], "observed")
        state["value"] = "INHIBITED"
        answer = self._call(base, "POST", "/gate/evaluate", dict(self.GOOD, cellState="READY", jobId="job-2"))[1]
        self.assertFalse(answer["allowed"])  # the caller claimed READY; the service read INHIBITED
        state["fail"] = True
        answer = self._call(base, "POST", "/gate/evaluate", dict(self.GOOD, jobId="job-3"))[1]
        self.assertFalse(answer["allowed"])
        self.assertIn("monitor is down", answer["reason"])

    def test_a_decision_that_cannot_be_recorded_is_a_denial(self):
        class Broken(GateAudit):
            def append(self, decision):
                raise GateAuditError("disk full")

        _, base = self._serve(audit=Broken(str(self.dir / "broken.jsonl")))
        status, answer = self._call(base, "POST", "/gate/evaluate", self.GOOD)
        self.assertEqual(status, 503)
        self.assertFalse(answer["allowed"])
        self.assertIn("could not be recorded", answer["reason"])

    def test_the_decision_is_sent_to_the_data_lake_when_one_is_set(self):
        received = []

        import http.server

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                received.append((self.path, self.headers.get("Authorization"), json.loads(self.rfile.read(length))))
                self.send_response(202)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args):
                pass

        lake = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=lake.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (lake.shutdown(), lake.server_close()))
        _, base = self._serve(datalake_url=f"http://127.0.0.1:{lake.server_port}", datalake_token="lake-token-16-chars")
        self._call(base, "POST", "/gate/evaluate", dict(self.GOOD, grantedPermissions=[]))
        for _ in range(100):
            if received:
                break
            threading.Event().wait(0.05)
        self.assertTrue(received)
        path, authorization, sample = received[0]
        self.assertEqual(path, "/ingest")
        self.assertEqual(authorization, "Bearer lake-token-16-chars")
        self.assertEqual(sample["sourceId"], "gate:industrial-mqtt")
        self.assertEqual(sample["kind"], "gate_decision")
        self.assertEqual(sample["fields"]["allowed"], 0)
        self.assertEqual(sample["fields"]["capability.publishCommandTopic"], 1)


if __name__ == "__main__":
    unittest.main()
