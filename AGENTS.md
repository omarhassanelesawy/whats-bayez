# Whats Bayz — contributor and agent guide

## Purpose and scope

Whats Bayz is a private, local-only, read-only viewer for WhatsApp conversations from a decrypted Finder iPhone backup. Keep the product name **Whats Bayz** and the WhatsApp-inspired green theme. It is not a live messaging client or a backup decryption tool.

Read [README.md](README.md), [development history and next steps](docs/DEVELOPMENT.md), and [architecture decisions](docs/adr/README.md) before changing behavior.

## Project map

| Path | Responsibility |
| --- | --- |
| `server.py` | Loopback HTTP server, read-only SQLite queries, contacts, history, search and media delivery |
| `index.html` | HTML, CSS and vanilla JavaScript UI; no build step |
| `import_backup.py` | One-time import of related data into an empty private store |
| `test_viewer.py` | Integration tests against the existing local store |
| `store/` | Sensitive, Git-ignored databases and media; never source code or fixtures |
| `docs/adr/` | Accepted architectural decisions and their consequences |

## Non-negotiable data safety

- Never delete, replace, migrate, edit, stage or upload `store/` without explicit approval for that exact operation. Never use it as a disposable test directory.
- The earlier Finder/decrypted backups were deleted with the user's approval. Do not assume another copy exists. Treat this store as the only remaining task data.
- Keep `/store/` in `.gitignore`. Never use `git add -f` for data. Do not put databases, message excerpts, names, phone numbers, screenshots or media into tracked fixtures, logs, docs or issues.
- Do not dump private records for debugging. Prefer schema inspection, counts, IDs and pass/fail assertions. Keep screenshots and browser profiles outside tracked files and remove only explicitly approved artifacts.
- Read live databases using SQLite `mode=ro`. Any future derived indexes must be separate, ignored data, not modifications to the chat database.
- Preserve importer refusal to overwrite a nonempty store and the `.import-incomplete` guard. Never remove that marker just to bypass a failed import.
- Do not recreate deleted backups, rerun import against the populated store, or broaden cleanup without approval.

## Architecture constraints

- Runtime uses Python 3 standard library and vanilla browser APIs. No runtime packages or external CDNs, fonts, analytics, APIs or uploads.
- Bind the server to `127.0.0.1`, not a LAN interface. There is no authentication or TLS; this is not a production/public server.
- Use project-relative `store/` paths, never developer-specific Desktop paths or links to external backup directories.
- Use parameterized SQL for inputs. Render private/user text with `textContent` or DOM text nodes, not interpolated HTML.
- Keep Content Security Policy, `no-store` data responses and media byte-range support.
- A `ZWAMEDIAITEM` row is metadata, not proof of an attachment. Keep `attachment: null` for ordinary text with metadata. See [ADR 0003](docs/adr/0003-message-semantics-and-media.md).
- History cursors use `(COALESCE(ZSORT, 0), Z_PK)`. Search must cover the entire selected chat, not just rendered messages. See [ADR 0004](docs/adr/0004-history-and-search.md).

## Development workflow

1. Read relevant ADRs; inspect existing code and worktree changes before editing.
2. State scope and trade-offs for significant work; obtain approval before new dependencies, data operations or architectural changes.
3. Reproduce the issue using minimal, privacy-safe diagnostics. Add a regression test before or alongside the fix.
4. Make the smallest consistent change. Preserve full-history access, search, media, scrolling and mobile navigation.
5. Run integration tests. For UI changes, validate in a real browser at desktop and mobile widths; syntax checks alone are insufficient.
6. Update README and development notes when commands or behavior change. Add a numbered ADR for a material decision; mark alternatives as proposals until approved.
7. Review Git status and ignored paths. Report tests actually run, limitations and any checks not performed.

## Commands

From the project root:

```bash
python3 server.py
python3 -m unittest -v test_viewer.py
git status --short
git check-ignore -v store/ChatStorage.sqlite store/Manifest.db
```

Viewer URL: `http://127.0.0.1:8765`. Stop the existing server before starting another. Restart after backend changes and hard-refresh after frontend changes.

Tests require the populated private store and suitable records. A fresh clone will not contain the store; report that prerequisite rather than silently manufacturing private fixtures or deleting existing data. The current baseline is 10 integration tests. Browser automation is not a committed project dependency; past temporary browser tooling was removed during cleanup.

## Documentation conventions

ADRs use `NNNN-short-title.md` and include date, status, context, decision, alternatives, consequences and validation. Retrospective ADRs describe implemented decisions; roadmap entries describe proposed work. Do not claim a security guarantee, supported message type or test coverage that the code does not provide.
