# Development history and future sequence

Project: **Whats Bayz**. Current home: `~/workdir/dev/whats-bayz`. Runtime data: project-local, ignored `store/`.

## Completed sequence

The following is a retrospective of work completed on 2026-10-06. No private chat contents or credentials are recorded here.

| Step | Work completed | Result / lesson |
| --- | --- | --- |
| 1 | Inspected Finder backup metadata; identified encryption. User decrypted it outside the viewer. | Decryption is not an app responsibility. |
| 2 | Located `ChatStorage.sqlite` through Finder manifest mappings. | Files use backup IDs, not ordinary names. |
| 3 | Built local Python/SQLite API and a vanilla WhatsApp-like browser UI. | Initial viewer showed bounded latest history and placeholder media. |
| 4 | Added earliest-history access, bidirectional paging, attachment mapping and identity resolution. | Both `Media/` and `Message/Media/` paths matter. Contact identifiers are not display names. |
| 5 | Fixed constrained flex layout and message scrolling. | Internal scrolling needs bounded parents and `min-height: 0`. |
| 6 | Added per-chat full-history search, result pagination and jumps into surrounding context. | Search must query the database, not the rendered window. |
| 7 | Refined the UI with conversation filters, responsive search panel, image zoom and clearer cards. | Preserved desktop/mobile history and media behavior. |
| 8 | Renamed to Whats Bayz and returned to a WhatsApp-inspired green theme. | Product naming and colors reflect the user's final preference. |
| 9 | Fixed false attachment cards on plain-text messages containing media metadata. | Explicit attachment classification belongs in the API. |
| 10 | Copied source to the current project; added importer, private `store/`, filtered manifest and named SQLite snapshots. Initialized a local Git repository. | The app no longer depends on a Desktop backup. Store remains untracked. |
| 11 | Verified imported files, database integrity, independent copies, permissions and Git exclusion. | The store is self-contained. |
| 12 | Deleted approved old viewer/backup/iMazing directories and temporary browser tooling. Reran integration tests. | Only this project's task data remains; do not assume a recoverable original exists. |
| 13 | Added contributor instructions, retrospective ADRs and this development guide. | Future decisions and work can be continued with context. |

## Validation baseline

- 10 integration tests in `test_viewer.py`, requiring the populated local store.
- Test areas: earliest/forward/backward history, name fallback, available media/ranges, plain-text false-attachment regression, project-local storage, whole-chat search, result paging, literal search and cross-chat jump rejection.
- Migration checks: manifest entries had local files with matching sizes, independent file inodes, private permissions, SQLite `quick_check` and ignored store paths.
- Prior temporary Chrome checks: UI branding/theme, scrolling, false-card regression, search, visible result targets and mobile layout.
- No committed browser automation, synthetic fixture suite, public CI or automated importer recovery exists yet.

Repeat tests when changing behavior; do not interpret this history as proof that a future change was tested.

## Proposed future development sequence

These are options for future work, **not approved or implemented features**. Reconfirm priorities before starting.

1. **Protect data before changing it.** Confirm a secure independent backup of `store/`, inspect Git exclusion and agree on recovery steps. Do not modify the live chat DB for experimentation.
2. **Create deterministic synthetic fixtures.** Invent small databases/media covering equal sort keys, null fields, Unicode queries, optional contact DBs, contacts/locations, plain metadata, missing media and byte ranges. Separate these from optional private-store integration tests.
3. **Make browser regressions repeatable.** Add an explicitly approved development-only harness for desktop/mobile scrolling, stale search requests, jump targets, media previews and keyboard/accessibility behavior. Screenshots must not contain private data in tracked output.
4. **Profile bottlenecks before optimizing.** Measure search scans/counts, chat listing and DOM growth using safe aggregate timing. If needed, propose an ADR for a separate ignored search index, caching or windowed rendering. Preserve search semantics, history cursors and scroll anchors.
5. **Harden import and recovery.** Add fixture-based importer tests, snapshot-aware space estimation, verified-source checks, resumable/staged imports and clear failure recovery. Do not implement replacement/migration of the current store without explicit approval.
6. **Improve schema compatibility and message coverage.** Validate optional tables/columns and new WhatsApp versions; add well-tested system messages, additional attachment kinds and identity cases. Avoid inventing phone numbers from opaque IDs.
7. **Refactor static assets if useful.** Separate CSS/JavaScript from `index.html` without adding a framework by default. Adjust the server's static-file allowlist and CSP deliberately; add tests before changing serving behavior.
8. **Review security before deployment changes.** Any LAN/public access, authentication, encryption, telemetry, cloud sync or package/toolchain addition needs an approved design and ADR. Current localhost behavior is the baseline.

## Workflow for the next change

1. Read [AGENTS.md](../AGENTS.md), the [ADR index](adr/README.md), and current code; inspect Git status.
2. Agree on scope and acceptance criteria. Distinguish source-only changes from private-data operations.
3. Reproduce safely and add regression coverage.
4. Implement a narrow change; validate API and relevant browser paths.
5. Update user docs and add/supersede an ADR for a material architectural change.
6. Verify private data remains ignored, summarize actual tests and obtain user feedback.

Never clean up, overwrite or force-stage `store/` as part of ordinary development.
