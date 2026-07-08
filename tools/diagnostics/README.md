# BTicino CLASSE100X Diagnostics Tools

This folder contains read-only diagnostic tools for the BTicino CLASSE100X Home Assistant integration.

The main tool is:

    health_check.py

It checks the local Home Assistant installation for common BTicino-related problems.

## What the entity checks detect

The `entity_registry` check compares the BTicino entities in
`core.entity_registry` against the expected entity set defined in
`checks/expected_entities.py` (kept in sync with the integration's entity
descriptions). It reports:

- obsolete entities with deprecated unique IDs or legacy `entity_id` naming,
- incomplete migrations (an old and a new unique ID present at the same time),
- stale BTicino entries left in `deleted_entities`,
- missing expected entities and unexpected extra BTicino entities,
- duplicated entity IDs / unique IDs and orphaned or unlinked entities.

Each finding includes the exact entity ID, unique ID, reason and suggested
cleanup action.

The `metadata_consistency` check compares the metadata Home Assistant persisted
for each present entity (`translation_key`, `entity_category`,
`original_device_class`, `original_icon`, `unit_of_measurement`, `state_class`
and enum `options`) against the expected values. Mismatches are reported as
warnings, since they usually mean the registry is stale (a reload or restart is
needed) rather than that the integration is broken.

Because these tools run against an offline `.storage` copy and cannot import the
integration, the expected values live in `checks/expected_entities.py` and must
be updated whenever the entity descriptions change. The
`scripts/validate_health_check.py` self-test (run in CI) locks in the detection
logic.

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