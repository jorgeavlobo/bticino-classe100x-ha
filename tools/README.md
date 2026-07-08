# BTicino CLASSE100X Tools

This folder contains maintenance and diagnostic tools for the BTicino CLASSE100X
Home Assistant integration.

These tools are intended for developers and advanced users.

## Important

Always stop Home Assistant Core before modifying files inside `/config/.storage`:

1. Stop Home Assistant Core

       ha core stop

2. Run the desired tool

3. Start Home Assistant Core

       ha core start

You can also run the tools against an **offline copy** of your configuration
(for example a restored backup) by pointing `--config` at a directory that
contains a `.storage` folder. This never touches your live instance.

## Common options

All tools accept:

| Option | Description |
|--------|-------------|
| `--config PATH` | Home Assistant config directory, or an offline copy containing `.storage` (default: `/config`). |
| `--verbose` | Print more detailed output. |

The cleanup tools additionally accept:

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be removed without modifying any file. |
| `--yes` | Do not ask for confirmation before modifying a file. |
| `--no-backup` | Do not create a backup before modifying a file (not recommended). |

## Cleanup tools

| Tool | Description |
|------|-------------|
| `clean/clean_everything.py` | Runs every BTicino cleanup tool. |
| `clean/clean_entity_registry.py` | Removes BTicino entities from `core.entity_registry`. |
| `clean/clean_restore_state.py` | Removes BTicino entries from `core.restore_state`. |
| `clean/clean_config_entries.py` | Removes BTicino (and BTicino-related HomeKit) config entries. |

Preview first, then apply:

    python3 tools/clean/clean_everything.py --config /config --dry-run
    python3 tools/clean/clean_everything.py --config /config

## Diagnostic tools

| Tool | Description |
|------|-------------|
| `diagnostics/find_bticino_references.py` | Lists BTicino references in the Home Assistant storage files, detected by structural identifiers (integration domain, entity platform, entity_id/unique_id prefix, config-entry domain and device identifiers) rather than generic words. HACS management entities (`update`/`switch`) and HACS's own bookkeeping files (`hacs.*`) are reported separately as informational. Backups are ignored. |

    python3 tools/diagnostics/find_bticino_references.py --config /config

See [Exit codes](#exit-codes) for how the outcome is reported.

## Safety

- By default each cleanup tool creates a timestamped backup (for example
  `core.entity_registry.backup_20260101_120000`) next to the file **before**
  modifying it. Use `--no-backup` only if you have your own backup.
- Cleanup tools ask for confirmation before writing. Run with `--yes` for
  non-interactive use. If stdin is not interactive and `--yes` is not given, the
  tool makes no changes.
- Use `--dry-run` to preview the exact number of entries that would be removed
  without changing anything.
- The tools validate that `--config` points to an existing directory and skip
  files that are missing or cannot be parsed instead of failing destructively.

## Exit codes

For scripting and CI the tools report their outcome via the process exit code:

- Cleanup tools (including `clean_everything.py`) exit `0` on success (updated,
  nothing to remove, dry run or a deliberate skip) and `1` if any file could not
  be read, backed up or written.
- `find_bticino_references.py` exits `0` when the storage was scanned in full
  and no **confirmed** references remain, `1` when confirmed references were
  found, and `2` when the scan could not be completed — the storage path is
  missing (for example a misconfigured `--config`) or one or more files could
  not be read. HACS-managed entities and HACS's own bookkeeping files are
  reported as informational only and never change the exit code.
