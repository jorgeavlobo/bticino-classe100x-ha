# Diagnostics

Home Assistant can download a diagnostics file for the BTicino CLASSE100X
integration (**Settings → Devices & Services → BTicino CLASSE100X → ⋮ →
Download diagnostics**). It is designed to be **safe to attach to public GitHub
issues**: every installation-specific value is redacted, while enough detail is
kept to debug effectively.

## Sanitization architecture

Diagnostics never redact values inline. All redaction goes through a single,
dependency-free module,
[`diagnostics/sanitize.py`](../custom_components/bticino_classe100x/diagnostics/sanitize.py),
so the privacy policy has one testable home and future fields (serial numbers,
UUIDs, …) reuse it instead of re-implementing redaction. Its behaviour is
verified by [`scripts/validate_sanitize.py`](../scripts/validate_sanitize.py),
which runs in the **Quality Checks** CI workflow.

## Privacy policy per field

| Field | Policy | Notes |
|-------|--------|-------|
| Integration / Home Assistant version | Visible | Not identifying. |
| Entity count, platforms | Visible | Not identifying. |
| Entry title / id / version / source | Visible | The entry id is a Home-Assistant-internal random id, not device or network data. |
| Auth method, `*_configured` / `*_exists` booleans | Visible | Booleans and an enum only. |
| Command timeout, release delay | Visible | User settings, not identifying. |
| Connection / coordinator status, test times & results | Visible | Not identifying. |
| Firmware version, firmware build, model, installed package, OS release, uptime | Visible | Device software info, not identifying. |
| SSH / OpenWebNet latency | Visible | Not identifying. |
| **MAC address** | Partially redacted | Vendor OUI kept; device half masked (`00:03:50:**:**:**`). |
| **Hostname** | Partially redacted | Model prefix kept; MAC + UUID tail dropped (`C1X-<redacted>`). |
| **Kernel** (`uname -a`) | Partially redacted | Version and architecture kept; embedded node name dropped. |
| **Last error** | Partially redacted | SSH key path, host, hostname and username are replaced with `<redacted-…>` placeholders; the failure message is kept. |
| **Host** | Fully redacted | Only the address family is kept (`<redacted-ipv4-address>`). |
| **Username** | Fully redacted | `<redacted-username>`. |
| Passwords, SSH private key contents, SSH private key **path** | Never included | The values never appear. A sanitized error may contain a `<redacted-ssh-key-path>` placeholder marking where the path was removed. |

## Adding a new field

1. Decide its policy: **visible**, **partially redacted**, or **fully
   redacted**.
2. If it needs redaction, add (or reuse) a `sanitize_*` function in
   `diagnostics/sanitize.py` — never redact inline in `__init__.py`. Prepared
   helpers already exist for UUIDs and serial numbers.
3. Add assertions to `scripts/validate_sanitize.py`.
4. Update the table above.
