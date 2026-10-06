"""Read-only integration tests against the configured backup."""
import json
import threading
import unittest
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
import server


class ViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.chats = cls.get('/api/chats')
        cls.chat = max(cls.chats, key=lambda c: c['total'])['id']

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    @classmethod
    def get(cls, route):
        with urlopen(cls.base + route, timeout=120) as response:
            return json.load(response)

    def test_earliest_and_forward_pages(self):
        first = self.get(f'/api/messages?chat={self.chat}&start=1&limit=10')
        self.assertFalse(first['has_older'])
        cursor = first['messages'][-1]
        second = self.get(f"/api/messages?chat={self.chat}&after_id={cursor['id']}&sort={cursor['sort']}&limit=10")
        with server.database() as con:
            expected = con.execute('SELECT Z_PK FROM ZWAMESSAGE WHERE ZCHATSESSION=? ORDER BY COALESCE(ZSORT,0),Z_PK LIMIT 20', (self.chat,)).fetchall()
        self.assertEqual([m['id'] for m in first['messages'] + second['messages']], [r[0] for r in expected])

    def test_backward_pages(self):
        latest = self.get(f'/api/messages?chat={self.chat}&limit=10')
        self.assertFalse(latest['has_newer'])
        cursor = latest['messages'][0]
        previous = self.get(f"/api/messages?chat={self.chat}&before_id={cursor['id']}&sort={cursor['sort']}&limit=10")
        with server.database() as con:
            expected = con.execute('SELECT Z_PK FROM ZWAMESSAGE WHERE ZCHATSESSION=? ORDER BY COALESCE(ZSORT,0) DESC,Z_PK DESC LIMIT 20', (self.chat,)).fetchall()
        self.assertEqual([m['id'] for m in previous['messages'] + latest['messages']], [r[0] for r in reversed(expected)])

    def test_names(self):
        self.assertTrue(all(server.readable(c['name']) for c in self.chats))
        self.assertEqual(server.identity('123456789@s.whatsapp.net', 'CI2+iNYGIABIAZABAPABAtgC+InT8oiglwM=')[0], '+123456789')

    def test_direct_chat_resolves_lid_sender_number(self):
        with server.database() as con:
            row = con.execute('''SELECT m.Z_PK,m.ZCHATSESSION,m.ZFROMJID,s.ZCONTACTJID,m.ZTEXT
                FROM ZWAMESSAGE m JOIN ZWACHATSESSION s ON s.Z_PK=m.ZCHATSESSION
                WHERE m.ZISFROMME=0 AND m.ZFROMJID LIKE '%@lid'
                AND s.ZCONTACTJID LIKE '%@s.whatsapp.net'
                AND EXISTS (SELECT 1 FROM ZWAGROUPMEMBER g WHERE g.ZMEMBERJID=m.ZFROMJID)
                AND length(m.ZTEXT) BETWEEN 25 AND 90 LIMIT 1''').fetchone()
        self.assertIsNotNone(row)
        expected = '+' + row[3].split('@')[0]
        self.assertTrue(server.identity(row[2])[1] == expected)
        chat = next(c for c in self.chats if c['id'] == row[1])
        self.assertTrue(chat['number'] == expected)
        window = self.get(f'/api/messages?chat={row[1]}&around={row[0]}&limit=10')
        message = next(m for m in window['messages'] if m['id'] == row[0])
        self.assertTrue(message['sender_number'] == expected)
        results = self.get('/api/search?' + urlencode({'chat': row[1], 'q': row[4], 'limit': 100}))
        result = next(m for m in results['results'] if m['id'] == row[0])
        self.assertTrue(result['sender_number'] == expected)
        with server.database() as con:
            group = con.execute('''SELECT m.Z_PK,m.ZCHATSESSION FROM ZWAMESSAGE m
                JOIN ZWAGROUPMEMBER g ON g.Z_PK=m.ZGROUPMEMBER
                WHERE m.ZISFROMME=0 AND m.ZFROMJID LIKE '%@g.us'
                AND g.ZMEMBERJID=? LIMIT 1''', (row[2],)).fetchone()
        self.assertIsNotNone(group)
        window = self.get(f'/api/messages?chat={group[1]}&around={group[0]}&limit=10')
        message = next(m for m in window['messages'] if m['id'] == group[0])
        self.assertTrue(message['sender_number'] == expected)

    def test_direct_lid_mapping_rejects_conflicts(self):
        pairs = [('first@lid', '15550000001@s.whatsapp.net'),
                 ('first@lid', '15550000001@c.us'),
                 ('second@lid', '15550000002@s.whatsapp.net'),
                 ('second@lid', '15550000003@s.whatsapp.net'),
                 ('third@lid', 'opaque@s.whatsapp.net')]
        self.assertEqual(server.direct_lid_numbers(pairs), {'first@lid': '15550000001'})

    def test_plain_text_metadata_is_not_attachment(self):
        with server.database() as con:
            row = con.execute('''SELECT m.Z_PK,m.ZCHATSESSION FROM ZWAMESSAGE m
                JOIN ZWAMEDIAITEM a ON a.Z_PK=m.ZMEDIAITEM
                WHERE m.ZMESSAGETYPE=0 AND m.ZTEXT IS NOT NULL
                AND (a.ZMEDIALOCALPATH IS NULL OR a.ZMEDIALOCALPATH='') LIMIT 1''').fetchone()
        self.assertIsNotNone(row)
        window = self.get(f'/api/messages?chat={row[1]}&around={row[0]}&limit=10')
        message = next(m for m in window['messages'] if m['id'] == row[0])
        self.assertTrue(message['media'])
        self.assertIsNone(message['attachment'])
        self.assertTrue(message['text'])

    def test_group_sender_uses_member_identity(self):
        with server.database() as con:
            row = con.execute('''SELECT m.Z_PK,m.ZCHATSESSION,m.ZTEXT,
                g.ZMEMBERJID,g.ZCONTACTNAME,g.ZCONTACTABID,m.ZPUSHNAME
                FROM ZWAMESSAGE m JOIN ZWAGROUPMEMBER g ON g.Z_PK=m.ZGROUPMEMBER
                WHERE m.ZISFROMME=0 AND m.ZFROMJID LIKE '%@g.us'
                AND COALESCE(m.ZPUSHNAME,'')='' AND g.ZMEMBERJID NOT LIKE '%@g.us'
                AND length(m.ZTEXT) BETWEEN 25 AND 90 LIMIT 1''').fetchone()
        self.assertIsNotNone(row)
        expected, number = server.identity(row[3], server.readable(row[4]) or row[6], row[5])
        self.assertTrue(expected not in ('Group chat', 'Unknown contact'))
        window = self.get(f'/api/messages?chat={row[1]}&around={row[0]}&limit=10')
        message = next(m for m in window['messages'] if m['id'] == row[0])
        self.assertTrue(message['sender'] == expected)
        self.assertTrue(message['from_jid'] == row[3])
        self.assertTrue(message['sender_number'] == number)
        results = self.get('/api/search?' + urlencode({'chat': row[1], 'q': row[2], 'limit': 100}))
        result = next(m for m in results['results'] if m['id'] == row[0])
        self.assertTrue(result['sender'] == expected)
        self.assertTrue(result['from_jid'] == row[3])
        self.assertTrue(result['sender_number'] == number)

    def test_logo_and_static_allowlist(self):
        with urlopen(self.base + '/logo.svg?v=2') as response:
            self.assertEqual(response.headers.get_content_type(), 'image/svg+xml')
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            self.assertIn(b'<title>Whats Bayz</title>', response.read())
            self.assertIn("default-src 'self'", response.headers['Content-Security-Policy'])
        with urlopen(self.base + '/') as response:
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            self.assertIn(b'sizes="any" href="/logo.svg?v=2"', response.read())
        for path in ('/server.py', '/store/ChatStorage.sqlite', '/nested/index.html'):
            with self.assertRaises(HTTPError) as error:
                urlopen(self.base + path)
            self.assertEqual(error.exception.code, 404)

    def test_store_is_project_local(self):
        self.assertEqual(server.BACKUP, server.ROOT / 'store')
        self.assertEqual(server.DB, server.BACKUP / 'ChatStorage.sqlite')
        self.assertTrue(server.DB.is_file())
        self.assertFalse(server.DB.is_symlink())

    def test_attachment_ranges(self):
        with server.database() as con:
            rows = con.execute('SELECT m.Z_PK,m.ZCHATSESSION,a.ZMEDIALOCALPATH FROM ZWAMESSAGE m JOIN ZWAMEDIAITEM a ON a.Z_PK=m.ZMEDIAITEM WHERE a.ZMEDIALOCALPATH IS NOT NULL ORDER BY m.Z_PK DESC LIMIT 500').fetchall()
        message, chat, path = next(r for r in rows if server.media_file(r[2]))
        file = server.media_file(path)
        request = Request(self.base + f'/api/media?message={message}', headers={'Range': 'bytes=0-15'})
        with urlopen(request) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(response.read(), file.read_bytes()[:16])
        items = self.get(f'/api/messages?chat={chat}&limit=250')['messages']
        self.assertTrue(any(m['attachment'] and m['attachment']['available'] for m in items))

    def test_search_entire_chat_and_jump(self):
        with server.database() as con:
            target = con.execute('SELECT Z_PK,ZTEXT FROM ZWAMESSAGE WHERE ZCHATSESSION=? AND length(ZTEXT) BETWEEN 25 AND 90 ORDER BY COALESCE(ZSORT,0),Z_PK LIMIT 1', (self.chat,)).fetchone()
        self.assertIsNotNone(target)
        query = target[1].strip()
        results = self.get('/api/search?' + urlencode({'chat': self.chat, 'q': query, 'limit': 100}))
        self.assertGreater(results['total'], 0)
        self.assertTrue(all(query.casefold() in (m['text'] or '').casefold() for m in results['results']))
        latest = self.get(f'/api/messages?chat={self.chat}&limit=10')
        self.assertNotIn(target[0], [m['id'] for m in latest['messages']])
        window = self.get(f'/api/messages?chat={self.chat}&around={target[0]}&limit=20')
        self.assertIn(target[0], [m['id'] for m in window['messages']])
        self.assertLessEqual(len(window['messages']), 21)
        with server.database() as con:
            for m in window['messages']:
                self.assertEqual(con.execute('SELECT ZCHATSESSION FROM ZWAMESSAGE WHERE Z_PK=?', (m['id'],)).fetchone()[0], self.chat)

    def test_search_pagination(self):
        query = urlencode({'chat': self.chat, 'q': 'a', 'limit': 3})
        first = self.get('/api/search?' + query)
        second = self.get('/api/search?' + query + '&offset=3')
        self.assertEqual(first['total'], second['total'])
        self.assertEqual(len(first['results']), 3)
        self.assertFalse(set(m['id'] for m in first['results']) & set(m['id'] for m in second['results']))

    def test_literal_search_and_empty(self):
        empty = self.get('/api/search?' + urlencode({'chat': self.chat, 'q': '   '}))
        self.assertEqual(empty['total'], 0)
        result = self.get('/api/search?' + urlencode({'chat': self.chat, 'q': '%', 'limit': 100}))
        self.assertTrue(all(any('%' in (m.get(field) or '') for field in ('text','title','sender','contact_name')) for m in result['results']))

    def test_jump_rejects_other_chat(self):
        with server.database() as con:
            target = con.execute('SELECT Z_PK FROM ZWAMESSAGE WHERE ZCHATSESSION<>? LIMIT 1', (self.chat,)).fetchone()[0]
        with self.assertRaises(HTTPError) as error:
            self.get(f'/api/messages?chat={self.chat}&around={target}')
        self.assertEqual(error.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
