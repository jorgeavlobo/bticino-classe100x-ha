# Dashboard

This page explains how to show short, dashboard-friendly names for the BTicino
CLASSE100X entities, and provides an example dashboard.

## Why entity names look long

The integration enables modern Home Assistant entity naming
(`has_entity_name = True`). With this model an entity's friendly name is built
from the **device name** plus the **entity name**, for example:

```text
BTicino CLASSE100X Condominium Gate
```

This is the correct and recommended Home Assistant behaviour: it keeps names
unambiguous across multiple devices and works well with areas, voice assistants
and the automatically generated device page. It is **not** a bug.

On a Tile card placed on a general dashboard, Home Assistant shows this full
name, which can feel long. (On the device's own auto-generated page Home
Assistant already drops the device prefix, so the short name is shown there
without any extra configuration.)

## Decision

- `has_entity_name = True` **stays enabled** — it is the Home Assistant-native,
  compliant model, and changing it would regress the entity naming.
- The integration does **not** hardcode short names or change any `unique_id`.
- To get short names on a dashboard, override the card `name` in the dashboard
  YAML. This is the Home Assistant-native way and is fully non-destructive: it
  does not rename entities in the registry and does not affect automations,
  areas or voice assistants.

If you prefer, you can instead override an entity's friendly name from
**Settings → Devices & Services → Entities → (entity) → Settings → Name**. That
is a per-user choice and is intentionally left to you rather than forced by the
integration.

## Example dashboard

The snippet below is a complete dashboard (it has both `title:` and `views:`).
Every Tile card uses a short `name` override, so the cards read
`Condominium Gate` instead of `BTicino CLASSE100X Condominium Gate`.

- **As a new dashboard**: create a dashboard, switch it to **YAML mode** (⋮ →
  *Edit dashboard* → ⋮ → *Raw configuration editor*) and paste the whole
  snippet.
- **As a view on an existing dashboard**: paste only the list item under
  `views:` (the `- title: Intercom` block and everything indented beneath it)
  into that dashboard's existing `views:` list.

```yaml
title: BTicino CLASSE100X
views:
  - title: Intercom
    cards:
      - type: grid
        columns: 2
        square: false
        cards:
          - type: tile
            entity: button.bticino_classe100x_condominium_gate
            name: Condominium Gate
            icon: mdi:gate
          - type: tile
            entity: button.bticino_classe100x_pedestrian_door
            name: Pedestrian Door
            icon: mdi:door
          - type: tile
            entity: binary_sensor.bticino_classe100x_connection_status
            name: Connection
          - type: tile
            entity: sensor.bticino_classe100x_health_status
            name: Health

      - type: entities
        title: Diagnostics
        entities:
          - entity: button.bticino_classe100x_test_ssh_connection
            name: Test connection
          - entity: sensor.bticino_classe100x_ssh_latency
            name: SSH latency
          - entity: sensor.bticino_classe100x_openwebnet_latency
            name: OpenWebNet latency
          - entity: sensor.bticino_classe100x_last_test_result
            name: Last test result
          - entity: sensor.bticino_classe100x_last_successful_test
            name: Last successful test
          - entity: sensor.bticino_classe100x_last_failed_test
            name: Last failed test
```

Notes:

- Adjust the `entity` IDs if you renamed the entities or use a different device
  slug.
- Some device-information sensors (firmware version, OS release, uptime,
  hostname, MAC address) are disabled by default. Enable them from the device
  page if you want to add them to a card.
