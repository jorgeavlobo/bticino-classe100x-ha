#!/usr/bin/env python3
"""Self-test for the BTicino device-information parsing.

Exercises the pure parsing helpers in
``custom_components/bticino_classe100x/api/device_information.py`` — the
``dbfiles_ws.xml`` tag extraction, the ``/etc/version`` build-timestamp
formatting, and the marker-delimited section parser — and asserts they return
the values issue #37 requires (real firmware version, model and installed
package from ``dbfiles_ws.xml``; ``/etc/version`` reformatted as a build date),
while degrading gracefully when the file or a tag is missing.

The module imports its SSH client at import time, so it is loaded with a tiny
stub standing in for that dependency; the parsing helpers themselves are pure
and need nothing from Home Assistant, so this self-test runs anywhere:

    python3 scripts/validate_device_information.py

Exit code ``0`` means every assertion held.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

REPO_ROOT = Path(__file__).resolve().parents[1]
API_DIR = REPO_ROOT / "custom_components" / "bticino_classe100x" / "api"
DEVICE_INFO_PATH = API_DIR / "device_information.py"

# ``device_information`` does ``from .ssh_client import ...`` at import time.
# Register a stub package + stub ssh_client so the relative import resolves; the
# parsing helpers under test never touch it.
_PKG = "bticino_device_info_selftest"
_package = types.ModuleType(_PKG)
_package.__path__ = [str(API_DIR)]
sys.modules[_PKG] = _package

_ssh_stub = types.ModuleType(f"{_PKG}.ssh_client")
_ssh_stub.BticinoCommandFailedError = type(
    "BticinoCommandFailedError", (Exception,), {}
)
_ssh_stub.BticinoConnectionConfig = type("BticinoConnectionConfig", (), {})
_ssh_stub.BticinoSshClient = type("BticinoSshClient", (), {})
sys.modules[f"{_PKG}.ssh_client"] = _ssh_stub

_spec = importlib.util.spec_from_file_location(
    f"{_PKG}.device_information", DEVICE_INFO_PATH
)
if _spec is None or _spec.loader is None:
    raise SystemExit(f"could not load device_information module from {DEVICE_INFO_PATH}")
device_information = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = device_information
_spec.loader.exec_module(device_information)

Client = device_information.BticinoDeviceInformationClient

# A realistic dbfiles_ws.xml: ISO-8859-1, a comment, tags in any order.
DBFILES_WS = (
    '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
    "<dbfiles_ws>\n"
    "  <!-- web server configuration -->\n"
    "  <webserver_type>C100X</webserver_type>\n"
    "  <ver_webserver>1.5.8</ver_webserver>\n"
    "  <latest_sp>C100X_010508.fwz</latest_sp>\n"
    "</dbfiles_ws>\n"
)


def _device_output(dbfiles: str = DBFILES_WS, build: str = "20250522064330") -> str:
    """Build a marker-delimited SSH output like ``collect()`` parses.

    An empty ``dbfiles`` models a failed ``cat`` (missing file): the two markers
    end up consecutive with no content in between, exactly as on the device.
    """
    lines = ["__BTICINO_HOSTNAME__", "C1X-00-03-50-b6-5f-fb", "__BTICINO_DBFILES_WS__"]
    if dbfiles:
        lines.append(dbfiles)
    lines += [
        "__BTICINO_FIRMWARE_BUILD__",
        build,
        "__BTICINO_MAC_ADDRESSES__",
        "/sys/class/net/eth0/address=00:03:50:b6:5f:fb",
    ]
    return "\n".join(lines)


def main() -> int:
    """Run every assertion and report the outcome."""
    checks: list[tuple[str, bool]] = []

    def check(label: str, passed: bool) -> None:
        """Record one assertion result under a human-readable label."""
        checks.append((label, passed))

    # XML tag extraction: the three authoritative device fields.
    check("firmware version from ver_webserver", Client._extract_xml_tag(DBFILES_WS, "ver_webserver") == "1.5.8")
    check("model from webserver_type", Client._extract_xml_tag(DBFILES_WS, "webserver_type") == "C100X")
    check("installed package from latest_sp", Client._extract_xml_tag(DBFILES_WS, "latest_sp") == "C100X_010508.fwz")
    # Missing / empty / whitespace tags degrade to None or trim cleanly.
    check("missing tag is None", Client._extract_xml_tag(DBFILES_WS, "no_such_tag") is None)
    check("empty tag is None", Client._extract_xml_tag("<ver_webserver></ver_webserver>", "ver_webserver") is None)
    check("whitespace tag trimmed", Client._extract_xml_tag("<ver_webserver>  1.5.8  </ver_webserver>", "ver_webserver") == "1.5.8")
    check("empty document is None", Client._extract_xml_tag("", "ver_webserver") is None)

    # Build timestamp formatting.
    check("build timestamp formatted", Client._format_build("20250522064330") == "2025-05-22 06:43:30")
    check("build timestamp trimmed", Client._format_build("\n20250522064330\n") == "2025-05-22 06:43:30")
    check("no build stays None", Client._format_build(None) is None)
    check("blank build is None", Client._format_build("   ") is None)
    check("unexpected build falls back to raw", Client._format_build("1.5.8") == "1.5.8")

    # Section parsing wires the markers to the right fields.
    sections = Client._parse_sections(_device_output())
    check("dbfiles_ws section parsed", "ver_webserver" in sections.get("dbfiles_ws", ""))
    check("firmware_build section parsed", sections.get("firmware_build") == "20250522064330")
    check("hostname section parsed", sections.get("hostname") == "C1X-00-03-50-b6-5f-fb")
    # End to end: extract + format straight off the parsed sections.
    check("end-to-end firmware version", Client._extract_xml_tag(sections.get("dbfiles_ws") or "", "ver_webserver") == "1.5.8")
    check("end-to-end build", Client._format_build(sections.get("firmware_build")) == "2025-05-22 06:43:30")

    # Missing dbfiles_ws.xml (cat fails, no content): the section is absent, so
    # extraction returns None and the integration keeps working.
    empty = Client._parse_sections(_device_output(dbfiles=""))
    check("missing dbfiles_ws section absent", empty.get("dbfiles_ws") is None)
    check("missing dbfiles_ws yields None fields", Client._extract_xml_tag(empty.get("dbfiles_ws") or "", "ver_webserver") is None)

    ok = True
    for label, passed in checks:
        print(f"{'OK' if passed else 'FAIL'}: {label}")
        ok = ok and passed

    if ok:
        print(f"\nAll {len(checks)} device-information assertions passed.")
        return 0

    print("\nDevice-information self-test failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
