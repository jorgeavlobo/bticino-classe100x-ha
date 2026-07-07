# BTicino CLASSE100X Tools

This folder contains maintenance and diagnostic tools for the BTicino CLASSE100X Home Assistant integration.

These tools are intended for developers and advanced users.

------------------------------------------------------------
IMPORTANT
------------------------------------------------------------

Always stop Home Assistant Core before modifying files inside:

    /config/.storage

Recommended workflow:

1. Stop Home Assistant Core

    ha core stop

2. Execute the desired tool

3. Start Home Assistant Core

    ha core start

------------------------------------------------------------
AVAILABLE TOOLS
------------------------------------------------------------

Clean tools

    clean_everything.py

        Cleans every BTicino-related Home Assistant file.

    clean_entity_registry.py

        Cleans BTicino entities from core.entity_registry.

    clean_restore_state.py

        Cleans BTicino entries from core.restore_state.

    clean_config_entries.py

        Removes BTicino config entries.

------------------------------------------------------------

Diagnostic tools

    find_bticino_references.py

        Searches the Home Assistant configuration and storage files
        for BTicino references.

------------------------------------------------------------

SAFETY

Every cleanup tool automatically creates a timestamped backup
before modifying any Home Assistant file.

Always verify the backup exists before continuing.