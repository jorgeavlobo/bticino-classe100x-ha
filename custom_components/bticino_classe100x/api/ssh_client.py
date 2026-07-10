"""SSH client for BTicino CLASSE100X."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import subprocess

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class BticinoConnectionConfig:
    """Connection settings for the BTicino CLASSE100X device."""

    host: str
    username: str
    auth_method: str = "ssh_key"
    ssh_key_path: str | None = None
    password: str | None = None
    command_timeout: int = 10
    release_delay: float = 1.0


class BticinoOpenWebNetError(Exception):
    """Base exception for BTicino CLASSE100X communication errors."""


class BticinoSshKeyNotFoundError(BticinoOpenWebNetError):
    """Raised when the configured SSH private key does not exist."""


class BticinoAuthenticationMethodError(BticinoOpenWebNetError):
    """Raised when the authentication method is invalid or unsupported."""


class BticinoCommandFailedError(BticinoOpenWebNetError):
    """Raised when an SSH command fails."""


class BticinoSshClient:
    """Small SSH command runner for the CLASSE100X."""

    def __init__(self, config: BticinoConnectionConfig) -> None:
        """Initialize the SSH client."""
        self.config = config

    def run(self, remote_command: str) -> subprocess.CompletedProcess[str]:
        """Run a command inside the CLASSE100X through SSH."""
        command = self._build_command(remote_command)

        _LOGGER.debug(
            "Running SSH command on BTicino CLASSE100X host=%s command=%s",
            self.config.host,
            remote_command,
        )

        try:
            result = subprocess.run(
                command,
                check=True,
                timeout=self.config.command_timeout,
                capture_output=True,
                # Decode as text but tolerate non-UTF-8 bytes: device files such
                # as /home/bticino/sp/dbfiles_ws.xml are ISO-8859-1 and may carry
                # bytes that are invalid UTF-8. With the default strict policy a
                # single such byte raises UnicodeDecodeError from inside
                # subprocess.run and aborts the entire collection; "replace" keeps
                # the rest of the output (hostname, MAC, the ASCII XML values we
                # parse, ...) intact.
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            _LOGGER.debug(
                "SSH command succeeded on BTicino CLASSE100X host=%s stdout=%s stderr=%s",
                self.config.host,
                result.stdout,
                result.stderr,
            )

            return result

        except subprocess.TimeoutExpired as exc:
            _LOGGER.error(
                "SSH command timed out on BTicino CLASSE100X host=%s timeout=%s command=%s",
                self.config.host,
                self.config.command_timeout,
                remote_command,
            )
            raise BticinoCommandFailedError("SSH command timed out") from exc

        except subprocess.CalledProcessError as exc:
            _LOGGER.error(
                "SSH command failed on BTicino CLASSE100X host=%s command=%s stdout=%s stderr=%s",
                self.config.host,
                remote_command,
                exc.stdout,
                exc.stderr,
            )
            raise BticinoCommandFailedError(
                f"SSH command failed. stdout={exc.stdout} stderr={exc.stderr}"
            ) from exc

    def _build_command(self, remote_command: str) -> list[str]:
        """Build the OpenSSH command line."""
        base_command = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "HostKeyAlgorithms=+ssh-rsa",
            "-o",
            "PubkeyAcceptedAlgorithms=+ssh-rsa",
            "-o",
            "MACs=hmac-sha1",
            "-o",
            "ConnectTimeout=5",
        ]

        if self.config.auth_method == "ssh_key":
            if not self.config.ssh_key_path:
                raise BticinoAuthenticationMethodError("SSH key path is required")

            if not os.path.isfile(self.config.ssh_key_path):
                raise BticinoSshKeyNotFoundError(
                    f"SSH key not found: {self.config.ssh_key_path}"
                )

            return [
                *base_command,
                "-o",
                "BatchMode=yes",
                "-i",
                self.config.ssh_key_path,
                f"{self.config.username}@{self.config.host}",
                remote_command,
            ]

        if self.config.auth_method == "password":
            raise BticinoAuthenticationMethodError(
                "Password authentication is not implemented yet"
            )

        raise BticinoAuthenticationMethodError(
            f"Unsupported authentication method: {self.config.auth_method}"
        )
