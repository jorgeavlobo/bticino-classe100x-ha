# BTicino CLASSE100X Diagnostics Tools

This folder contains read-only diagnostic tools for the BTicino CLASSE100X Home Assistant integration.

The main tool is:

    health_check.py

It checks the local Home Assistant installation for common BTicino-related problems.

## Usage inside Home Assistant

    python3 /config/dev/bticino-classe100x-ha/tools/diagnostics/health_check.py --config /config

## Usage against an offline Home Assistant backup

    python tools/diagnostics/health_check.py --config C:\Path\To\HomeAssistant\Config

## List available checks

    python tools/diagnostics/health_check.py --list

## Run one check only

    python tools/diagnostics/health_check.py entity_registry --config /config

## Run multiple checks

    python tools/diagnostics/health_check.py entity_registry restore_state --config /config

## Markdown output

    python tools/diagnostics/health_check.py --config /config --markdown

## GitHub issue friendly output

    python tools/diagnostics/health_check.py --config /config --github

## JSON output

    python tools/diagnostics/health_check.py --config /config --json

## Performance timing

    python tools/diagnostics/health_check.py --config /config --performance

## Automatic fixes

The --fix flag is reserved for the future.

At the moment, automatic fixes are not implemented.