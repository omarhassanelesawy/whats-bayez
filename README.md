# Whats Bayz

Private, WhatsApp-inspired viewer for chats and media from a **decrypted Finder iPhone backup**. Python 3 standard library only; no runtime packages or cloud services.

## Start

```bash
cd ~/workdir/dev/whats-bayz
python3 server.py
```

Open **http://127.0.0.1:8765**. Stop with Control-C. Stop any old viewer on that port first. After changing files, restart the server and refresh the browser with Command-Shift-R.

## Private data store

All backup data lives inside `store/`, which is excluded by `.gitignore`:

```text
store/
  ChatStorage.sqlite                 # Self-contained chat database
  AddressBook.sqlite                 # iPhone contact names/numbers, if present
  LID.sqlite                         # WhatsApp identifier mappings, if present
  BackedUpStorageDatabase.sqlite      # WhatsApp push names, if present
  Manifest.db                        # Only related backup file mappings
  00/ … ff/                          # WhatsApp files/media under backup IDs
```

The app reads only this store, not the original Desktop backup. Imported files are independent copies, never symlinks or hard links. macOS may use APFS copy-on-write clones to save disk space. Named SQLite snapshots include any available write-ahead log. Original backups remain untouched.

To populate a **fresh, empty** store from a decrypted backup:

```bash
python3 import_backup.py "$HOME/Desktop/whatsapp-backup-decrypted"
```

Importer copies available WhatsApp files and AddressBook data only. It does not decrypt encrypted backups. It refuses to overwrite a nonempty store. `.import-incomplete` prevents the viewer from using a partially imported store.

**Store contains private, decrypted conversations, contacts and media.** Keep it private and encrypted at rest where possible. `.gitignore` prevents normal Git staging, not manual `git add -f`, copying, or uploads. Never force-add `store/`. Integration tests also read this private data.

## Features

- All, Groups and Archived conversation filters.
- Green WhatsApp-inspired palette with outgoing/incoming message cards.
- **Go to start** opens the earliest backed-up message. Scroll or use history buttons to load older/newer messages. **Latest** returns to recent history.
- Per-chat search covers the entire backed-up conversation, including unloaded messages, captions, contact-card names and original sender names. Click a result to jump into surrounding context. Cmd+F / Ctrl+F opens search.
- Photos, video, audio and document downloads when files exist in the backup. Click photos to zoom.
- Contact names/numbers from iPhone contacts and WhatsApp mappings where available.

Plain-text media metadata is not displayed as an attachment. Actual missing attachment files are explicitly marked. Deleted or absent media cannot be recovered from this backup. Some formats (HEIC, OPUS, etc.) depend on browser codec support; download to open in a compatible app if needed.

Server binds only to `127.0.0.1`, reads databases in read-only mode, and does not upload chat data. This is a read-only backup viewer, not a live WhatsApp client.

## Tests

After importing the store:

```bash
python3 -m unittest -v test_viewer.py
```

Tests cover pagination, earliest history, attachments and byte ranges, false-attachment regression, names, full-chat search, search pagination, result jumps and project-local store configuration.

## Development documentation

- [AGENTS.md](AGENTS.md): contributor/agent rules, privacy constraints and development workflow.
- [Architecture decisions](docs/adr/README.md): accepted decisions, alternatives and consequences.
- [Development history and next steps](docs/DEVELOPMENT.md): completed work, validation baseline and proposed future sequence.
