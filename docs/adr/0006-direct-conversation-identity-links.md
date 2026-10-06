# ADR 0006: Direct-conversation identity links

- **Date:** 2026-10-06
- **Status:** Accepted

## Context

Some incoming messages identify their sender with a LID, while their direct conversation is addressed to a phone JID. An empty explicit LID mapping table previously left those sender popups unresolved despite the corresponding conversation header displaying a phone number.

## Decision

During the existing read-only, cached contact lookup, collect distinct pairs of incoming message `ZFROMJID` ending in `@lid` and the linked conversation `ZCONTACTJID` ending in `@s.whatsapp.net` or `@c.us`. Accept only numeric phone local parts and only one distinct phone number per LID. Normalize equivalent phone-JID suffixes before checking conflicts.

Use these pairs as fallback mappings; do not overwrite explicit LID mappings. The shared identity resolver applies them to message and search sender labels/numbers, including group members using the same LID. Never derive a link from outgoing messages, group conversation IDs or display-name equality.

## Alternatives

- **Only explicit LID database mappings:** misses identities already linked by direct conversations.
- **Match display names:** risks linking different people with identical names.
- **Treat a LID as a phone number:** fabricates a number from an opaque identifier.

## Consequences

More sender popups can display backed-up phone identities without new dependencies or store modifications. Conflicting direct-conversation evidence remains unresolved. This is a backup-schema identity inference, not independent verification of current phone ownership.

## Validation

All 14 tests passed. Read-only integration coverage checks agreement between direct-chat header, message sender, search sender and a linked group sender. Invented pairs verify conflicting links are discarded and equivalent phone suffixes agree.
