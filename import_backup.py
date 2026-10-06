#!/usr/bin/env python3
"""Copy WhatsApp backup data into this project's private, gitignored store."""
import argparse
import ctypes
import os
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parent
STORE = ROOT / 'store'
CHAT_PATH = 'ChatStorage.sqlite'
CHAT_DOMAIN = 'AppDomainGroup-group.net.whatsapp.WhatsApp.shared'
RELATED = "flags=1 AND (domain LIKE '%whatsapp%' OR (domain='HomeDomain' AND relativePath LIKE 'Library/AddressBook/%'))"


def copy_private(source, destination):
    """Use independent copy-on-write files on macOS; never hard-link originals."""
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.exists():
        raise FileExistsError(f'Refusing to overwrite {destination}')
    cloned = False
    if sys.platform == 'darwin':
        libc = ctypes.CDLL(None, use_errno=True)
        clonefile = libc.clonefile
        clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
        clonefile.restype = ctypes.c_int
        cloned = clonefile(os.fsencode(source), os.fsencode(destination), 0) == 0
    if not cloned:
        shutil.copy2(source, destination)
    destination.chmod(0o600)


def import_backup(source):
    source = source.expanduser().resolve()
    if not (source / 'Manifest.db').is_file():
        raise ValueError('Source must be a decrypted Finder backup containing Manifest.db.')
    if STORE.exists() and any(STORE.iterdir()):
        raise FileExistsError('store/ is not empty. Import into a fresh project or preserve the existing store elsewhere first.')
    with sqlite3.connect(f'file:{source}/Manifest.db?mode=ro', uri=True) as con:
        rows = con.execute(f'SELECT fileID,domain,relativePath FROM Files WHERE {RELATED}').fetchall()
        chat = con.execute('SELECT fileID FROM Files WHERE domain=? AND relativePath=? AND flags=1', (CHAT_DOMAIN,CHAT_PATH)).fetchone()
    if not chat or not (source / chat[0][:2] / chat[0]).is_file():
        raise ValueError('Decrypted WhatsApp ChatStorage.sqlite is missing.')
    available = [(fid,domain,path) for fid,domain,path in rows if (source / fid[:2] / fid).is_file()]
    total_bytes = sum((source / fid[:2] / fid).stat().st_size for fid,_,_ in available)
    free = shutil.disk_usage(ROOT).free
    print(f'{len(available):,} related files, {total_bytes / 2**30:.2f} GiB logical size; {free / 2**30:.2f} GiB free.', flush=True)
    if total_bytes + 512 * 2**20 > free:
        raise ValueError('Insufficient free space for an independent copy of the WhatsApp store.')
    STORE.mkdir(mode=0o700, exist_ok=True)
    STORE.chmod(0o700)
    marker = STORE / '.import-incomplete'
    marker.write_text('Import is incomplete. Do not start the viewer yet.\n')
    marker.chmod(0o600)
    # Keep only related manifest mappings, not metadata for unrelated apps.
    manifest = STORE / 'Manifest.db'
    with sqlite3.connect(manifest) as con:
        con.execute('CREATE TABLE Files (fileID TEXT PRIMARY KEY, domain TEXT, relativePath TEXT, flags INTEGER)')
        con.executemany('INSERT INTO Files VALUES (?,?,?,1)', available)
        con.execute('CREATE INDEX files_domain_path ON Files(domain,relativePath)')
    manifest.chmod(0o600)
    for index, (fid,_,_) in enumerate(available, 1):
        copy_private(source / fid[:2] / fid, STORE / fid[:2] / fid)
        if index % 25000 == 0:
            print(f'Copied {index:,}/{len(available):,} files.', flush=True)
    # These are named snapshots for SQLite readers; raw backup IDs remain for media.
    named = {'ChatStorage.sqlite': (CHAT_DOMAIN,CHAT_PATH),
             'AddressBook.sqlite': ('HomeDomain','Library/AddressBook/AddressBook.sqlitedb'),
             'LID.sqlite': (CHAT_DOMAIN,'LID.sqlite'),
             'BackedUpStorageDatabase.sqlite': (CHAT_DOMAIN,'BackedUpStorageDB/BackedUpStorageDatabase.sqlite')}
    with sqlite3.connect(f'file:{manifest}?mode=ro', uri=True) as con:
        for filename, (domain,path) in named.items():
            row = con.execute('SELECT fileID FROM Files WHERE domain=? AND relativePath=?', (domain,path)).fetchone()
            if not row:
                continue
            raw = STORE / row[0][:2] / row[0]
            # SQLite backup includes any available WAL, yielding a self-contained file.
            for suffix in ('-wal','-shm'):
                sidecar = con.execute('SELECT fileID FROM Files WHERE domain=? AND relativePath=?', (domain,path+suffix)).fetchone()
                if sidecar:
                    copy_private(STORE / sidecar[0][:2] / sidecar[0], Path(str(raw)+suffix))
            target = STORE / filename
            with sqlite3.connect(f'file:{raw}?mode=ro', uri=True) as source_db, sqlite3.connect(target) as target_db:
                source_db.backup(target_db)
            target.chmod(0o600)
    marker.unlink()
    print(f'Import complete: {STORE}. Originals unchanged.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup', type=Path, help='Path to the decrypted Finder backup')
    args = parser.parse_args()
    try:
        import_backup(args.backup)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, f'Import failed: {error}\n')
