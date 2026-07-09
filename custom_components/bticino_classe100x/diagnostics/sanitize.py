"""Centralized sanitization for BTicino CLASSE100X diagnostics.

Diagnostics are meant to be attached to public GitHub issues, so every
installation-specific value passes through this module before it is exposed.
Sanitization lives here — never inline in ``__init__.py`` — so the privacy policy
has a single, testable home and future fields (serial numbers, UUIDs, …) can
reuse it without re-implementing redaction.

This module is deliberately dependency-free (no Home Assistant imports), so its
behaviour can be exercised directly by ``scripts/validate_sanitize.py``.

Redaction style:

- **Partial** keeps the debugging-useful, non-identifying part and masks the
  rest (MAC keeps the vendor OUI; hostname keeps the model prefix; host keeps
  only its address family; kernel keeps the version but drops the node name).
- **Full** replaces the whole value with a labelled placeholder.

Placeholders are hyphenated (no spaces) so a redacted token stays a single word
and survives whitespace-splitting (used when redacting the ``uname`` node name).
"""

from __future__ import annotations

import ipaddress
import re

HOST_IPV4 = "<redacted-ipv4-address>"
HOST_IPV6 = "<redacted-ipv6-address>"
REDACTED_HOSTNAME = "<redacted-hostname>"
REDACTED_USERNAME = "<redacted-username>"
REDACTED_UUID = "<redacted-uuid>"
REDACTED_SERIAL_NUMBER = "<redacted-serial-number>"

# ``uname -a`` prints "<sysname> <nodename> <release> …"; the node name (field 2)
# is the device hostname, redacted even when the hostname itself is unknown.
_UNAME = re.compile(r"^(\S+)\s+(\S+)(.*)$", re.DOTALL)


def sanitize_host(host: str | None) -> str | None:
    """Redact a host, preserving only whether it is an IPv4/IPv6/hostname.

    Policy: **full redaction** of the value. An RFC1918 address still describes
    the user's internal network, so the value is dropped; the address family is
    kept because it is useful for debugging and is not identifying.
    """
    if not host:
        return host
    try:
        return HOST_IPV6 if ipaddress.ip_address(host).version == 6 else HOST_IPV4
    except ValueError:
        return REDACTED_HOSTNAME


def sanitize_username(username: str | None) -> str | None:
    """Redact a username entirely.

    Policy: **full redaction**. Usernames are installation-specific and carry no
    debugging value once connectivity is otherwise reported.
    """
    if not username:
        return username
    return REDACTED_USERNAME


def sanitize_mac(mac_address: str | None) -> str | None:
    """Mask the device-specific half of a MAC address.

    Policy: **partial**. Only the vendor prefix (OUI) is kept for debugging;
    the unique portion is hidden to avoid publishing a stable device identifier.
    Accepts ``:`` or ``-`` separated MACs and leaves anything else untouched.
    """
    if not mac_address:
        return mac_address

    separator = ":" if ":" in mac_address else "-" if "-" in mac_address else None
    if separator is None:
        return mac_address

    parts = mac_address.split(separator)
    if len(parts) != 6:
        return mac_address

    return separator.join([*parts[:3], "**", "**", "**"])


def sanitize_hostname(hostname: str | None) -> str | None:
    """Keep the model prefix of a hostname and redact the identifying tail.

    Policy: **partial**. The CLASSE100X hostname embeds a MAC address and a
    generated UUID (for example ``C1X-00-03-50-b6-5f-fb-f4055f96-…``). The model
    prefix (``C1X``) is useful and not identifying, so it is kept while the rest
    is redacted. A hostname without a separator is redacted in full.
    """
    if not hostname:
        return hostname

    prefix, separator, _ = hostname.partition("-")
    if not separator or not prefix:
        return REDACTED_HOSTNAME
    return f"{prefix}-<redacted>"


def sanitize_kernel(kernel: str | None, hostname: str | None = None) -> str | None:
    """Redact the device hostname embedded in a ``uname -a`` string.

    Policy: **partial**. The kernel version and architecture are kept for
    debugging; only the embedded node name (the device hostname) is removed.
    The known hostname is redacted first; the ``uname`` node-name field is then
    redacted too, so the device id is removed even when the hostname is unknown.
    """
    if not kernel:
        return kernel

    result = kernel
    if hostname:
        result = result.replace(hostname, REDACTED_HOSTNAME)

    match = _UNAME.match(result)
    if match and match.group(2) != REDACTED_HOSTNAME:
        result = f"{match.group(1)} {REDACTED_HOSTNAME}{match.group(3)}"
    return result


def sanitize_error(
    error: str | None,
    *,
    ssh_key_path: str | None = None,
    host: str | None = None,
    hostname: str | None = None,
    username: str | None = None,
) -> str | None:
    """Redact installation-specific values echoed in an error message.

    Policy: **partial**. Error strings can echo the SSH command (private key
    path) and connection details; these are replaced with labelled placeholders
    while the rest of the message — the actual failure — is preserved. More
    specific values are redacted first so a shorter value (a username) cannot
    partially match inside a longer one (a key path that contains it).
    """
    if not error:
        return error

    result = error
    for value, placeholder in (
        (ssh_key_path, "<ssh-key-path>"),
        (hostname, "<hostname>"),
        (host, "<host>"),
        (username, "<username>"),
    ):
        if value:
            result = result.replace(value, placeholder)
    return result


def sanitize_uuid(value: str | None) -> str | None:
    """Redact a UUID entirely (prepared for future diagnostics fields)."""
    if not value:
        return value
    return REDACTED_UUID


def sanitize_serial_number(value: str | None) -> str | None:
    """Redact a serial number entirely (prepared for future diagnostics fields)."""
    if not value:
        return value
    return REDACTED_SERIAL_NUMBER
