# BTicino Classe 100X — Protocol & Platform Reference

> Consolidated technical reference for the `bticino-classe100x-ha` integration.
> It documents how the device is accessed, the OpenWebNet protocol it speaks, the
> SSH transport, the firmware/OTA model, and the security posture — with the
> **evidence and verification status for every claim**.

**Target unit for this document:** BTicino `344682` (Classe 100X16E), firmware **1.5.8**,
fquinto-flashed. Values are specific to this model/firmware unless noted; other
revisions are expected to be similar but **must not be assumed** — parsers and
clients must degrade gracefully on unexpected formats.

---

## 0. Verification legend

Every factual line carries one of these markers. This is the backbone of the document — respect it.

| Marker | Meaning |
|--------|---------|
| ✅ **DEVICE** | Verified live on the actual unit (via SSH / PowerShell / a spike). Highest confidence. |
| 📦 **IMAGE** | Read from the extracted stock firmware image (`btweb_only.ext4`). True of the image; the flashed unit *may* differ — confirm on device when it matters. |
| ⚙️ **SPIKE** | Proven by a throwaway validation script against the live unit. |
| ⚠️ **INFERRED** | A reasoned conclusion from evidence, not a direct measurement. Treat as a strong hypothesis, not fact. |
| ❓ **UNVERIFIED** | Plausible (often from third-party repos) but **not** confirmed here. Do not build on it without capturing/testing first. |

Document date: 2025 (firmware 1.5.8 era). Re-validate against newer firmware before relying on any ✅ that could have changed.

---

## 1. Device identification

| Property | Value | Status |
|----------|-------|--------|
| Commercial model | `344682` — Classe 100X16E "with Netatmo" | ✅ DEVICE (physical label) |
| Manufacture date code | `20W26 070` → week 26 of 2020 | ✅ DEVICE (label) |
| Cloud generation | **Pre-Netatmo** (produced before June 2023 → old BTicino "Door Entry" infrastructure) | ⚠️ INFERRED (from date vs. the documented June-2023 cutoff) |
| Firmware version | `1.5.8` (from `ver_webserver`) | ✅ DEVICE |
| Firmware build stamp | `/etc/version` = `20250522064330` → 2025-05-22 06:43:30 | ✅ DEVICE |
| Installed package | `C100X_010508.fwz` (`latest_sp`) | ✅ DEVICE |
| Webserver type | `C100X` (`webserver_type`) | ✅ DEVICE |
| Object model | `1.0.99` | 📦 IMAGE (FWZ manifest) |
| SoC / kernel | NXP i.MX, kernel `4.9.11+imx+` | 📦 IMAGE |
| WiFi driver | Broadcom `brcmfmac` | 📦 IMAGE |
| Interactive hostname | `shark` | ✅ DEVICE |
| Non-interactive `hostname` | `C1X-00-03-50-b6-...` (differs from `shark` — matters for device-info) | ✅ DEVICE |
| Flash state | fquinto custom firmware (adds `root2` SSH account) | ✅ DEVICE |

**Firmware/model source of truth on-device:** `/home/bticino/sp/dbfiles_ws.xml`
```xml
<webserver_type>C100X</webserver_type>
<ver_webserver>1.5.8</ver_webserver>
<latest_sp>C100X_010508.fwz</latest_sp>
```
`/etc/version` holds the **build timestamp**, not the semantic version — do not use it as the firmware version.

---

## 2. Network architecture

### 2.1 Interfaces

| Interface | Address | Role | Status |
|-----------|---------|------|--------|
| `wlan0` | DHCP from home router (e.g. `192.168.50.251`) | Normal LAN connectivity (WiFi only) | ✅ DEVICE |
| `usb0` | `192.168.129.1/30` | USB-gadget link; PC gets `192.168.129.2` (single DHCP lease, /30) | 📦 IMAGE + ✅ DEVICE |

### 2.2 Listening sockets

Decoded from `/proc/net/tcp` (LISTEN state; little-endian IP, hex port). ✅ DEVICE.

| Address:Port | Service | Reachability |
|--------------|---------|--------------|
| `0.0.0.0:20000` | OpenWebNet (plain) | All interfaces — LAN-reachable *if firewall allows* |
| `0.0.0.0:40000` | OpenWebNet over TLS | All interfaces |
| `0.0.0.0:40005` | XML-OpenWebNet over TLS | All interfaces |
| `0.0.0.0:22` | SSH (dropbear) | All interfaces (always open) |
| `127.0.0.1:30006` | OpenWebNet **commands** (`bt_vct`) | **localhost only** |
| `127.0.0.1:30007` | OpenWebNet config | localhost only |
| `192.168.50.251:5061` | SIP/TLS (call/media signalling) | bound to the LAN IP |

