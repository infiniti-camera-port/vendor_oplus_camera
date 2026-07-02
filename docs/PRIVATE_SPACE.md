# Private Space / OP15InfinityX priv-app set — status and future work

**Status:** the OP15InfinityX "private-space" app cluster is intentionally NOT shipped in full.
Three of its priv-apps were **dropped** (see `5585a11 camera: drop the
UMS/PhoneManager/OplusExSystemService priv-apps`); a stub-based accommodation that would let the
OplusCamera stack run without them was **considered and deliberately abandoned** — nothing is
stubbed. This file is the marker + future-work note. It documents intent only; it re-adds no apps
and implements no stubs.

Full provenance (origin commits, manifest surfaces, per-app consumer analysis, verification method)
lives in the project evidence doc `privspace-apps-provenance.md` — treat that as the authoritative
reference; this file is the in-tree pointer.

## What was dropped and why

The private-space port (`1fa1bf1 camera: port OP15InfinityX private-space support`) pulled six OOS
apps into the build. Three of them are `system_ext` **priv-apps** that request platform privileged
permissions with no allowlist entry. Under `ro.control_privapp_permissions=enforce` (LOS userdebug)
the privapp check turns each into an `IllegalStateException` at `AppIdPermissionPolicy.onSystemReady`
→ `system_server` death → hard bootloop. They are OnePlus/OOS private-space + security **bloat**, not
part of AI Unit and not load-bearing for the camera stack, so they were dropped rather than
allowlisted (the enforce gate only fires for packages that are present):

- **com.oplus.pantanal.ums** (UMS) — Pantanal "user model service" / smart-card + decision hub.
- **com.oplus.phonemanager** (PhoneManager) — OOS cleanup/security app.
- **com.oplus.exsystemservice** (OplusExSystemService) — OEM extended-system-service backend.

Absence tolerance is proven: v3.3 shipped and ran OplusCamera/Gallery without any of these; the
OOS-derived code paths that reference them hit **caught** `NameNotFoundException` / missing-provider
fallbacks and continue. In particular, **OplusCamera's Pantanal/UMS FluidCard hooks fail closed
benignly** — the bundled seedling/card-widget SDK queries authority
`com.oplus.pantanal.ums.decision`, gets "Failed to find provider" (non-fatal), and the FluidCard
feature simply stays dark. No camera capture/preview/gallery function depends on it.

## Kept siblings (same 1fa1bf1 bundle — deliberately retained)

These three came in with the same bundle and are **kept**; they are not priv-apps with unallowlisted
platform perms (or are already allowlisted), so they carry no bootloop exposure:

- **com.oplus.encryption** (FileEncryption) — `system_ext/priv-app`; the Private Safe vault. Its one
  platform priv perm (`WRITE_SECURE_SETTINGS`) is covered by
  `configs/permissions/privapp-permissions-oplus.xml`. Serves Gallery/FileManager "move to Private
  Safe" and the cryptoeng App Lock path.
- **com.oneplus.filemanager** (FileManager) — `system_ext/app` (not a priv-app). OOS file manager;
  primarily serves the private-safe move flow.
- **com.oplus.securitypermission** (SecurityPermission) — `system_ext/app` (not a priv-app). OOS
  security/permission controller backend.

If private-space is ever fully abandoned, these three can be dropped together as one decision;
keeping them is harmless.

## TODO — future "Private Safe" accommodation (deferred, DO NOT build here)

If Private Safe / the OplusCam private-space integration is ever wanted **without** shipping the OEM
bloat backends, the intended path is a minimal **stub surface**, not re-adding the dropped apks. The
full blueprint is captured in `privspace-apps-provenance.md` ("Future: stub-based accommodation").
Sketch:

- A **Pantanal/UMS stub** (`com.oplus.pantanal.ums`): a ContentProvider at authority
  `com.oplus.pantanal.ums.decision` returning empty cursors/Bundle, satisfying the FluidCard query
  path (plus the other card/seedling authorities + `CardReqService`/`CardComponentService` binders
  the SDK touches when card features are driven). Only needs to exist and be permission-compatible.
- **PhoneManager** needs no stub (only an AppPlatform caller-identity `String.equals`, already
  caught).
- **OplusExSystemService** needs no live stub (AIMemory's bundled helper is already an in-apk
  all-"stub" replica); a stub is only warranted if future OEM apps live-bind its services.
- A single **oplus-permission-definer stub** defining the `com.oplus.permission.safe.*` family would
  make the OEM cross-app signature guards resolvable — but signature-level guards mean an OEM app only
  holds a perm defined by an OEM-presigned definer, so the practical alternative is smali no-ops in
  the consumers we keep. Capture only.

Until then: no stubs, no re-added apks. The dropped set stays dropped.
