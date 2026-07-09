#!/usr/bin/env python3
"""Self-test for the BTicino diagnostics sanitization framework.

Exercises every function in
``custom_components/bticino_classe100x/diagnostics/sanitize.py`` and asserts that
each installation-specific value is redacted the way the diagnostics privacy
policy requires, while the debugging-useful parts survive.

The module is dependency-free (no Home Assistant import), so it is loaded
directly by file path and this self-test runs anywhere:

    python3 scripts/validate_sanitize.py

Exit code ``0`` means every assertion held.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SANITIZE_PATH = (
    REPO_ROOT
    / "custom_components"
    / "bticino_classe100x"
    / "diagnostics"
    / "sanitize.py"
)

_spec = importlib.util.spec_from_file_location("bticino_sanitize", SANITIZE_PATH)
assert _spec and _spec.loader
sanitize = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sanitize)

HOSTNAME = "C1X-00-03-50-b6-5f-fb-f4055f96-88f5-4523-ad76-3b19bf29a581"
KERNEL = (
    f"Linux {HOSTNAME} 3.10.14 #1 SMP PREEMPT Mon Jan 1 00:00:00 UTC 2024 armv7l"
)


def main() -> int:
    """Run every assertion and report the outcome."""
    checks: list[tuple[str, bool]] = []

    def check(label: str, passed: bool) -> None:
        checks.append((label, passed))

    # Host: value dropped, address family preserved.
    check("IPv4 host redacted", sanitize.sanitize_host("192.168.50.251") == "<redacted-ipv4-address>")
    check("IPv6 host redacted", sanitize.sanitize_host("2001:db8::1") == "<redacted-ipv6-address>")
    check("hostname host redacted", sanitize.sanitize_host("classe100x.local") == "<redacted-hostname>")
    check("no host stays None", sanitize.sanitize_host(None) is None)
    check("host value not leaked", "192.168.50.251" not in (sanitize.sanitize_host("192.168.50.251") or ""))

    # Username: fully redacted.
    check("username redacted", sanitize.sanitize_username("root2") == "<redacted-username>")
    check("no username stays None", sanitize.sanitize_username(None) is None)

    # MAC: OUI kept, device half masked. Both separators, and non-MAC untouched.
    check("MAC OUI kept", sanitize.sanitize_mac("00:03:50:b6:5f:fb") == "00:03:50:**:**:**")
    check("MAC hyphen form", sanitize.sanitize_mac("00-03-50-b6-5f-fb") == "00-03-50-**-**-**")
    check("MAC device half hidden", "b6:5f:fb" not in (sanitize.sanitize_mac("00:03:50:b6:5f:fb") or ""))
    check("non-MAC untouched", sanitize.sanitize_mac("not-a-mac") == "not-a-mac")
    check("no MAC stays None", sanitize.sanitize_mac(None) is None)

    # Hostname: model prefix kept, MAC/UUID tail redacted.
    sanitized_hostname = sanitize.sanitize_hostname(HOSTNAME)
    check("hostname keeps model prefix", sanitized_hostname == "C1X-<redacted>")
    check("hostname drops MAC", "00-03-50" not in (sanitized_hostname or ""))
    check("hostname drops UUID", "f4055f96" not in (sanitized_hostname or ""))
    check("bare hostname redacted", sanitize.sanitize_hostname("plainhost") == "<redacted-hostname>")
    check("no hostname stays None", sanitize.sanitize_hostname(None) is None)

    # Kernel: version kept, embedded node name removed (with and without hostname).
    sanitized_kernel = sanitize.sanitize_kernel(KERNEL, HOSTNAME)
    check("kernel drops hostname", HOSTNAME not in (sanitized_kernel or ""))
    check("kernel keeps version", "3.10.14" in (sanitized_kernel or ""))
    check("kernel keeps arch", "armv7l" in (sanitized_kernel or ""))
    check(
        "kernel node name redacted without hostname",
        HOSTNAME not in (sanitize.sanitize_kernel(KERNEL) or ""),
    )
    check("no kernel stays None", sanitize.sanitize_kernel(None) is None)

    # Error: secrets removed, the actual failure preserved.
    error = (
        "Failed to run ssh -i /home/root2/.ssh/id_rsa root2@192.168.50.251: "
        f"host {HOSTNAME} unreachable (timeout)"
    )
    sanitized_error = sanitize.sanitize_error(
        error,
        ssh_key_path="/home/root2/.ssh/id_rsa",
        host="192.168.50.251",
        hostname=HOSTNAME,
        username="root2",
    )
    check("error drops key path", "/home/root2/.ssh/id_rsa" not in (sanitized_error or ""))
    check("error drops host", "192.168.50.251" not in (sanitized_error or ""))
    check("error drops username", "root2" not in (sanitized_error or ""))
    check("error drops hostname", HOSTNAME not in (sanitized_error or ""))
    check("error keeps failure", "unreachable (timeout)" in (sanitized_error or ""))
    check("no error stays None", sanitize.sanitize_error(None, host="192.168.50.251") is None)

    # Prepared helpers for future fields.
    check("uuid redacted", sanitize.sanitize_uuid("f4055f96-88f5-4523-ad76-3b19bf29a581") == "<redacted-uuid>")
    check("serial redacted", sanitize.sanitize_serial_number("SN12345") == "<redacted-serial-number>")
    check("no uuid stays None", sanitize.sanitize_uuid(None) is None)

    ok = True
    for label, passed in checks:
        print(f"{'OK' if passed else 'FAIL'}: {label}")
        ok = ok and passed

    if ok:
        print(f"\nAll {len(checks)} sanitization assertions passed.")
        return 0

    print("\nSanitization self-test failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
