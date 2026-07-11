# Dashboard

This page explains how to show short, dashboard-friendly names for the BTicino
CLASSE100X entities, why those names are **not** translated automatically, and
provides ready-to-use example dashboards in several languages.

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

## Why `has_entity_name = True` stays enabled

Keeping this enabled is the Home Assistant-native, compliant model. Disabling it
to force short names would regress the integration:

- it reduces Home Assistant compliance (the recommended naming model);
- it degrades the auto-generated **device page**, which relies on the
  device-name + entity-name split;
- it degrades **voice assistants**, which expect device-qualified names;
- it degrades **automatic naming** for areas and generated cards.

So the integration keeps entity names compliant and leaves the dashboard label
to you — the Home Assistant-native way, described next.

## Entity translations vs. dashboard names

These two things look similar but are handled in completely different places:

| Name type | Controlled by | Translated by Home Assistant? |
|---|---|---|
| **Entity name** (`translation_key`) | The integration, via the translation files | **Yes** — follows the Home Assistant UI language |
| **Dashboard card name** (`name:`) | You, in the dashboard YAML | **No** — the string is static |

The integration itself is fully localized through the Home Assistant translation
system: entity names, the config/options flow, diagnostics, sensor names,
buttons and binary sensors are all translated automatically to match the Home
Assistant UI language.

Dashboard YAML is different. When a card contains:

```yaml
name: Condominium Gate
```

that string is **static**. Home Assistant does not translate dashboard card
names — whatever you type is shown verbatim, regardless of the UI language.
That is why this page ships a separate example per language instead of a single
one: you copy the file that matches your installation's language.

## Naming strategy (recommended)

- Keep the integration's entity names **Home Assistant-compliant** — don't ask
  the integration to hardcode short names.
- Customize the **dashboard appearance** with the card `name:` override. This is
  the Home Assistant-native way and is fully non-destructive: it does not rename
  entities in the registry and does not affect automations, areas or voice
  assistants.
- **Avoid** renaming entities in the entity registry just to shorten a dashboard
  label. A registry rename changes the name **everywhere** in Home Assistant
  (device page, voice assistants, other dashboards), not only on the one card.

If you *do* prefer a global rename, you can still set it from **Settings →
Devices & Services → Entities → (entity) → Settings → Name**. It is intentionally
left to you rather than forced by the integration.

## Localized example dashboards

Each file below is a **complete** dashboard (it has both `title:` and `views:`)
with short, localized `name:` overrides already filled in, so every Tile card
reads e.g. `Condominium Gate` instead of `BTicino CLASSE100X Condominium Gate`.
Pick the one matching your Home Assistant language:

- 🇬🇧 English — [`examples/dashboard-en.yaml`](examples/dashboard-en.yaml)
- 🇵🇹 Português — [`examples/dashboard-pt.yaml`](examples/dashboard-pt.yaml)
- 🇫🇷 Français — [`examples/dashboard-fr.yaml`](examples/dashboard-fr.yaml)
- 🇮🇹 Italiano — [`examples/dashboard-it.yaml`](examples/dashboard-it.yaml)
- 🇩🇪 Deutsch — [`examples/dashboard-de.yaml`](examples/dashboard-de.yaml)

The card **names** are localized; the `entity:` IDs are identical in every file,
so the same dashboard works on any installation using the default entity IDs.

## Where to paste it

Home Assistant has two dashboard modes, and the example goes to a different place
in each:

### Storage dashboards (default, UI-managed)

These are edited through the **Raw configuration editor** (⋮ → *Edit dashboard*
→ ⋮ → *Raw configuration editor*):

- **New dashboard**: paste the whole file (it includes both `title:` and
  `views:`).
- **Existing dashboard**: paste only the list item under `views:` (the
  `- title: …` block and everything indented beneath it) into that dashboard's
  existing `views:` list.

### YAML dashboards (`configuration.yaml`)

If the dashboard is set to YAML mode (the Raw configuration editor is not
available for these), edit its referenced YAML file directly and add the same
content there.

## Notes

- Adjust the `entity:` IDs if you renamed the entities or use a different device
  slug.
- Some device-information sensors (firmware version, firmware build, installed
  package, OS release, uptime, hostname, MAC address) are disabled by default.
  Enable them from the device page if you want to add them to a card.
- These examples use the built-in Tile and Entities cards so they work with no
  extra installation. The same naming strategy applies to any layout (Sections,
  Mushroom, Picture Elements, mobile/wall-tablet views); additional example
  layouts can be added under `examples/` using the same localized names.