Other localhost-only ports observed: `20001`, `30013`, `31006/7/13`, `60000`. ✅ DEVICE.

### 2.3 Firewall (iptables)

Policy `INPUT DROP`. The OWN ports are gated to the USB link; SSH is open everywhere. ✅ DEVICE (`iptables -S`).

```
-P INPUT DROP
-A INPUT -i lo -j ACCEPT
-A INPUT -i usb0 -p tcp --dport 20000 -j ACCEPT      # OWN plain: USB only
-A INPUT        -p tcp --dport 20000 -j DROP         # ... dropped for LAN
-A INPUT -i usb0 -p tcp --dport 20005 -j ACCEPT      # (same pattern for 20005/40000/40005)
-A INPUT        -p tcp --dport 20005 -j DROP
-A INPUT -i usb0 -p tcp --dport 40000 -j ACCEPT
-A INPUT        -p tcp --dport 40000 -j DROP
-A INPUT -i usb0 -p tcp --dport 40005 -j ACCEPT
-A INPUT        -p tcp --dport 40005 -j DROP
-A INPUT        -p tcp --dport 22 -j ACCEPT          # SSH: all interfaces
-A INPUT        -p tcp --dport 5061 -j ACCEPT        # SIP
-A INPUT        -p tcp --dport 53 -j ACCEPT          # + 67,68,5353,5678,50003 ...
```

Key facts:
- `iptables` binary is at **`/usr/sbin/iptables`** (symlink → `xtables-multi`). A **non-interactive SSH shell has a minimal PATH** without `/usr/sbin`, so always call it by absolute path. ✅ DEVICE.
- Firewall rules are **volatile** — a reboot rebuilds them from stock, dropping any injected rule. ✅ DEVICE (see §6.3).
- **The kernel has no NAT table.** `iptables -t nat -L` → `can't initialize iptables table 'nat': Table does not exist`. No `nf_nat`/`iptable_nat`, no NAT kernel modules on the image. A LAN→localhost DNAT redirect is therefore **impossible**. ✅ DEVICE + 📦 IMAGE.

---

## 3. Access strategy (the core architecture)

The device forces an **asymmetry** that dictates the whole integration design:

| Capability | Port | Bind | Auth | Path |
|------------|------|------|------|------|
| **Listen** (events) | `20000` | `0.0.0.0` (LAN-reachable) | OPEN password | Direct TCP from HA over LAN — *needs firewall opened* |
| **Act** (open gate/door) | `30006` | `127.0.0.1` (localhost only) | none | SSH → `nc 127.0.0.1 30006` on the device |

- **Listen** happens over the LAN on 20000 (authenticated). It requires the firewall rule (§6) to be present.
- **Act** must run on the device because 30006 is localhost-only; SSH is the tunnel. SSH here provides the *only* authentication on the command path (the key), since 30006 itself has none.
- The two use **different transports** (20000 direct TCP vs 22 SSH) and **can fail independently** — availability and errors should treat them separately.

Why not other approaches (all ruled out with evidence):
- **OTA/firmware patch over WiFi** — blocked by RSA-signed images (§7). ✅/📦
- **Direct commands to 20000 over LAN** — 20000 NACKs door-entry actuations; those live on 30006. ✅ DEVICE.
- **NAT redirect LAN→localhost:30006** — no NAT in kernel (§2.3). ✅ DEVICE.
- **Cloud (Netatmo HACS integration)** — unit is pre-Netatmo/Door Entry generation. ⚠️ INFERRED.

---

## 4. OpenWebNet protocol

### 4.1 Ports & session types

| Frame | Meaning | Status |
|-------|---------|--------|
| `*99*0##` | Request **command** session | ✅ DEVICE (repo-documented + used) |
| `*99*1##` | Request **event/monitor** session | ✅ DEVICE |
| `*#*1##` | ACK (also the connection banner) | ✅ DEVICE |
| `*#*0##` | NACK | ✅ DEVICE |

### 4.2 `openserver` configuration

From `/home/bticino/cfg/openserver`. 📦 IMAGE (matches device behaviour ✅).

