# BTicino CLASSE100X Diagnostics Tools

This folder contains read-only diagnostic tools for the BTicino CLASSE100X Home Assistant integration.

The main tool is:

    health_check.py

It checks the local Home Assistant installation for common BTicino-related problems.

## Usage inside Home Assistant

    python3 /config/tools/diagnostics/health_check.py --config /config

## Usage against an offline Home Assistant backup

    python tools/diagnostics/health_check.py --config C:\Path\To\HomeAssistant\Config

## Markdown output

    python tools/diagnostics/health_check.py --config /config --markdown

## Automatic fixes

The --fix flag is reserved for the future.

At the moment, automatic fixes are not implemented.