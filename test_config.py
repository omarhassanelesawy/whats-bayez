"""Configuration tests that do not require or access a private backup."""
import io
import unittest
from unittest.mock import patch
import server


class ConfigurationTests(unittest.TestCase):
    def test_default_port_is_loopback_only(self):
        with patch.object(server, 'ThreadingHTTPServer') as factory, patch('builtins.print'):
            server.main([])
        factory.assert_called_once_with(('127.0.0.1', 8765), server.Handler)
        factory.return_value.serve_forever.assert_called_once_with()

    def test_custom_port_is_loopback_only(self):
        with patch.object(server, 'ThreadingHTTPServer') as factory, patch('builtins.print'):
            server.main(['--port', '8877'])
        factory.assert_called_once_with(('127.0.0.1', 8877), server.Handler)
        factory.return_value.serve_forever.assert_called_once_with()

    def test_invalid_ports_do_not_start_server(self):
        for value in ('0', '-1', '65536', 'not-a-port'):
            with self.subTest(value=value), patch.object(server, 'ThreadingHTTPServer') as factory:
                with patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit) as error:
                    server.main(['--port', value])
                self.assertEqual(error.exception.code, 2)
                factory.assert_not_called()

    def test_bind_error_has_actionable_message(self):
        with patch.object(server, 'ThreadingHTTPServer', side_effect=OSError('Address already in use')):
            with patch('sys.stderr', new_callable=io.StringIO) as output:
                with self.assertRaises(SystemExit) as error:
                    server.main([])
                self.assertEqual(error.exception.code, 1)
                self.assertIn('Try another --port', output.getvalue())

    def test_control_c_exits_cleanly(self):
        with patch.object(server, 'ThreadingHTTPServer') as factory, patch('builtins.print'):
            factory.return_value.serve_forever.side_effect = KeyboardInterrupt
            server.main([])
        factory.return_value.__exit__.assert_called_once()


if __name__ == '__main__':
    unittest.main()