```
IsGateway=1
IsPermissive=1          # lets the LAN session through despite [Range Ip]
ForceHMAC=0             # HMAC scheme NOT required → legacy OPEN scheme is used
OwnPort=20000  XmlPort=20005  SslOwnPort=40000  SslXmlOwnPort=40005
MaxClient=50            # session ceiling — relevant to a sustained monitor session
[Range Ip]
range_01=192.168.129.2  # app-level allow-list = the USB peer only
[Stackopen]
client_02=bt_vct;0;4;8  # bt_vct handles WHO 0,4,8 (door entry)
```
`stack_open.xml`: `<authentication><hmac>0</hmac><open>1</open></authentication>` → OPEN auth active. 📦 IMAGE.

### 4.3 OPEN authentication handshake (port 20000)

Sequence proven end-to-end on the device (⚙️ SPIKE + ✅ DEVICE):

```
client connects
server → *#*1##                        (banner)
client → *99*1##                       (request event session)
server → *#<NONCE>##                   (OPEN nonce — digits only; changes every connection)
client → *#<own_calc_pass(pw,NONCE)>## (computed response)
server → *#*1##  (OK)  |  *#*0## (wrong password)
              → event stream begins
```

- **Password on this unit: `12345`** (factory default) — ✅ DEVICE (auth succeeded).
- The **nonce changes on every connection** — never cache it. ✅ DEVICE.
- `ForceHMAC=0` means the stronger HMAC (`*98*...`) scheme is not required; the legacy OPEN scheme (the `*#<nonce>##` challenge) is what this unit uses. ✅ DEVICE.

### 4.4 The `own_calc_pass` algorithm

The classic BTicino OPEN password algorithm (from fquinto `calc_passwd.py`; matches known OWN libraries). Executed and cross-checked here (⚙️ SPIKE).

```python
def own_calc_pass(password: str, nonce: str) -> int:
    start = True
    num1 = 0
    num2 = 0
    pwd = int(password)
    for c in nonce:
        if c != "0":
            if start:
                num2 = pwd
            start = False
        if c == "1":
            num1 = (num2 & 0xFFFFFF80) >> 7;  num2 = num2 << 25
        elif c == "2":
            num1 = (num2 & 0xFFFFFFF0) >> 4;  num2 = num2 << 28
        elif c == "3":
            num1 = (num2 & 0xFFFFFFF8) >> 3;  num2 = num2 << 29
        elif c == "4":
            num1 = num2 << 1;                 num2 = num2 >> 31
        elif c == "5":
            num1 = num2 << 5;                 num2 = num2 >> 27
        elif c == "6":
            num1 = num2 << 12;                num2 = num2 >> 20
        elif c == "7":
            num1 = (num2 & 0x0000FF00 | ((num2 & 0x000000FF) << 24)
                    | ((num2 & 0x00FF0000) >> 16)); num2 = (num2 & 0xFF000000) >> 8
        elif c == "8":
            num1 = (num2 & 0x0000FFFF) << 16 | (num2 >> 24); num2 = (num2 & 0x00FF0000) >> 8
        elif c == "9":
            num1 = ~num2
        else:
            num1 = num2
        num1 &= 0xFFFFFFFF
        num2 &= 0xFFFFFFFF
        if c not in "09":
            num1 |= num2
        num2 = num1
    return num1
```

Response frame = `f"*#{own_calc_pass(pw, nonce)}##"`.

**Verified test vectors** (⚙️ SPIKE — use these in unit tests):

| password | nonce | → response |
|----------|-------|-----------|
| `12345` | `603356072` | `25280520` |
| `12345` | `410501656` | `119537670` |
| `12345` | `620942509` | `12641280` |
| `12345` | `392005583` | `4022796255` (from a live handshake) |

### 4.5 Event / command frames (WHO=8, door entry)

**Verified on this unit** — these physically actuate / are emitted (✅ DEVICE):

| Frame | Meaning |
|-------|---------|
| `*8*19*20##` | Gate (WHERE=20) — button **press** |
| `*8*20*20##` | Gate (WHERE=20) — button **release** |
| `*8*19*21##` | Pedestrian door (WHERE=21) — press |
| `*8*20*21##` | Pedestrian door (WHERE=21) — release |

Structure: `WHO=8`, `WHAT=19` (press) / `WHAT=20` (release), `WHERE` = target (20 = gate, 21 = pedestrian on this install). Each actuation emits a press/release **pair**. WHERE values are **installation-specific** — other units may differ; discover per-install (§9).

