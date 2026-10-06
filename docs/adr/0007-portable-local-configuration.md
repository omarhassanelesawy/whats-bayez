# ADR 0007: Portable local configuration

- **Date:** 2026-10-06
- **Status:** Accepted

## Context

Users need to configure the viewer for their own iPhone backup without editing source paths or sharing private data. The importer already accepts a backup folder argument; runtime data is project-relative. Multiple independent installations can collide on the default HTTP port.

## Decision

Keep one private `store/` per installation. Configure the one-time source backup through `import_backup.py`'s existing positional argument. Add `server.py --port`, defaulting to `8765` and accepting `1` through `65535`. Always bind to `127.0.0.1`; do not offer a host override.

Use CLI configuration rather than a new config format or dependency. Document own-backup preparation, fresh import, custom ports, troubleshooting, platform validation limits and source-only sharing in README. Preserve nonempty-store refusal and the incomplete-import guard. Use separate fresh source installations for different backups; no replace/update operation is introduced.

## Alternatives

- **Committed user paths or secrets:** nonportable and risks exposing private data.
- **`.env` or JSON configuration:** unnecessary for the existing source argument and one runtime option.
- **Arbitrary external store paths or multi-user service:** broadens the data and deployment model beyond this request.
- **Host override:** creates a LAN/public exposure risk without authentication or TLS.

## Consequences

Existing startup commands work unchanged. Users can select separate local ports without editing code. Runtime remains dependency-free and local-only. Other operating systems and backup schema versions remain unverified; documentation does not promise universal compatibility. Imports are still one-time snapshots, not resumable refresh operations.

## Validation

Five configuration tests without private data cover default/custom ports, rejection of invalid values, bind-error guidance and Control-C handling. The existing 14 viewer tests also pass. Both CLI help commands were checked. Fresh import and Windows/Linux behavior were not tested during this change; the current private store was not modified.
