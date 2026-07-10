# Translations

The integration ships user-visible strings for several languages. Home Assistant
loads them at runtime from `custom_components/bticino_classe100x/translations/<language>.json`.

Currently supported:

| Locale | File |
|--------|------|
| English | `en.json` |
| Portuguese | `pt.json` |
| French | `fr.json` |
| German | `de.json` |
| Italian | `it.json` |

## Maintenance policy

English is the authoritative source. To keep every language exposing exactly the
same functionality, structure, placeholders and capabilities:

1. **English is canonical.** Every new translatable string is added to
   `en.json` first.
2. **No key drifts.** Other languages differ only in their *values* — never in
   keys, hierarchy, value types or `{placeholder}` tokens.
3. **Every language is updated before a release.** Missing translations must
   never silently accumulate.
4. **The validator must pass before every merge.** It runs in CI and is the
   permanent safeguard against forgotten or inconsistent translations.

## Validating

The validator compares every
`custom_components/bticino_classe100x/translations/*.json` against the canonical
`en.json` and reports missing keys, unexpected keys, type mismatches (object vs
string) and `{placeholder}` mismatches. Key-order differences are reported as
informational notes only. It never modifies the files.

```bash
python3 tools/translations/validate_translations.py
```

Exit code `0` means every language matches `en.json`; `1` means a required
locale is missing, a file is invalid JSON, or a language drifts from the source.
The self-test for the validator's own logic runs with:

```bash
python3 scripts/validate_translations.py
```

Both run automatically in the **Quality Checks** GitHub Actions workflow.

## Adding a new language

All translation files live under `custom_components/bticino_classe100x/translations/`.

1. Copy `custom_components/bticino_classe100x/translations/en.json` to
   `custom_components/bticino_classe100x/translations/<language>.json`.
2. Translate only the *values*. Never add, remove or rename keys.
3. Preserve every `{placeholder}` token exactly.
4. Keep the JSON hierarchy and (ideally) the key order identical to `en.json`.
5. Add the new file to `REQUIRED_LOCALES` in
   [`tools/shared/translations.py`](../tools/shared/translations.py) — the single
   source of truth shared by the validator and the diagnostics health check.
6. Validate:
   ```bash
   python3 -m json.tool custom_components/bticino_classe100x/translations/<language>.json
   python3 tools/translations/validate_translations.py
   ```
7. Verify in Home Assistant: Config Flow, Options Flow, entity names, enum
   sensor states and diagnostics are all translated, with no missing-translation
   warnings in the log.

## Terminology

Use terminology consistent with Home Assistant, BTicino documentation and
established Home Assistant community usage. Prefer an accepted Home Assistant
term over a literal machine translation (for example *Connection*, *Firmware*,
*Hostname*, *MAC Address*, *SSH Latency*, *Condominium Gate*, *Pedestrian Door*).
