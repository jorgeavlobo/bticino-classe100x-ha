"""Expected BTicino CLASSE100X entity specification.

This is the single source of truth the diagnostics use to decide whether the
Home Assistant registry matches the current integration. It mirrors the entity
descriptions in ``custom_components/bticino_classe100x/entities`` — the tools run
against an offline ``.storage`` copy and cannot import the integration (which
requires Home Assistant), so the expectations are declared here and must be kept
in sync with the entity descriptions.

Each :class:`ExpectedEntity` captures the metadata Home Assistant persists in
``core.entity_registry`` for that entity, so both the entity-registry check (are
the right entities present, and are any obsolete ones left behind?) and the
metadata-consistency check (does the persisted metadata still match the code?)
can be derived from the same list.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from diagnostics.shared.entities import DOMAIN
from shared.matching import LEGACY_OBJECT_ID_FRAGMENTS


@dataclass(frozen=True, slots=True)
class ExpectedEntity:
    """The metadata expected for a single BTicino entity.

    ``key`` is the entity description key (used for the default object id and the
    translation key). ``unique_key`` is the suffix of the unique id and usually
    equals ``key`` — the connection binary sensor is the exception, keeping the
    legacy ``connection`` suffix while its key is ``connection_status``.
    """

    domain: str
    key: str
    unique_key: str
    entity_category: str | None = None
    original_device_class: str | None = None
    original_icon: str | None = None
    unit_of_measurement: str | None = None
    state_class: str | None = None
    options: tuple[str, ...] | None = None
    # Declared to mirror the entity descriptions but intentionally NOT compared
    # for drift: Home Assistant persists it as ``disabled_by``, which a user can
    # legitimately toggle from the UI, so comparing it would raise false
    # positives whenever someone enabled or disabled one of these entities.
    entity_registry_enabled_default: bool = True
    # Deprecated ``unique_key`` values this entity was migrated away from. If a
    # registry entry still uses one of these suffixes the migration is stale.
    deprecated_unique_keys: tuple[str, ...] = field(default_factory=tuple)

    @property
    def translation_key(self) -> str:
        """Return the expected translation key."""
        return self.key

    @property
    def default_object_id(self) -> str:
        """Return the default object id (``suggested_object_id``)."""
        return f"{DOMAIN}_{self.key}"

    @property
    def default_entity_id(self) -> str:
        """Return the default entity id using the default object id."""
        return f"{self.domain}.{self.default_object_id}"

    def unique_id(self, host: str) -> str:
        """Return the full expected unique id for a given host."""
        return f"{DOMAIN}_{host}_{self.unique_key}"


# Kept in sync with the entity descriptions in
# custom_components/bticino_classe100x/entities/{button,binary_sensor,sensor}.py.
EXPECTED_ENTITIES: tuple[ExpectedEntity, ...] = (
    # Buttons
    ExpectedEntity(
        domain="button",
        key="condominium_gate",
        unique_key="condominium_gate",
        original_icon="mdi:gate",
    ),
    ExpectedEntity(
        domain="button",
        key="pedestrian_door",
        unique_key="pedestrian_door",
        original_icon="mdi:door",
    ),
    ExpectedEntity(
        domain="button",
        key="test_ssh_connection",
        unique_key="test_ssh_connection",
        entity_category="diagnostic",
        original_icon="mdi:lan-check",
    ),
    # Binary sensors
    ExpectedEntity(
        domain="binary_sensor",
        key="connection_status",
        unique_key="connection",
        entity_category="diagnostic",
        original_device_class="connectivity",
        original_icon="mdi:connection",
        deprecated_unique_keys=("connection_status",),
    ),
    # Sensors
    ExpectedEntity(
        domain="sensor",
        key="health_status",
        unique_key="health_status",
        entity_category=None,
        original_device_class="enum",
        original_icon="mdi:heart-pulse",
        options=("healthy", "slow", "offline"),
    ),
    ExpectedEntity(
        domain="sensor",
        key="ssh_latency",
        unique_key="ssh_latency",
        entity_category="diagnostic",
        original_device_class="duration",
        original_icon="mdi:lan",
        unit_of_measurement="ms",
        state_class="measurement",
    ),
    ExpectedEntity(
        domain="sensor",
        key="openwebnet_latency",
        unique_key="openwebnet_latency",
        entity_category="diagnostic",
        original_device_class="duration",
        original_icon="mdi:connection",
        unit_of_measurement="ms",
        state_class="measurement",
    ),
    ExpectedEntity(
        domain="sensor",
        key="firmware_version",
        unique_key="firmware_version",
        entity_category="diagnostic",
        original_icon="mdi:chip",
        entity_registry_enabled_default=False,
    ),
    ExpectedEntity(
        domain="sensor",
        key="os_release",
        unique_key="os_release",
        entity_category="diagnostic",
        original_icon="mdi:linux",
        entity_registry_enabled_default=False,
    ),
    ExpectedEntity(
        domain="sensor",
        key="uptime",
        unique_key="uptime",
        entity_category="diagnostic",
        original_icon="mdi:clock-outline",
        entity_registry_enabled_default=False,
    ),
    ExpectedEntity(
        domain="sensor",
        key="hostname",
        unique_key="hostname",
        entity_category="diagnostic",
        original_icon="mdi:server",
        entity_registry_enabled_default=False,
    ),
    ExpectedEntity(
        domain="sensor",
        key="mac_address",
        unique_key="mac_address",
        entity_category="diagnostic",
        original_icon="mdi:network-outline",
        entity_registry_enabled_default=False,
    ),
    ExpectedEntity(
        domain="sensor",
        key="last_test_result",
        unique_key="last_test_result",
        entity_category="diagnostic",
        original_device_class="enum",
        original_icon="mdi:check-network-outline",
        options=("success", "failed"),
    ),
    ExpectedEntity(
        domain="sensor",
        key="last_successful_test",
        unique_key="last_successful_test",
        entity_category="diagnostic",
        original_device_class="timestamp",
        original_icon="mdi:check-circle-outline",
    ),
    ExpectedEntity(
        domain="sensor",
        key="last_failed_test_status",
        unique_key="last_failed_test_status",
        entity_category="diagnostic",
        original_device_class="enum",
        original_icon="mdi:alert-circle-outline",
        options=("never", "failed"),
    ),
    ExpectedEntity(
        domain="sensor",
        key="last_failed_test",
        unique_key="last_failed_test",
        entity_category="diagnostic",
        original_device_class="timestamp",
        original_icon="mdi:alert-circle-outline",
    ),
)


# The legacy room-prefixed object-id forms (``<room>_bticino_classe100x_<key>``)
# are defined once in ``shared.matching`` and re-exported here under the name the
# entity-registry check already imports, so the cleanup tools, the reference scan
# and the health check share a single source of truth and never drift.
LEGACY_ENTITY_ID_FRAGMENTS = LEGACY_OBJECT_ID_FRAGMENTS
