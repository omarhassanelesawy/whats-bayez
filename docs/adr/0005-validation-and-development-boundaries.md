# ADR 0005: Validation and privacy-safe development

- **Date:** 2026-10-06
- **Status:** Accepted (retrospective)

## Context

Several defects were specific to real backup semantics or browser layout: metadata mistaken for media, hashed path prefixes, inaccessible older history and a flex layout that did not scroll. Syntax checks alone could not verify these behaviors. Test input is highly private.

## Decision

Keep read-only integration tests against the configured local store, with an ephemeral loopback HTTP server. Validate UI changes in a real browser at desktop and mobile widths when tooling is available. Do not commit private chat fixtures, browser screenshots, profiles or captured API responses.

Use schema/count diagnostics instead of exposing record content. Keep temporary browser tooling outside the project and treat it as optional development tooling, not a runtime dependency. Record validations actually performed and report missing prerequisites.

Maintain developer guidance in `AGENTS.md`, user commands in `README.md`, accepted architecture in `docs/adr/`, and chronological work/proposed next steps in `docs/DEVELOPMENT.md`.

## Alternatives

- **Syntax-only checks:** do not catch browser scrolling or schema semantics.
- **Commit a sampled real backup:** creates a privacy leak, even if the sample is small.
- **Require a large private backup in public CI:** impractical and unsafe.
- **Add synthetic fixtures now:** desirable future work, but not yet implemented or required for the current local integration suite.

## Consequences

The existing 10 tests require a populated store with suitable message/media examples. A fresh Git clone cannot run them without importing data. There is no committed browser test harness or public CI configuration. Past browser checks were temporary scripts and their artifacts were deleted during approved cleanup.

Future deterministic synthetic fixtures should complement, not replace, private-store smoke tests. Public test data must be invented rather than derived from this backup.

## Validation

All 10 integration tests passed after migration and cleanup. Prior Chrome checks covered branding, green palette, ordinary text without attachment warnings, media, history, per-chat search, result navigation, internal scrolling and mobile layout. This records previous checks; it does not imply continuous browser coverage.