**Call / doorbell frames — ❓ UNVERIFIED.** No call occurred during monitoring, so these were never captured. Candidates from fquinto `constants.go`, **not confirmed here**:
```
*8*1#1#4#21*16##    # doorbell / call from entrance panel (candidate)
*8*1#5#4#20*16##    # self-call: eye button activates camera (candidate)
*8*2#5#4*16##       # answer / pick up (candidate)
*8*3#1#4*416##      # hang up (candidate)
```
**Action:** capture these live (monitor session across a real ring → answer → hang-up) before mapping call entities.

### 4.6 Sending a command (port 30006)

Proven ✅ DEVICE:
```sh
printf '*8*19*20##*8*20*20##' | timeout 2 nc 127.0.0.1 30006
→ *#*1##*#*1##        # one ACK per frame; gate opens
```
- **No authentication** on 30006 (it's localhost/trusted). No `*99*` handshake, no nonce. ✅ DEVICE.
- Both gate (WHERE=20) and pedestrian (WHERE=21) confirmed. ✅ DEVICE.
- Success is judged by the **ACK count**, not the shell exit code — `timeout` can force a non-zero exit even on success.

---

## 5. SSH transport

| Property | Value | Status |
|----------|-------|--------|
| User | `root2` (added by the fquinto flash) | ✅ DEVICE |
| Auth | private key (password path not used) | ✅ DEVICE |
| Port | 22 (open on all interfaces) | ✅ DEVICE |
| Host key | **regenerates on every reboot** | ✅ DEVICE |

**OpenSSH CLI legacy flags** needed for the old dropbear (✅ DEVICE):
`HostKeyAlgorithms=+ssh-rsa`, `PubkeyAcceptedAlgorithms=+ssh-rsa`, `MACs=hmac-sha1`,
plus `StrictHostKeyChecking=no` + `UserKnownHostsFile=/dev/null` (no host-key verification).

**`asyncssh` (native async client) — validated (⚙️ SPIKE, `asyncssh 2.24.0`):**
- Connects on **default algorithms** — no `ssh-rsa`/`hmac-sha1` forcing needed (better than the CLI).
- Result object exposes `.stdout`, `.stderr`, **`.exit_status`** (not `returncode`).
- `conn.is_closed()` is the liveness accessor; `conn.close()` + `await conn.wait_closed()` closes cleanly.
- **Persistent connection reuse:** handshake ~852 ms once, then commands ~54–184 ms (4–15× faster).
- **Idle survival:** ≥ 5 minutes idle without drop (30/60/120/240/300 s tested). >5 min untested.
- **Reboot recovery:** drop detected (`ChannelOpenError: SSH connection closed`); auto-reconnect works. ⚠️ **A connect with no `connect_timeout` hung ~43 s** against the offline unit — always set `connect_timeout` and use bounded backoff.

---

## 6. Firewall unlock (the "listen" prerequisite)

### 6.1 The rule
```sh
/usr/sbin/iptables -I INPUT -p tcp -s <HA_IP> --dport 20000 -j ACCEPT
```

### 6.2 Idempotent application (avoid duplicate rules)
```sh
/usr/sbin/iptables -C INPUT -p tcp -s <HA_IP> --dport 20000 -j ACCEPT 2>/dev/null \
  || /usr/sbin/iptables -I INPUT -p tcp -s <HA_IP> --dport 20000 -j ACCEPT
```

### 6.3 The reboot cycle — proven end-to-end (✅ DEVICE)

| Step | Command | Result |
|------|---------|--------|
| Blocked by default | `Test-NetConnection :20000` | `TcpTestSucceeded: False` |
| Open the rule | `iptables -I INPUT ... --dport 20000 -j ACCEPT` | — |
| Reachable | `Test-NetConnection :20000` | `True` |
| **Reboot resets stock** | (device reboots) | rule gone: `-C` → `REGRA_AUSENTE`, `:20000` → `False` |
| Re-inject | `iptables -I ...` | `:20000` → `True` again |

**Implication:** the event client MUST re-inject the rule on every reconnect (a dropped OWN session is the signal the device likely rebooted). `<HA_IP>` should be resolved **dynamically** (DHCP can change it) rather than hardcoded.

---

## 7. Firmware & OTA (why the design avoids flashing)

📦 IMAGE (read from the extracted firmware; OTA not exercised live):

- OTA updater `dedrifupdater`/`fw_manager` performs OpenSSL **RSA-2048/SHA-256 signature verification** on the filesystem, kernel, recovery kernel, and the `FWZ.xml` manifest, against a baked-in cert chain (`CN=C100X` → Bticino intermediate CA → root CA) at `home/bticino/certs/public_cert.pem`.
- A modified `.fwz` fails verification (no Legrand private key). The USB DFU flash path bypasses `dedrifupdater` entirely — which is why the community method flashes over USB.
- `dedrifu.sh` runs the updater at boot if a file exists at `/home/bticino/cfg/extra/UPGRADE.fwz`; OTA downloads land at `/home/bticino/cfg/extra/FW/UPDATE.fwz`.
- The firmware `.fwz` is a ZipCrypto archive; the community password is `C100X`.

**Consequence:** you cannot patch the running firmware over WiFi. The integration deliberately talks to what stock exposes rather than modifying firmware.

---

## 8. Security model (honest)

State this plainly in `SECURITY.md` rather than implying the channel is "secure":

- **OPEN auth is weak and the password is the public default `12345`.** ✅ DEVICE. Anyone who can reach port 20000 and knows the (public) algorithm can authenticate. The firewall rule restricting to the HA IP is the main gate — and source IPs are spoofable on a LAN.
- **The command port (30006) has no authentication** — its only protection is being localhost-only; SSH (the key) is the real auth on the command path. ✅ DEVICE.
- **SSH host-key verification is disabled** (`known_hosts=None`). Because the host key regenerates on reboot, naïve pinning is not viable; see the host-key issue for the TOFU-with-re-trust alternative. ✅ DEVICE.
- **Legacy crypto** (`ssh-rsa`, `hmac-sha1`) is a device limitation, not a choice.
- Net posture: this is a **trusted-home-LAN** integration, not a hardened one. That is acceptable and honest — document it, don't hide it.

---

## 9. Open questions & unverified items

Tracked honestly so nobody mistakes them for solved:

1. ❓ **Call/doorbell frames** (§4.5) — never captured; the highest-value gap for "listen".
2. ⚠️ **Sustained-session coexistence** — a *single* session works; a permanently-open monitor session coexisting with native processes over hours/days (and vs `MaxClient=50`) is **unproven**. Needs a soak test.
3. ❓ **SSH idle survival > 5 min** — proven only to 5 minutes.
4. ⚠️ **WiFi jitter** — measured 0% loss but 4–164 ms (avg ~69 ms), consistent with radio power-saving (inferred, not a direct RSSI reading). Size event-client timeouts for the worst case, not the average.
5. ❓ **WHERE values are installation-specific** — gate=20 / pedestrian=21 is true *here*; other installs differ. The in-integration capture mode (issue #38 §7.6) is the mechanism for users to discover their own.
6. ⚠️ **Netatmo migration** — this pre-2023 unit is not migratable per Legrand's 2023 statement; re-confirm if it matters (policy could change).

---

## 10. Reproduction (spike scripts)

Throwaway scripts used to validate the above, kept for re-validation against new firmware. All connect over the LAN with the firewall rule (§6) active.

- **`own_monitor.py`** — OPEN-authenticated monitor session; prints raw event frames. Use to capture unknown frames (e.g. §4.5 calls).
- **`spike_asyncssh.py`** — asyncssh handshake + one command (viability gate).
- **`spike_persistent.py`** — one connection, several timed commands (reuse proof).
- **`spike_idle_reconnect.py`** — idle sweep 30–300 s (idle survival).
- **`spike_reboot.py`** — command loop + external reboot (drop detection + auto-reconnect).

Firewall test one-liners (PowerShell):
```powershell
Test-NetConnection 192.168.50.251 -Port 20000          # reachability
ssh bticino "/usr/sbin/iptables -C INPUT -p tcp -s <HA_IP> --dport 20000 -j ACCEPT 2>/dev/null && echo PRESENT || echo ABSENT"
```

---

## 11. Quick reference (cheat sheet)

```
Firmware/model : /home/bticino/sp/dbfiles_ws.xml (ver_webserver / webserver_type / latest_sp)
Build stamp    : /etc/version  (YYYYMMDDHHMMSS)
iptables path  : /usr/sbin/iptables   (absolute — non-interactive PATH is minimal)

Listen : LAN → host:20000, OPEN auth (pw 12345), needs firewall rule
         banner *#*1## → *99*1## → *#NONCE## → *#calc## → *#*1##
Act    : SSH → nc 127.0.0.1 30006  (no auth), ACK per frame = *#*1##
         gate  : *8*19*20## + *8*20*20##
         pedes.: *8*19*21## + *8*20*21##
Unlock : iptables -I INPUT -p tcp -s <HA_IP> --dport 20000 -j ACCEPT   (volatile; re-inject on reconnect)
SSH    : root2 + key ; host key regenerates on reboot ; asyncssh 2.24.0 on defaults
```
