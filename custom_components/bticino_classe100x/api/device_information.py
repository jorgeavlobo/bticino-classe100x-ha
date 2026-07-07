"""Device information helpers for BTicino CLASSE100X."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import time

from .ssh_client import (
    BticinoCommandFailedError,
    BticinoConnectionConfig,
    BticinoSshClient,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class BticinoDeviceInformation:
    """Cached information about the BTicino CLASSE100X device."""

    hostname: str | None = None
    firmware_version: str | None = None
    os_release: str | None = None
    kernel: str | None = None
    uptime: str | None = None
    mac_address: str | None = None
    ssh_latency_ms: int | None = None
    openwebnet_latency_ms: int | None = None


class BticinoDeviceInformationClient:
    """Client used to collect device information through SSH."""

    def __init__(self, connection_config: BticinoConnectionConfig) -> None:
        """Initialize the device information client."""
        self._ssh_client = BticinoSshClient(connection_config)

    def collect(self) -> BticinoDeviceInformation:
        """Collect device information from the CLASSE100X using one SSH call."""
        start_time = time.monotonic()

        output = self._execute_linux_command(
            "echo '__BTICINO_HOSTNAME__'; "
            "hostname; "
            "echo '__BTICINO_FIRMWARE_VERSION__'; "
            "cat /etc/version 2>/dev/null; "
            "echo '__BTICINO_OS_RELEASE__'; "
            "if [ -f /etc/os-release ]; then cat /etc/os-release; fi; "
            "if [ -f /etc/issue ]; then cat /etc/issue; fi; "
            "echo '__BTICINO_KERNEL__'; "
            "uname -a; "
            "echo '__BTICINO_UPTIME__'; "
            "uptime; "
            "echo '__BTICINO_MAC_ADDRESSES__'; "
            "for i in /sys/class/net/*/address; do echo $i=$(cat $i); done"
        )

        latency_ms = round((time.monotonic() - start_time) * 1000)

        sections = self._parse_sections(output)

        return BticinoDeviceInformation(
            hostname=self._clean_output(sections.get("hostname")),
            firmware_version=self._clean_output(sections.get("firmware_version")),
            os_release=self._normalize_os_release(sections.get("os_release")),
            kernel=self._clean_output(sections.get("kernel")),
            uptime=self._clean_output(sections.get("uptime")),
            mac_address=self._parse_mac_address(sections.get("mac_addresses")),
            ssh_latency_ms=latency_ms,
        )

    def _execute_linux_command(self, command: str) -> str | None:
        """Execute a Linux command on the CLASSE100X through SSH."""
        try:
            result = self._ssh_client.run(command)
        except BticinoCommandFailedError as exc:
            _LOGGER.warning(
                "Failed to collect BTicino device information using command '%s': %s",
                command,
                exc,
            )
            return None

        return self._clean_output(result.stdout)

    @staticmethod
    def _parse_sections(output: str | None) -> dict[str, str]:
        """Parse command output separated by internal markers."""
        if not output:
            return {}

        marker_map = {
            "__BTICINO_HOSTNAME__": "hostname",
            "__BTICINO_FIRMWARE_VERSION__": "firmware_version",
            "__BTICINO_OS_RELEASE__": "os_release",
            "__BTICINO_KERNEL__": "kernel",
            "__BTICINO_UPTIME__": "uptime",
            "__BTICINO_MAC_ADDRESSES__": "mac_addresses",
        }

        sections: dict[str, list[str]] = {}
        current_key: str | None = None

        for line in output.splitlines():
            stripped_line = line.strip()

            if stripped_line in marker_map:
                current_key = marker_map[stripped_line]
                sections[current_key] = []
                continue

            if current_key is not None:
                sections[current_key].append(line)

        return {
            key: "\n".join(lines).strip()
            for key, lines in sections.items()
            if lines
        }

    @staticmethod
    def _normalize_os_release(raw_output: str | None) -> str | None:
        """Return a clean operating system release name."""
        if not raw_output:
            return None

        if "Poky (Yocto Project Reference Distro) 2.5.3" in raw_output:
            return "Yocto Poky 2.5.3"

        if "Poky (Yocto Project Reference Distro) 2.5.1" in raw_output:
            return "Yocto Poky 2.5.1"

        for line in raw_output.splitlines():
            cleaned_line = line.strip()

            if not cleaned_line:
                continue

            if cleaned_line.startswith("+") or cleaned_line.startswith("|"):
                continue

            if "Poky" in cleaned_line:
                return cleaned_line.replace("\\n \\l", "").strip()

        return None

    @staticmethod
    def _parse_mac_address(output: str | None) -> str | None:
        """Return the preferred non-loopback MAC address."""
        if not output:
            return None

        interface_macs: dict[str, str] = {}

        for line in output.splitlines():
            match = re.match(
                r"/sys/class/net/(?P<interface>[^/]+)/address=(?P<mac>([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})",
                line.strip(),
            )

            if not match:
                continue

            interface = match.group("interface")
            mac_address = match.group("mac").lower()

            if mac_address == "00:00:00:00:00:00":
                continue

            interface_macs[interface] = mac_address

        for preferred_interface in ("wlan0", "eth0", "end0", "usb0"):
            if preferred_interface in interface_macs:
                return interface_macs[preferred_interface]

        if interface_macs:
            return next(iter(interface_macs.values()))

        return None

    @staticmethod
    def _clean_output(value: str | None) -> str | None:
        """Normalize command output."""
        if value is None:
            return None

        cleaned = value.strip()

        if not cleaned:
            return None

        return cleaned
