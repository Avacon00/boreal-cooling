import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from boreal.transport import Worker, request, socket_path


class WorkerTests(unittest.TestCase):
    def test_real_demo_worker_roundtrip(self):
        worker = Worker(True)
        try:
            result = worker.call('discover')
            self.assertEqual(result[0]['id'], 'demo-z3')
            worker.call('attach', 'demo-z3')
            self.assertGreater(worker.call('status', 'demo-z3')['Pump speed']['value'], 0)
        finally:
            worker.close()

    def test_deadline_kills_worker(self):
        worker = Worker(True)
        worker.process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
        proc = worker.process
        with patch('boreal.transport.select.select', return_value=([], [], [])):
            with self.assertRaises(TimeoutError):
                worker.call('discover')
        self.assertIsNone(worker.process)
        self.assertIsNotNone(proc.poll())


@unittest.skipUnless(os.environ.get('BOREAL_INTEGRATION') == '1', 'Requires local Unix sockets')
class DaemonTests(unittest.TestCase):
    def test_daemon_rpc_lifecycle(self):
        with tempfile.TemporaryDirectory(prefix='boreal-test-', dir='/tmp') as tmp:
            env = {**os.environ, 'XDG_RUNTIME_DIR': tmp, 'XDG_CONFIG_HOME': tmp,
                   'XDG_STATE_HOME': tmp}
            with patch.dict(os.environ, env):
                process = subprocess.Popen([sys.executable, '-m', 'boreal', '--daemon', '--demo'], env=env,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    for _ in range(100):
                        if socket_path(True).exists():
                            break
                        time.sleep(.03)
                    self.assertEqual(socket_path(True).stat().st_mode & 0o777, 0o600)
                    state = request(True, 'discover')
                    key = state['devices'][0]['id']
                    state = request(True, 'attach', device=key)
                    self.assertTrue(state['devices'][0]['connected'])
                    from boreal.core import PRESETS
                    request(True, 'save_profile', name='Integration', profile=PRESETS['Leise'])
                    self.assertIn('Integration', request(True, 'profiles'))
                    request(True, 'apply', device=key, profile=PRESETS['Leise'])
                    request(True, 'screen', device=key, mode='stats')
                    request(True, 'color', device=key, channel='external', mode='fixed', hex='74dbbb')
                    state = request(True, 'detach', device=key)
                    self.assertFalse(state['devices'][0]['connected'])
                    # A second service must fail without replacing the first socket.
                    duplicate = subprocess.run([sys.executable, '-m', 'boreal', '--daemon', '--demo'], env=env,
                                               capture_output=True, timeout=5)
                    self.assertNotEqual(duplicate.returncode, 0)
                    self.assertIsInstance(request(True, 'snapshot'), dict)
                finally:
                    process.terminate()
                    process.wait(timeout=10)
                self.assertFalse(socket_path(True).exists())
