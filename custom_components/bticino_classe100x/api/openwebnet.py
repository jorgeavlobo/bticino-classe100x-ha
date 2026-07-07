"""OpenWebNet client for BTicino CLASSE100X."""

from __future__ import annotations

import logging
import time

from .ssh_client import (
    BticinoAuthenticationMethodError,
    BticinoCommandFailedError,
    BticinoConnectionConfig,
    BticinoOpenWebNetError,
    BticinoSshClient,
    BticinoSshKeyNotFoundError,
)

_LOGGER = logging.getLogger(__name__)

# OpenWebNet is reached on the device itself through a local TCP socket, so the
# commands are piped to netcat targeting the loopback gateway ("0") on the
# standard OpenWebNet port.
OPENWEBNET_HOST = "0"
OPENWEBNET_PORT = 30006
OPENWEBNET_STATUS_REQUEST = "*#*1##"


class BticinoOpenWebNetClient:
    """Client used to send OpenWebNet commands through SSH."""

    def __init__(self, config: BticinoConnectionConfig) -> None:
        """Initialize the OpenWebNet client."""
        self.config = config
        self._ssh_client = BticinoSshClient(config)

    def test_connection(self) -> bool:
        """Test SSH access and local OpenWebNet socket availability."""
        result = self._ssh_client.run(
            f"echo '{OPENWEBNET_STATUS_REQUEST}' | nc {OPENWEBNET_HOST} {OPENWEBNET_PORT}"
        )

        if result.stdout:
            _LOGGER.info("Connected to BTicino CLASSE100X at %s", self.config.host)
            return True

        _LOGGER.warning(
            "OpenWebNet test command returned no output. host=%s stderr=%s",
            self.config.host,
            result.stderr,
        )
        return False

    def send_sequence(self, press_command: str, release_command: str, name: str) -> None:
        """Send a press/release OpenWebNet command sequence."""
        _LOGGER.info("Opening %s through BTicino CLASSE100X", name)

        remote_command = (
            f"echo '{press_command}' | nc {OPENWEBNET_HOST} {OPENWEBNET_PORT}; "
            f"sleep {self.config.release_delay}; "
            f"echo '{release_command}' | nc {OPENWEBNET_HOST} {OPENWEBNET_PORT}"
        )

        result = self._ssh_client.run(remote_command)

        _LOGGER.debug(
            "BTicino command completed. name=%s stdout=%s stderr=%s",
            name,
            result.stdout,
            result.stderr,
        )

    def measure_latency_ms(self) -> int | None:
        """Measure OpenWebNet test command latency in milliseconds."""
        start_time = time.monotonic()

        if not self.test_connection():
            return None

        return round((time.monotonic() - start_time) * 1000)


__all__ = [
    "BticinoAuthenticationMethodError",
    "BticinoCommandFailedError",
    "BticinoConnectionConfig",
    "BticinoOpenWebNetClient",
    "BticinoOpenWebNetError",
    "BticinoSshKeyNotFoundError",
]
