# ADR 0003: Attachment semantics, media mapping and identities

- **Date:** 2026-10-06
- **Status:** Accepted (retrospective)

## Context

Finder stores files under hashed IDs, not original names. WhatsApp media paths in its chat database may begin with `Media/`, while backup mappings use `Message/Media/`. Also, hundreds of thousands of ordinary text messages in the inspected backup have `ZWAMEDIAITEM` metadata. Treating every metadata row as an attachment produced false missing-file cards.

## Decision

The API explicitly returns `attachment: null` unless the message has an attachment path or a recognized attachment message type. Contact cards and shared locations receive their own attachment kinds. The frontend renders cards based on this API classification, never solely on `ZMEDIAITEM` being nonzero.

Resolve files by the backup convention `SHA1(domain + '-' + relativePath)`, checking known WhatsApp domains and path variants including `Message/`. Use an explicit thumbnail path or a corresponding `.thumb` fallback. Retain raw file-ID storage inside `store/`.

For available files, display browser-supported images/video/audio and offer downloads. Preserve HTTP byte-range responses for playback/seeking, MIME handling, no-store responses and safe delivery of opaque files. Missing-file warnings are reserved for actual attachment messages whose files are absent. Contact cards and locations do not need a missing-file warning.

Resolve identities using the imported iPhone address book, WhatsApp LID/phone mappings and push names where available. Do not display serialized contact identifiers as names. Use a phone number or an unknown/group fallback when a name cannot be resolved. Sidebar previews prefer actual last-message text and avoid serialized preview strings.

## Alternatives

- **A metadata row implies a file:** demonstrably incorrect for plain text and link metadata.
- **Look only for human-readable filenames:** does not work with Finder's hashed backup storage.
- **Fetch missing files from WhatsApp/cloud URLs:** violates local-only behavior and cannot reliably recover deleted data.
- **Assume every numeric WhatsApp ID is a phone number:** incorrect for group and LID identifiers.

## Consequences

Only backed-up files can be displayed. Browser codec support varies; downloads remain available when inline previews fail. Message-type mappings are version-dependent heuristics, not a complete WhatsApp schema specification. Unknown/system messages may remain unsupported, and identity fields may be incomplete.

Add a regression test when extending message-type handling. Do not classify an unknown message as an attachment merely to avoid a blank state.

## Validation

Tests verify a real plain-text message with metadata receives no attachment, verify available files and byte ranges, and verify name/number fallback. Browser checks confirmed plain text has no false card and real media is rendered from the project store.
