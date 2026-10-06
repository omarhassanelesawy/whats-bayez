# Whats Bayz

<img src="logo.svg" alt="Whats Bayz logo" width="64" height="64">

A private, local, read-only viewer for WhatsApp conversations from **your own decrypted iPhone backup**. Browse history, search chats and open backed-up attachments. Python standard library and vanilla browser APIs only—no runtime packages, account login or cloud services.

**This is not a live messaging client or a backup decryption tool.** Use only backups you own or are authorized to access.

## Requirements

- Python **3.10 or newer**, with the standard `sqlite3` module.
- A modern browser. Chrome desktop/mobile layouts have been checked.
- A **decrypted or unencrypted Finder-format iPhone backup**, containing a readable `Manifest.db` and WhatsApp `ChatStorage.sqlite` among its hashed files.
- Enough disk space for an independent copy of the related WhatsApp data, plus at least 512 MiB headroom. Large media collections may require many GiB.

macOS has been tested. Windows and Linux have not been validated end-to-end; commands below describe intended Python usage, not a compatibility guarantee. WhatsApp database schemas vary by version, so not every iPhone backup is guaranteed to work.

## Quick start: your own backup

### 1. Get the source

Download or clone this repository into a new folder. Open Terminal in that folder:

```bash
cd "/path/to/whats-bayz"
python3 --version
```

No `pip install`, Node.js, `.env` or configuration file is needed. Keep backup folders outside this source folder until imported.

### 2. Prepare a readable backup

Create an iPhone backup using Finder on macOS, or obtain an already decrypted Finder-format copy through your own backup workflow. If the backup is encrypted, decrypt it **outside Whats Bayz** first. An encrypted `Manifest.db` cannot be imported directly; knowing its password is not enough for this app.

Select the **individual backup root**, not its parent `MobileSync/Backup` directory. Its layout should resemble:

```text
your-decrypted-backup/
  Manifest.db
  00/
  01/
  ...
  ff/
```

Hashed filenames are normal. Do not rename them. A WhatsApp text export, iCloud account, or standalone chat database is not a supported import source.

### 3. Import into an empty installation

Replace the example path with your backup folder. Quotes handle spaces in paths:

```bash
python3 import_backup.py "/path/to/your-decrypted-backup"
```

Wait for **`Import complete`** before starting the viewer. The importer copies available WhatsApp-related files and optional iPhone contacts into project-local `store/`. Source files remain unchanged; no links back to the original backup are created. Available SQLite write-ahead logs are included in named snapshots.

**The importer refuses to overwrite a nonempty `store/`.** For another person, another backup, or a refreshed snapshot, use a separate fresh copy of the source project. Do not delete an existing store to make room for a new import. Keep an independent, secure backup of your data.

### 4. Start the viewer

```bash
python3 server.py
```

Open **http://127.0.0.1:8765** on the same computer. Stop with **Control-C**.

After backend changes, stop and restart the server. After UI changes, hard-refresh the browser: **Command-Shift-R** on macOS Chrome or **Ctrl-Shift-R** on Windows/Linux Chrome. A stale favicon may require closing and reopening the tab.

## Configuration

Configuration uses command-line arguments, not private paths committed to source:

| Setting | How to configure | Default |
| --- | --- | --- |
| Input backup folder | `python3 import_backup.py "/your/backup/path"` | Required for one-time import |
| Local HTTP port | `python3 server.py --port 8877` | `8765` |
| Private data location | Automatically relative to these scripts | `store/` beside the source files |
| Listening address | Intentionally not configurable | `127.0.0.1` only |

For a custom port, open the matching URL, such as **http://127.0.0.1:8877**. Each separate installation can use a different port. The port must be between `1` and `65535`.

Command help:

```bash
python3 import_backup.py --help
python3 server.py --help
```

On Windows, if Python is installed through its launcher, use `py -3` instead of `python3`, for example:

```powershell
py -3 import_backup.py "C:\Backups\my-decrypted-backup"
py -3 server.py --port 8877
```

The Windows workflow remains unverified. File permission behavior differs across operating systems.

## Features and limits

