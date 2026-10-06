#!/usr/bin/env python3
"""Local-only WhatsApp backup viewer. Reads the database without modifying it."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json
import sqlite3
import mimetypes
import re
import hashlib
import argparse
from functools import lru_cache

ROOT = Path(__file__).resolve().parent
BACKUP = ROOT / 'store'
DB = BACKUP / 'ChatStorage.sqlite'
DOMAIN = "AppDomainGroup-group.net.whatsapp.WhatsApp.shared"


def readonly(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)


@lru_cache(maxsize=1)
def contacts():
    by_id, by_number, by_jid, lid_numbers = {}, {}, {}, {}
    rows = [('AddressBook.sqlite','Library/AddressBook/AddressBook.sqlitedb'),
            ('LID.sqlite','LID.sqlite'),
            ('BackedUpStorageDatabase.sqlite','BackedUpStorageDB/BackedUpStorageDatabase.sqlite')]
    for filename, path in rows:
        file = BACKUP / filename
        if not file.is_file():
            continue
        with readonly(file) as con:
            if path.endswith('AddressBook.sqlitedb'):
                for uid, first, middle, last, org, display in con.execute('SELECT ROWID,First,Middle,Last,Organization,DisplayName FROM ABPerson'):
                    name = display or ' '.join(v for v in (first,middle,last) if v) or org
                    if name:
                        by_id[uid] = name
                for uid, number in con.execute('SELECT record_id,value FROM ABMultiValue WHERE property=3'):
                    digits = re.sub(r'\D', '', number or '')
                    if digits and uid in by_id:
                        by_number[digits] = by_id[uid]
            elif path == 'LID.sqlite':
                for lid, number in con.execute('SELECT ZLID,ZPHONENUMBER FROM ZWAPHONENUMBERLIDPAIR'):
                    if lid and number:
                        lid_numbers[lid] = number
                        lid_numbers[lid.split('@')[0]] = number
                for lid, name in con.execute('SELECT ZLID,ZDISPLAYNAME FROM ZWALIDPROPERTIES'):
                    if lid and name:
                        by_jid[lid] = name
            else:
                for jid, name in con.execute('SELECT jid,push_name FROM profile_push_name'):
                    if name:
                        by_jid[jid] = name
    with database() as con:
        for jid, name in con.execute('SELECT ZJID,ZPUSHNAME FROM ZWAPROFILEPUSHNAME'):
            if name:
                by_jid.setdefault(jid, name)
        # Incoming messages in a phone-addressed direct chat can use a LID.
        # The conversation supplies the peer's phone identity, not a name guess.
        pairs = con.execute('''SELECT DISTINCT m.ZFROMJID,s.ZCONTACTJID
            FROM ZWAMESSAGE m JOIN ZWACHATSESSION s ON s.Z_PK=m.ZCHATSESSION
            WHERE m.ZISFROMME=0 AND m.ZFROMJID LIKE '%@lid'
            AND (s.ZCONTACTJID LIKE '%@s.whatsapp.net' OR s.ZCONTACTJID LIKE '%@c.us')''')
        for lid, number in direct_lid_numbers(pairs).items():
            lid_numbers.setdefault(lid, number)
            lid_numbers.setdefault(lid.split('@')[0], number)
    return by_id, by_number, by_jid, lid_numbers


def direct_lid_numbers(pairs):
    candidates = {}
    for lid, phone_jid in pairs:
        number = phone_jid.split('@')[0]
        if re.fullmatch(r'\d+', number):
            candidates.setdefault(lid, set()).add(number)
    # Conflicting evidence must not silently choose someone else's number.
    return {lid: next(iter(numbers)) for lid, numbers in candidates.items() if len(numbers) == 1}


def readable(value):
    value = (value or '').strip()
    # Contact identifiers may be serialized protobuf values, not display names.
    return value if value and not re.fullmatch(r'[A-Za-z0-9+/]{20,}={0,2}', value) else ''


def identity(jid, partner='', abid=None):
    by_id, by_number, by_jid, lids = contacts()
    jid = jid or ''
    number = lids.get(jid, lids.get(jid.split('@')[0], ''))
    if not number and jid.endswith(('@s.whatsapp.net', '@c.us')):
        number = jid.split('@')[0]
    digits = re.sub(r'\D', '', number)
    name = (by_id.get(abid) or by_number.get(digits) or readable(partner)
            or readable(by_jid.get(jid)) or (('+' + digits) if digits else ''))
    if not name:
        name = 'Group chat' if jid.endswith('@g.us') else 'Unknown contact'
    return name, ('+' + digits) if digits else ''


@lru_cache(maxsize=8192)
def media_file(relative):
    if not relative:
        return None
    relative = relative.lstrip('/')
    candidates = [relative, 'Message/' + relative]
    if not relative.startswith('Media/'):
        candidates.extend(['Media/' + relative, 'Message/Media/' + relative])
    for path in candidates:
        for domain in (DOMAIN, 'AppDomain-net.whatsapp.WhatsApp'):
            file_id = hashlib.sha1(f'{domain}-{path}'.encode()).hexdigest()
            file = BACKUP / file_id[:2] / file_id
            if file.is_file():
                return file
    return None


def database():
    if (BACKUP / '.import-incomplete').exists():
        raise ValueError('Store import is still incomplete. Wait for import_backup.py to finish.')
    if not DB.is_file():
        raise FileNotFoundError(f"WhatsApp database not found: {DB}")
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Avoid logging private chat content or query parameters.

    def send_json(self, value, status=200):
        data = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Search requests can be canceled while the user types.

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/chats":
            self.chats(parse_qs(parsed.query).get("q", [""])[0])
        elif parsed.path == "/api/messages":
            self.messages(parse_qs(parsed.query))
        elif parsed.path == "/api/search":
            self.search_messages(parse_qs(parsed.query))
        elif parsed.path == "/api/status":
            self.send_json({"ready": DB.is_file(), "database": DB.name})
        elif parsed.path == "/api/media":
            self.media(parse_qs(parsed.query))
        else:
            static = {'/': 'index.html', '/index.html': 'index.html', '/logo.svg': 'logo.svg'}
            path = ROOT / static.get(parsed.path, '')
            if parsed.path not in static or not path.is_file() or ROOT not in path.resolve().parents:
                self.send_error(404)
                return
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml" if path.suffix == '.svg' else "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self'; media-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

    def chats(self, search):
        try:
            con = database()
            con.row_factory = sqlite3.Row
            sql = """SELECT s.Z_PK id, s.ZPARTNERNAME name, s.ZCONTACTABID abid,
                       s.ZCONTACTJID jid, COALESCE(NULLIF(last.ZTEXT,''),s.ZLASTMESSAGETEXT) preview,
                       last.ZMESSAGETYPE preview_type,
                      s.ZLASTMESSAGEDATE date, s.ZUNREADCOUNT unread,
                      s.ZARCHIVED archived, s.ZHIDDEN hidden, s.ZREMOVED removed,
                      (SELECT COUNT(*) FROM ZWAMESSAGE m WHERE m.ZCHATSESSION=s.Z_PK) total
                    FROM ZWACHATSESSION s LEFT JOIN ZWAMESSAGE last ON last.Z_PK=s.ZLASTMESSAGE
                    ORDER BY COALESCE(s.ZLASTMESSAGEDATE,0) DESC"""
            result = []
            needle = search.casefold().strip()
            for row in con.execute(sql):
                item = dict(row)
                item['name'], item['number'] = identity(item['jid'], item['name'], item.pop('abid'))
                preview_type = item.pop('preview_type')
                item['preview'] = readable(item['preview']) or ({1:'Photo',2:'Video',3:'Audio',4:'Contact',5:'Location',8:'Document',11:'GIF',15:'Sticker'}.get(preview_type,''))
                if not item['total']:
                    continue
                if needle and not any(needle in str(item.get(field) or '').casefold() for field in ('name', 'jid', 'number', 'preview')):
                    continue
                result.append(item)
            con.close()
            self.send_json(result)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def messages(self, query):
        try:
            chat = int(query.get("chat", ["0"])[0])
            limit = min(max(int(query.get("limit", ["100"])[0]), 1), 250)
            before_id = query.get("before_id", [None])[0]
            after_id = query.get("after_id", [None])[0]
            start = query.get('start', ['0'])[0] == '1'
            sort_cursor = query.get('sort', [None])[0]
            ascending = start or after_id is not None
            con = database()
            con.row_factory = sqlite3.Row
            where = "m.ZCHATSESSION=?"
            args = [chat]
            cursor_id = after_id if ascending else before_id
            if cursor_id is not None and sort_cursor is not None:
                op = '>' if ascending else '<'
                where += f" AND (COALESCE(m.ZSORT,0) {op} ? OR (COALESCE(m.ZSORT,0)=? AND m.Z_PK {op} ?))"
                args += [int(sort_cursor), int(sort_cursor), int(cursor_id)]
            args.append(limit + 1)
            direction = 'ASC' if ascending else 'DESC'
            select = """SELECT m.Z_PK id, m.ZMESSAGEDATE date, m.ZTEXT text,
                          m.ZISFROMME outgoing, m.ZPUSHNAME sender,
                          COALESCE(NULLIF(g.ZMEMBERJID,''),m.ZFROMJID) from_jid,
                          g.ZCONTACTNAME member_name, g.ZCONTACTABID sender_abid,
                         COALESCE(m.ZSORT,0) sort,
                         m.ZMESSAGETYPE type, m.ZSTARRED starred, m.ZMEDIAITEM media,
                         a.ZMEDIALOCALPATH path, a.ZTHUMBNAILLOCALPATH thumbnail,
                          a.ZTITLE title, a.ZVCARDSTRING vcard, a.ZVCARDNAME contact_name,
                          a.ZLATITUDE latitude, a.ZLONGITUDE longitude
                        FROM ZWAMESSAGE m LEFT JOIN ZWAMEDIAITEM a ON a.Z_PK=m.ZMEDIAITEM
                        LEFT JOIN ZWAGROUPMEMBER g ON g.Z_PK=m.ZGROUPMEMBER"""
            around = query.get('around', [None])[0]
            if around is not None:
                target = con.execute('SELECT Z_PK,COALESCE(ZSORT,0) FROM ZWAMESSAGE WHERE Z_PK=? AND ZCHATSESSION=?', (int(around),chat)).fetchone()
                if target is None:
                    con.close()
                    self.send_json({'error': 'Message not found in this chat'}, 404)
                    return
                half = max(1, limit // 2)
                sides = []
                for op, order in (('<','DESC'), ('>','ASC')):
                    sides.append(con.execute(f'''SELECT Z_PK FROM ZWAMESSAGE
                        WHERE ZCHATSESSION=? AND (COALESCE(ZSORT,0) {op} ? OR (COALESCE(ZSORT,0)=? AND Z_PK {op} ?))
                        ORDER BY COALESCE(ZSORT,0) {order},Z_PK {order} LIMIT ?''',
                        (chat,target[1],target[1],target[0],half+1)).fetchall())
                ids = [target[0]] + [r[0] for side in sides for r in side[:half]]
                rows = con.execute(select + f" WHERE m.Z_PK IN ({','.join('?' for _ in ids)}) ORDER BY COALESCE(m.ZSORT,0),m.Z_PK", ids).fetchall()
                older, newer = len(sides[0]) > half, len(sides[1]) > half
            else:
                rows = con.execute(select + f" WHERE {where} ORDER BY COALESCE(m.ZSORT,0) {direction}, m.Z_PK {direction} LIMIT ?", args).fetchall()
                more = len(rows) > limit
                rows = rows[:limit]
                rows = rows if ascending else reversed(rows)
                older, newer = (more if not ascending else not start), (more if ascending else bool(before_id))
            con.close()
            messages = [dict(r) for r in rows]
            for m in messages:
                m['sender'], m['sender_number'] = identity(m['from_jid'], readable(m.pop('member_name')) or m['sender'], m.pop('sender_abid'))
                file = media_file(m['path'])
                if not m['thumbnail'] and m['path']:
                    fallback = str(Path(m['path']).with_suffix('.thumb'))
                    if media_file(fallback):
                        m['thumbnail'] = fallback
                thumb = media_file(m['thumbnail'])
                m['attachment'] = None
                # Plain-text messages also carry media metadata (e.g. link previews).
                # A metadata row alone is not evidence of an attached file.
                file_types = {1, 2, 3, 8, 11, 15, 20, 23, 26, 27, 38, 39, 42, 43, 54}
                if m['media'] and (m['path'] or m['type'] in file_types):
                    filename = Path(m['path'] or '').name or m['title'] or 'Attachment'
                    m['attachment'] = {'kind': 'file', 'available': bool(file), 'thumbnail': bool(thumb), 'name': filename,
                                       'mime': mimetypes.guess_type(filename)[0] or 'application/octet-stream'}
                elif m['media'] and m['type'] in {4,14} and m['vcard']:
                    m['attachment'] = {'kind': 'contact', 'name': m['contact_name'] or 'Contact'}
                elif m['media'] and m['type'] == 5 and m['latitude'] is not None and m['longitude'] is not None:
                    m['attachment'] = {'kind': 'location', 'name': m['title'] or 'Shared location'}
            self.send_json({"messages": messages, "has_older": older, "has_newer": newer})
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def search_messages(self, query):
        try:
            chat = int(query.get('chat', ['0'])[0])
            needle = query.get('q', [''])[0].strip().casefold()
            offset = max(0, int(query.get('offset', ['0'])[0]))
            limit = min(100, max(1, int(query.get('limit', ['50'])[0])))
            if not needle:
                self.send_json({'results': [], 'total': 0, 'has_more': False})
                return
            # Literal Unicode-aware substring search, not SQL wildcards or regex.
            with database() as con:
                con.row_factory = sqlite3.Row
                con.create_function('casefold', 1, lambda text: (text or '').casefold(), deterministic=True)
                join = ''' FROM ZWAMESSAGE m LEFT JOIN ZWAMEDIAITEM a ON a.Z_PK=m.ZMEDIAITEM
                    LEFT JOIN ZWAGROUPMEMBER g ON g.Z_PK=m.ZGROUPMEMBER '''
                where = '''WHERE m.ZCHATSESSION=? AND (
                    instr(casefold(m.ZTEXT),?)>0 OR instr(casefold(a.ZTITLE),?)>0
                    OR instr(casefold(a.ZVCARDNAME),?)>0 OR instr(casefold(m.ZPUSHNAME),?)>0)'''
                params = [chat] + [needle] * 4
                total = con.execute('SELECT COUNT(*)' + join + where, params).fetchone()[0]
                rows = con.execute('''SELECT m.Z_PK id, m.ZMESSAGEDATE date,
                    COALESCE(m.ZSORT,0) sort,m.ZTEXT text,m.ZISFROMME outgoing,
                    m.ZPUSHNAME sender,COALESCE(NULLIF(g.ZMEMBERJID,''),m.ZFROMJID) from_jid,
                    g.ZCONTACTNAME member_name,g.ZCONTACTABID sender_abid,a.ZTITLE title,
                    a.ZVCARDNAME contact_name,m.ZMEDIAITEM media''' + join + where +
                    ' ORDER BY COALESCE(m.ZSORT,0) DESC,m.Z_PK DESC LIMIT ? OFFSET ?',
                    params + [limit, offset]).fetchall()
            results = [dict(row) for row in rows]
            for item in results:
                item['sender'], item['sender_number'] = identity(item['from_jid'], readable(item.pop('member_name')) or item['sender'], item.pop('sender_abid'))
            self.send_json({'results': results, 'total': total, 'has_more': offset + len(results) < total})
        except ValueError:
            self.send_json({'error': 'Invalid search parameters'}, 400)
        except Exception as exc:
            self.send_json({'error': str(exc)}, 500)

    def media(self, query):
        try:
            message_id = int(query.get('message', ['0'])[0])
            thumbnail = query.get('thumbnail', ['0'])[0] == '1'
            with database() as con:
                row = con.execute('SELECT a.ZMEDIALOCALPATH,a.ZTHUMBNAILLOCALPATH FROM ZWAMESSAGE m JOIN ZWAMEDIAITEM a ON a.Z_PK=m.ZMEDIAITEM WHERE m.Z_PK=?', (message_id,)).fetchone()
            relative = row[1 if thumbnail else 0] if row else None
            if thumbnail and row and not relative and row[0]:
                relative = str(Path(row[0]).with_suffix('.thumb'))
            file = media_file(relative)
            if not file:
                self.send_error(404, 'Attachment not present in backup')
                return
            size = file.stat().st_size
            mime = mimetypes.guess_type(relative)[0]
            if not mime or relative.endswith('.thumb'):
                with file.open('rb') as stream:
                    signature = stream.read(16)
                if signature.startswith(b'\xff\xd8\xff'):
                    mime = 'image/jpeg'
                elif signature.startswith(b'\x89PNG\r\n\x1a\n'):
                    mime = 'image/png'
                elif signature.startswith(b'RIFF') and signature[8:12] == b'WEBP':
                    mime = 'image/webp'
            start, end = 0, size - 1
            range_header = self.headers.get('Range')
            if range_header:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', range_header)
                if not match or not any(match.groups()):
                    self.send_error(416)
                    return
                a,b = match.groups()
                start = int(a) if a else max(0, size-int(b))
                end = min(int(b),size-1) if a and b else size-1
                if start > end or start >= size:
                    self.send_error(416)
                    return
            self.send_response(206 if range_header else 200)
            self.send_header('Content-Type', mime or 'application/octet-stream')
            self.send_header('Content-Disposition', 'attachment' if query.get('download') else 'inline')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "sandbox; default-src 'none'")
            self.send_header('Accept-Ranges', 'bytes')
            if range_header:
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.send_header('Content-Length', str(end-start+1))
            self.end_headers()
            with file.open('rb') as stream:
                stream.seek(start)
                remaining = end-start+1
                while remaining:
                    chunk = stream.read(min(65536,remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except ValueError:
            self.send_error(400)


def port_number(value):
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError('Port must be an integer from 1 to 65535.')
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError('Port must be an integer from 1 to 65535.')
    return port


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=port_number, default=8765,
                        help='Local HTTP port (default: 8765); always binds to 127.0.0.1')
    args = parser.parse_args(argv)
    try:
        httpd = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError as error:
        parser.exit(1, f'Could not bind to 127.0.0.1:{args.port}: {error}. Try another --port.\n')
    with httpd:
        print(f'Whats Bayz: http://127.0.0.1:{args.port}  (local only; DB: {DB})')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
