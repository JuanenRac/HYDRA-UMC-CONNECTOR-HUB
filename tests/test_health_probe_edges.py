# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_health_probe_edges.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Edge cases of the health probe that need no network: the timeout limits, the shape of a result, a manifest without a usable check, the host switch, the
device checks on files that are not devices, and the MAVLink frame finder on hostile input (fixed seed)."""
from __future__ import annotations

import random
import struct
import tempfile
import unittest

from hydra_umc_connector_hub import health_probe as hp


def _manifest(check: object, **extra: object) -> dict:
    return {"adapterId": "edge", "healthCheck": check, **extra}


class TimeoutLimits(unittest.TestCase):
    def test_an_override_wins_and_is_clamped(self) -> None:
        self.assertEqual(hp._timeout({"timeoutMs": 5000}, 0.01), 0.1)
        self.assertEqual(hp._timeout({"timeoutMs": 5000}, 9999), hp.MAX_TIMEOUT_S)
        self.assertEqual(hp._timeout({"timeoutMs": 5000}, 2.5), 2.5)

    def test_a_declared_timeout_is_clamped_and_a_bad_one_falls_back(self) -> None:
        self.assertEqual(hp._timeout({"timeoutMs": 1}, None), 0.1)
        self.assertEqual(hp._timeout({"timeoutMs": 10_000_000}, None), hp.MAX_TIMEOUT_S)
        self.assertEqual(hp._timeout({"timeoutMs": 1500}, None), 1.5)
        for bad in (0, -5, True, "2000", 1.5, None):
            self.assertEqual(hp._timeout({"timeoutMs": bad}, None), hp.DEFAULT_TIMEOUT_S, bad)
        self.assertEqual(hp._timeout({}, None), hp.DEFAULT_TIMEOUT_S)


class HostSwitch(unittest.TestCase):
    def test_only_the_exact_value_one_turns_the_active_probes_on(self) -> None:
        self.assertTrue(hp.active_probes_enabled({hp.ACTIVE_ENV: "1"}))
        for value in ("", "0", "true", "yes", " 1", "1 ", "11"):
            self.assertFalse(hp.active_probes_enabled({hp.ACTIVE_ENV: value}), repr(value))
        self.assertFalse(hp.active_probes_enabled({}))


class ResultShape(unittest.TestCase):
    def test_to_dict_leaves_out_what_was_not_measured(self) -> None:
        bare = hp.HealthResult("a", "tcp-connect", True, True, "up").to_dict()
        self.assertEqual(bare, {"adapterId": "a", "type": "tcp-connect", "supported": True, "healthy": True, "detail": "up"})
        full = hp.HealthResult("a", "mqtt-ping", True, True, "up", 12.345, "mqtt-pingresp", True).to_dict()
        self.assertEqual((full["latencyMs"], full["checked"], full["active"]), (12.3, "mqtt-pingresp", True))


class UnusableChecks(unittest.TestCase):
    def test_a_manifest_without_a_check_type_is_unsupported_and_never_healthy(self) -> None:
        place = hp.Place("127.0.0.1", 1)
        for check in (None, "tcp-connect", [], {}, {"type": 7}, {"type": None}):
            result = hp.run_health_check(_manifest(check), place)
            self.assertFalse(result.supported or result.healthy, check)
            self.assertIn("no healthCheck type", result.detail)

    def test_an_unknown_type_names_itself(self) -> None:
        result = hp.run_health_check(_manifest({"type": "telepathy"}), hp.Place("127.0.0.1", 1))
        self.assertFalse(result.supported or result.healthy)
        self.assertIn("telepathy", result.detail)

    def test_a_refused_port_is_an_unhealthy_result_and_not_an_exception(self) -> None:
        for check in ("tcp-connect", "mqtt-ping", "opcua-read", "rpc-ping", "ros2-node-alive", "mavlink-heartbeat"):
            result = hp.run_health_check(_manifest({"type": check}), hp.Place("127.0.0.1", 1), timeout=0.3)
            self.assertTrue(result.supported, check)
            self.assertFalse(result.healthy, check)
            self.assertTrue(result.detail.startswith("the check failed:"), check)
            self.assertIsNotNone(result.latency_ms)


class DeviceChecks(unittest.TestCase):
    def test_no_device_in_the_profile(self) -> None:
        for check in ("serial-probe", "gpio-read"):
            result = hp.run_health_check(_manifest({"type": check}), hp.Place("127.0.0.1", 0))
            self.assertFalse(result.healthy)
            self.assertIn("no device", result.detail)
            self.assertEqual(result.checked, "device-open")

    def test_a_missing_device_and_a_plain_file(self) -> None:
        missing = hp.run_health_check(_manifest({"type": "serial-probe"}), hp.Place("127.0.0.1", 0, device="/dev/does-not-exist-probe"))
        self.assertFalse(missing.healthy)
        with tempfile.NamedTemporaryFile() as plain:
            result = hp.run_health_check(_manifest({"type": "gpio-read"}), hp.Place("127.0.0.1", 0, device=plain.name))
        self.assertFalse(result.healthy)

    def test_the_active_device_exchange_refuses_what_is_not_a_device(self) -> None:
        self.assertEqual(hp._probe_device_exchange(hp.Place("h", 0, send=b"a", expect=b"b"), 0.2), (False, "the profile names no device for this adapter"))
        ok, detail = hp._probe_device_exchange(hp.Place("h", 0, device="/dev/does-not-exist-probe", send=b"a", expect=b"b"), 0.2)
        self.assertFalse(ok)
        self.assertIn("does not exist", detail)
        with tempfile.NamedTemporaryFile() as plain:
            ok, detail = hp._probe_device_exchange(hp.Place("h", 0, device=plain.name, send=b"a", expect=b"b"), 0.2)
        self.assertFalse(ok)
        self.assertIn("not a character device", detail)

    def test_a_path_with_a_dotdot_is_refused_for_http(self) -> None:
        with self.assertRaises(hp.ProbeProfileError):
            hp._probe_http(hp.Place("127.0.0.1", 1), "/a/../b", 0.2)


class MavlinkFinder(unittest.TestCase):
    @staticmethod
    def v1(length: int = 9, msgid: int = 0, extra: int = 50) -> bytes:
        body = bytes([length, 1, 1, 1, msgid]) + bytes(length)
        return bytes([254]) + body + struct.pack("<H", hp._x25(body + bytes([extra])))

    def test_only_a_heartbeat_of_the_right_length_and_extra_byte_counts(self) -> None:
        self.assertTrue(hp.find_mavlink_heartbeat(self.v1()))
        self.assertFalse(hp.find_mavlink_heartbeat(self.v1(length=8)))
        self.assertFalse(hp.find_mavlink_heartbeat(self.v1(extra=51)))
        self.assertFalse(hp.find_mavlink_heartbeat(self.v1(msgid=1)))

    def test_a_signed_or_incompatible_v2_frame_is_not_accepted(self) -> None:
        body = bytes([9, 1, 0, 1, 1, 1, 0, 0, 0]) + bytes(9)  # incompat flag 1 = signed
        frame = bytes([253]) + body + struct.pack("<H", hp._x25(body + bytes([50])))
        self.assertFalse(hp.find_mavlink_heartbeat(frame))

    def test_random_bytes_never_raise(self) -> None:
        rng = random.Random(20260101)
        for _ in range(300):
            data = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 80)))
            self.assertIsInstance(hp.find_mavlink_heartbeat(data), bool)

    def test_the_gcs_frame_is_a_valid_v2_heartbeat_of_a_ground_station(self) -> None:
        frame = hp.gcs_heartbeat_frame()
        self.assertTrue(hp.find_mavlink_heartbeat(frame))
        self.assertEqual((frame[0], frame[5], frame[6]), (0xFD, 255, 190))


if __name__ == "__main__":
    unittest.main()
