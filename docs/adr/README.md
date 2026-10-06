# Architecture decision records

These records document the implemented architecture retrospectively on 2026-10-06. They are not proposals to rewrite the app.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-local-runtime-and-ui.md) | Local Python HTTP server and dependency-free browser UI | Accepted |
| [0002](0002-private-self-contained-store.md) | Private, self-contained project store and read-only access | Accepted |
| [0003](0003-message-semantics-and-media.md) | Explicit attachment semantics and Finder media mapping | Accepted |
| [0004](0004-history-and-search.md) | Stable history pagination, whole-chat search and context jumps | Accepted |
| [0005](0005-validation-and-development-boundaries.md) | Integration/browser validation and privacy-safe development | Accepted |
| [0006](0006-direct-conversation-identity-links.md) | Resolve sender LIDs through unambiguous incoming direct-conversation links | Accepted |
| [0007](0007-portable-local-configuration.md) | Portable own-backup setup and configurable loopback port | Accepted |

For a new architectural decision, add the next numbered record and update this index. Include context, decision, alternatives, consequences and validation. Mark proposed decisions as **Proposed**; do not silently rewrite an accepted decision when superseding it. Link its replacement instead.
