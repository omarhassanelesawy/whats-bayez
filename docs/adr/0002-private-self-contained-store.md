# ADR 0002: Private project-local store

- **Date:** 2026-10-06
- **Status:** Accepted (retrospective)

## Context

The original viewer read data from a Desktop backup. The user requested a portable project under `~/workdir/dev/whats-bayz`, with all necessary data inside a Git-ignored store. The old backups and task artifacts were subsequently deleted with explicit approval.

## Decision

All runtime data resides in project-relative `store/`:

- Named SQLite snapshots: `ChatStorage.sqlite`, optional `AddressBook.sqlite`, `LID.sqlite` and `BackedUpStorageDatabase.sqlite`.
- A filtered `Manifest.db` with related file mappings only.
- Related raw backup files under `00/` through `ff/`, preserving their file IDs.

`import_backup.py` accepts an already-decrypted Finder backup, selects available WhatsApp and AddressBook files, and refuses to overwrite a nonempty store. It creates independent copies using macOS APFS clone support where available, otherwise normal file copying. It never hard-links or symlinks original backup data. Named snapshots use SQLite backup with available WAL/SHM companions.

Use a `.import-incomplete` marker until all import steps finish. The viewer rejects incomplete imports. Imported directories/files are created with private permissions (`0700`/`0600`). The importer is separate from the read-only runtime.

Ignore `/store/` in Git. Serve queries with SQLite `mode=ro`; do not fall back to an external Desktop path.

## Alternatives

- **External paths or symlinks:** less copying, but not self-contained and breaks after source cleanup.
- **Hard links:** data ownership becomes coupled to the source; not acceptable for independent copies.
- **Data tracked by Git:** exposes private decrypted content and produces an oversized repository.
- **Copy the entire iPhone backup:** unnecessary for this viewer; includes unrelated apps and sensitive metadata.

## Consequences

The repository works independently of the deleted originals. The imported store contains sensitive plaintext and must be protected separately; `.gitignore` is not encryption or protection against forced staging or other uploads. APFS clones share physical blocks through copy-on-write, while remaining independent files.

There is no implemented import resume/recovery or automated store upgrade. A failed nonempty import requires a deliberate recovery plan, not deleting its marker or overwriting data. Free-space estimates currently do not precisely model every named snapshot's additional allocation.

Treat the current store as the only remaining task copy unless another backup is explicitly confirmed. Back it up securely before any approved data transformation.

## Validation

The migration verified every filtered manifest entry had a local file with matching size, checked independent inodes, ran SQLite `quick_check`, checked store permissions and confirmed Git ignores data. These were migration checks, not a recurring automated integrity job. The integration suite validates project-local paths and runs without the old backups.
