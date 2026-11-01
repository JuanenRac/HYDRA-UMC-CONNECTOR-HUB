# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_metrics_endpoint.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""GET /metrics of the catalog server: the text format of Prometheus with the version and the health of the registry directory, and nothing a
request carried."""
from __future__ import annotations

import re
import shutil
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from hydra_umc_connector_hub import __version__
from hydra_umc_connector_hub.catalog_server import serve_catalog

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@contextmanager
def serving(registry: Path) -> Iterator[str]:
    server = serve_catalog(str(registry), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _raw(url: str) -> tuple[int, str, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        with error:
            return error.code, error.headers.get("Content-Type", ""), error.read().decode("utf-8")


def test_metrics_are_the_prometheus_text_with_the_version_and_the_health() -> None:
    with serving(FIXTURES_DIR) as base:
        status, kind, text = _raw(base + "/metrics")
    assert status == 200
    assert kind == "text/plain; version=0.0.4; charset=utf-8"
    assert f'hydra_umc_service_info{{service="hydra-umc-connector-hub",version="{__version__}"}} 1' in text
    assert re.search(r'^hydra_umc_service_health\{service="hydra-umc-connector-hub"\} 1$', text, re.MULTILINE)
    assert re.search(r'^hydra_umc_service_health_check\{service="hydra-umc-connector-hub",check="registry_directory"\} 1$', text, re.MULTILINE)


def test_a_registry_directory_that_vanished_makes_the_service_unhealthy_but_still_answers(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    shutil.copytree(FIXTURES_DIR, registry)
    with serving(registry) as base:
        shutil.rmtree(registry)
        status, _, text = _raw(base + "/metrics")
    assert status == 200
    assert re.search(r'^hydra_umc_service_health\{service="hydra-umc-connector-hub"\} 0$', text, re.MULTILINE)


def test_metrics_carry_nothing_a_request_carried() -> None:
    with serving(FIXTURES_DIR) as base:
        _raw(base + "/no-such-route?adapter=very-private-name")
        _, _, text = _raw(base + "/metrics?token=leaked-secret")
    for needle in ("very-private-name", "leaked-secret", "no-such-route", "127.0.0.1"):
        assert needle not in text
