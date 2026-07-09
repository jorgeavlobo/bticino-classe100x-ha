# BTicino CLASSE100X Home Assistant Integration

Custom Home Assistant integration for the BTicino CLASSE100X video intercom.

This integration uses SSH to access the CLASSE100X Linux system and OpenWebNet commands to trigger supported actions.

This project is not affiliated with BTicino or Legrand.

## Features

- Open condominium gate
- Open pedestrian door
- Manual SSH/OpenWebNet connection test
- Connection status binary sensor
- Health status sensor
- SSH latency sensor
- OpenWebNet latency sensor
- Firmware version sensor
- OS release sensor
- Hostname sensor
- MAC address sensor
- Uptime sensor
- Last test result sensor
- Last successful test timestamp sensor
- Last failed test timestamp sensor
- Last failed status sensor
- Diagnostics support
- Config flow
- Options flow

## Supported devices

Tested with:

- BTicino CLASSE100X

## Requirements

- Home Assistant
- SSH access to the CLASSE100X device
- SSH key authentication
- OpenWebNet local command access on the device

## Installation with HACS

1. Open HACS.
2. Open the three-dot menu.
3. Select Custom repositories.
4. Add this repository URL.
5. Select category Integration.
6. Install BTicino CLASSE100X.
7. Restart Home Assistant.
8. Add the integration from Settings > Devices & Services.

## Manual installation

Copy this folder:

    custom_components/bticino_classe100x

to:

    /config/custom_components/bticino_classe100x

Then restart Home Assistant.

## Configuration

The integration is configured from the Home Assistant UI.

Required fields:

- Host/IP address
- Username
- SSH key path
- Command timeout
- Release delay

Default username:

    root2

Default SSH key path:

    /config/ssh/bticinokey

## Entities

### Buttons

- Condominium Gate
- Pedestrian Door
- Test SSH Connection

### Binary sensors

- Connection Status

### Sensors

- Health Status
- SSH Latency
- OpenWebNet Latency
- Firmware Version
- OS Release
- Uptime
- Hostname
- MAC Address
- Last Test Result
- Last Successful Test
- Last Failed Test
- Last Failed Status

## Dashboard

Home Assistant builds entity names from the device name plus the entity name
(for example `BTicino CLASSE100X Condominium Gate`), which can look long on Tile
cards. To show short, dashboard-friendly names, override the card `name` in your
dashboard YAML.

See [docs/Dashboard.md](docs/Dashboard.md) for the rationale and a ready-to-use
example dashboard.

## Translations

User-visible strings are available in English, Portuguese, French, German and
Italian. English is the authoritative source; a validator in CI keeps every
language in sync. See [docs/Translations.md](docs/Translations.md) for the
maintenance policy and how to add a new language.

## Diagnostics

The downloadable diagnostics file is designed to be safe to attach to public
issues: installation-specific values (host, username, hostname, MAC, the kernel
string and the last-error text) are redacted through a central sanitization
layer, and passwords and SSH keys are never included. See
[docs/Diagnostics.md](docs/Diagnostics.md) for the per-field privacy policy.

## HomeKit

The recommended HomeKit setup is a YAML-defined HomeKit Bridge with explicit entity inclusion.

Example:

    homekit:
      - name: Home Assistant Bridge
        port: 21064
        filter:
          include_entities:
            - button.bticino_classe100x_condominium_gate
            - button.bticino_classe100x_pedestrian_door

HomeKit pairing must be done from the same local network. Pairing over VPN may fail because HomeKit relies on Bonjour/mDNS discovery.

## Roadmap

- Improved health attributes
- Better uptime formatting
- Entity categories
- Dashboard screenshots
- Doorbell detection
- Incoming call detection
- Camera/RTSP investigation
- Snapshot support
- Two-way audio investigation

## License

MIT License.