- All, Groups and Archived conversation filters; original green WB branding and tab icon.
- **Go to start**, **Latest**, and bidirectional paging through all backed-up history.
- Per-chat search covers the entire conversation, not just loaded messages: text, captions, contact-card names and original sender names. **Cmd+F / Ctrl+F** opens search; results jump to message context.
- Photos, video, audio and document downloads when attachment files exist. Click photos to zoom.
- Group sender labels use member identities rather than the group identifier.
- Click sender names in message cards or search results, or a **direct-chat title**, for contact details. Close with Escape, the close button or the backdrop. Sidebar names open conversations; a group title is not an individual contact.
- Names and numbers come from imported contacts, WhatsApp mappings and unambiguous incoming-message links to phone-addressed direct conversations. Conflicting links are ignored; names alone never establish a phone mapping.

**“Phone number not resolved from backup”** means the viewer could not link that sender to a number. It does not prove the number is absent everywhere in the backup. Opaque LIDs are never displayed as invented phone numbers.

Optional contact databases may be absent. Some names, message types and phone identities may remain unresolved. Actual missing attachments are marked; ordinary text with media metadata is not treated as a missing file. Deleted or absent media cannot be recovered by the viewer. HEIC, OPUS and other formats depend on browser codec support; download to open in a compatible application when needed.

## Privacy and private store

```text
store/                              # Git-ignored, sensitive data
  ChatStorage.sqlite                # Self-contained chat snapshot
  AddressBook.sqlite                # Optional iPhone contacts
  LID.sqlite                        # Optional identifier mappings
  BackedUpStorageDatabase.sqlite    # Optional WhatsApp push names
  Manifest.db                       # Related file mappings only
  00/ ... ff/                       # Hashed WhatsApp files/media
```

Runtime reads databases in SQLite read-only mode, binds to loopback only and does not upload chat data. No external fonts, CDNs, APIs or analytics are used. Media/data responses are not cached; static responses also use `no-store`.

**The store contains decrypted messages, contacts and media.** Protect it with your operating system's security and encrypted storage. `.gitignore` prevents normal Git staging; it does not encrypt data or prevent manual uploads. Never force-add `store/`, share a populated project folder, or attach private databases/screenshots to issues. Share source code only.

There is no authentication or TLS. Do not expose the server through port forwarding, a tunnel, a reverse proxy or a LAN/public listening address. Loopback is a deployment boundary, not protection against other software running on your computer.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `python3` not found | Install Python 3.10+; on Windows try `py -3`. |
| Source must contain `Manifest.db` | Choose the individual decrypted backup root, not its parent folder or a text export. |
| Manifest is not a database / encrypted backup | Decrypt externally first; Whats Bayz cannot decrypt it. A damaged manifest can also produce SQLite errors. |
| WhatsApp `ChatStorage.sqlite` missing | Backup must contain WhatsApp's shared-container database and its referenced hashed file. Different schema/layouts may need compatibility work. |
| `store/ is not empty` | Import into a separate fresh source installation. Preserve existing data. |
| Import interrupted / `.import-incomplete` exists | Preserve the partial store and source backup. Do not remove the marker to bypass the guard. Retry in a separate fresh installation; automatic resume is not supported. |
| Insufficient free space | Use a location with more free disk space; import checks logical size even if macOS copy-on-write might save space. |
| Address already in use | Stop your old viewer or select another port with `--port 8877`. Do not stop an unrelated process. |
| Browser cannot connect | Keep the terminal/server running, use `127.0.0.1` and the selected port on the same computer. |
| Missing names or numbers | Optional contact data or identity links may be absent; unresolved identifiers are not phone numbers. |
| Contact popup does not open | Click the sender name above an incoming message or a direct-chat title. Restart after server changes and hard-refresh after UI changes. |
| Media absent / preview unsupported | File may be absent from the backup, or browser may lack codec support. Try download if the file is available. |

## Tests

Configuration tests do **not** require a private backup:

```bash
python3 -m unittest -v test_config.py
```

After importing a populated store with suitable messages and attachments:

```bash
python3 -m unittest -v test_config.py test_viewer.py
```

Integration tests read local private data; a fresh clone cannot run them without a suitable import. They cover pagination, earliest history, attachments/byte ranges, false-attachment regression, names, group sender identities/numbers, direct-chat LID links, static-file restrictions, full-chat search and context jumps. Browser checks are documented in development notes; no browser automation dependency is required or committed.

## Development documentation

- [AGENTS.md](AGENTS.md): contributor rules and data-safety constraints.
- [Architecture decisions](docs/adr/README.md): accepted decisions and consequences.
- [Development history](docs/DEVELOPMENT.md): validation history and proposed future work.
