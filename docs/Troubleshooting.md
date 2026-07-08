# Troubleshooting

## Translated sensor states show in English (or as the raw value)

**Symptom.** Enum sensors such as *Health Status*, *Last Test Result* and
*Last Failed Status* display the English label (for example `Healthy`,
`Success`, `Never`) even though Home Assistant is set to another language and
the integration ships the translations.

**This is not an integration bug.** The integration exposes each enum state as a
lowercase slug (`healthy`, `slow`, `offline`, `success`, `failed`, `never`) and
provides the matching labels under
`entity.sensor.<key>.state.<slug>` in every language file
(`translations/en.json`, `translations/pt.json`, `translations/fr.json`,
`translations/de.json`, `translations/it.json`), which is the structure Home
Assistant's translation loader reads at runtime.

CI does not exercise the Home Assistant runtime; instead
[`tools/translations/validate_translations.py`](../tools/translations/validate_translations.py)
checks translation *consistency* — that every language file exposes exactly the
same keys, structure and placeholders as `translations/en.json` — so no language
can silently omit a state slug. See [Translations.md](Translations.md) for the
full policy.

Two things can make the correct labels *appear* untranslated in the UI:

1. **Home Assistant did not fully reload its translations.** Translations are
   read once when the integration is loaded and then cached. **Reloading the
   config entry does not reload translation files** — only a full **Home
   Assistant Core restart** does.

2. **The browser cached the old translation bundle.** The frontend downloads and
   caches translation bundles. After a Core restart, force a hard refresh so the
   browser fetches the new bundle:

   - Windows / Linux: `Ctrl` + `F5`
   - macOS: `Cmd` + `Shift` + `R`

   If it still shows the old value, clear the site data for your Home Assistant
   URL, or try a private/incognito window.

### Why English looks "stuck"

When no translation is applied, the frontend falls back to prettifying the raw
slug — it replaces underscores with spaces and capitalises each word, so
`healthy` becomes `Healthy` regardless of the selected language. Because that
fallback happens to match the English labels, an untranslated state looks like
English in every language. Seeing the *prettified slug* rather than, for
example, `Saudável` (Portuguese) is the tell-tale sign that the translation
bundle is stale, not missing.

### Verifying the translations are present

Run the validator from the repository root:

```console
python3 scripts/validate_translations.py
```

It flattens each language file the same way Home Assistant does and confirms
every language exposes exactly the keys declared in `translations/en.json`. A
`0` exit code means the translations are complete and consistent.
