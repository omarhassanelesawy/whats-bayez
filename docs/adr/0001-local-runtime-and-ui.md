# ADR 0001: Local runtime and dependency-free UI

- **Date:** 2026-10-06
- **Status:** Accepted (retrospective)

## Context

The user wanted to browse a Finder backup without iMazing, with no cloud upload. The chat database is large enough that copying it into browser memory and loading all messages eagerly would be impractical. The final product is named **Whats Bayz** with WhatsApp-like green colors.

## Decision

Use Python's `ThreadingHTTPServer` and SQLite standard-library bindings, bound to `127.0.0.1:8765`. Serve a single `index.html` containing the UI, styles and vanilla JavaScript. Database access happens on the local server; the browser receives bounded JSON pages and media responses.

The original brand asset is local `logo.svg`, shared by the UI and favicon. Static routes are explicitly limited to `/`, `/index.html` and `/logo.svg`; source files and private store files are not static assets.

Endpoints:

- `/api/status`: local database presence.
- `/api/chats`: conversation list and resolved identities.
- `/api/messages`: history pages or context around a selected message.
- `/api/search`: whole-chat search results.
- `/api/media`: attachment/thumbnail bytes and downloads.

Keep external resources out of the UI. Render content as text, maintain the Content Security Policy, and avoid logging chat contents or query parameters.

## Alternatives

- **Browser-only SQLite/WASM:** avoids a server but adds dependencies and substantial browser memory/file-management complexity.
- **React/Node or another framework:** viable later, but unnecessary for the current local viewer and adds a toolchain.
- **Hosted service or extractor:** conflicts with the requested local workflow and privacy goal.

## Consequences

There is no build step or runtime package installation. A local Python process must stay running. HTML/CSS/JS currently share one file; extraction into local static files may improve maintainability later.

Loopback binding is a deployment boundary, not authentication. The app has no TLS or authentication and is not hardened for public hosting. Do not expose it to the network without a new security design.

## Validation

Integration tests exercise API responses using an ephemeral loopback port. Chrome checks previously verified rendering, scrolling, search, result jumps and mobile layout. Temporary browser automation files were removed after testing.
