# ADR 0004: History pagination and whole-chat search

- **Date:** 2026-10-06
- **Status:** Accepted (retrospective)

## Context

The initial latest-message view made older history difficult to reach. Conversations can contain hundreds of thousands of messages, so loading all history into the DOM is inappropriate. The user also requested per-chat search that finds unloaded messages.

## Decision

Use keyset history pagination ordered by `(COALESCE(ZSORT, 0), Z_PK)`, not date alone. The message primary key breaks ties. Bound normal message pages to at most 250 messages; the UI currently requests 150.

Support:

- Latest history and explicit **Go to start**.
- Older and newer cursor pages.
- Automatic boundary loading with explicit buttons as a fallback.
- An `around` message ID that returns bounded context after checking the target belongs to the selected chat.
- Scroll-anchor preservation when adding pages. Existing message/media elements are retained rather than rebuilding all loaded cards.

Search runs in SQLite against the entire selected chat's message text, attachment captions, contact-card names and original sender names. Use a Python `casefold` SQLite function and literal `instr` matching, parameterized queries, exact match counts and newest-first result ordering. Search result pages use offsets and are capped at 100 records; the UI requests 50 and can load more.

Clicking a result loads its surrounding context and highlights the target. Debounce input and cancel/ignore stale browser requests. Cmd+F / Ctrl+F opens the per-chat search panel.

## Alternatives

- **Search only DOM messages:** misses most history.
- **Date-only cursors:** can skip or repeat equal-date messages.
- **Fetch everything:** excessive memory, response size and DOM cost.
- **Modify the chat DB with a search index:** breaks the read-only data boundary.
- **Use FTS immediately:** adds derived-store and search-semantics complexity; keep as an explicitly proposed optimization.

## Consequences

History paging is bounded and stable for the inspected schema. Loaded pages still accumulate in the DOM; windowing/virtualization is not implemented. Whole-chat search scans records and calculates counts for each query, which may be slow on the largest chats. Offset search paging also becomes more expensive at deep result positions.

Frontend highlight matching uses JavaScript case-insensitive regex, so it is not perfectly equivalent to Python Unicode `casefold` for every character. Search on resolved address-book names is not implemented; backend sender matching uses stored push names.

## Validation

Integration tests compare adjacent pages to direct database ordering, test earliest-history access, whole-chat matches outside the latest page, literal wildcard characters, result pagination and rejection of cross-chat jumps. Chrome checks verified search, visible target navigation and desktop/mobile scrolling. Broader Unicode and cursor-edge fixtures remain proposed work.
