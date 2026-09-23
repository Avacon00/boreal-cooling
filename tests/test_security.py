import json
import os
import stat
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from boreal.library import media_call
from boreal.media_worker import copy_source
from boreal.transport import open_lock, rpc, runtime_dir


class SourceBoundaryTests(unittest.TestCase):
    def test_special_source_and_fifo_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            link = root / 'image.png'
            link.symlink_to('/dev/zero')
            fifo = root / 'pipe.gif'
            os.mkfifo(fifo)
            for source in (link, fifo):
                with self.assertRaises(ValueError):
                    copy_source(source, root / 'copy')
                self.assertFalse((root / 'copy').exists())

    def test_regular_symlink_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'image'
            source.write_bytes(b'normal image bytes')
            link = root / 'link'
            link.symlink_to(source)
            copy_source(link, root / 'copy')
            self.assertEqual((root / 'copy').read_bytes(), source.read_bytes())

    def test_growth_after_fstat_stays_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'growing'
            with source.open('wb') as stream:
                stream.truncate(10 * 1024**2 + 1)
            opened = SimpleNamespace(st_mode=stat.S_IFREG, st_size=1)
            with patch('boreal.media_worker.os.fstat', return_value=opened):
                with self.assertRaises(ValueError):
                    copy_source(source, root / 'copy')
            self.assertLessEqual((root / 'copy').stat().st_size, 10 * 1024**2)

    def test_parent_cleans_workspace_on_child_timeout(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'XDG_DATA_HOME': tmp}):
            seen = []

            def timeout(*args, **kwargs):
                workspace = Path(json.loads(kwargs['input'])['workspace'])
                seen.append(workspace)
                (workspace / 'partial').write_bytes(b'partial')
                raise subprocess.TimeoutExpired(args[0], 15)

            with patch('boreal.library.subprocess.run', side_effect=timeout):
                with self.assertRaises(ValueError):
                    media_call('import', path='unused', mode='static', size=64)
            self.assertEqual(len(seen), 1)
            self.assertFalse(seen[0].exists())


class RuntimeBoundaryTests(unittest.TestCase):
    def test_legacy_fallback_and_lock_permissions_are_tightened(self):
        with tempfile.TemporaryDirectory() as tmp:
            uid = os.getuid()
            base = Path(tmp) / f'boreal-{uid}'
            base.mkdir(mode=0o755)
            leaf = base / 'boreal'
            leaf.mkdir(mode=0o700)
            lock = leaf / 'demo.lock'
            lock.write_text('legacy lock contents')
            lock.chmod(0o644)
            with patch.dict(os.environ, {}, clear=True), \
                    patch('boreal.transport.Path', wraps=Path) as path_type:
                path_type.side_effect = lambda value: (
                    base if value == f'/tmp/boreal-{uid}' else Path(value))
                self.assertEqual(runtime_dir(), leaf)
            self.assertEqual(base.stat().st_mode & 0o777, 0o700)
            with open_lock(lock):
                pass
            self.assertEqual(lock.read_text(), 'legacy lock contents')
            self.assertEqual(lock.stat().st_mode & 0o777, 0o600)

    def test_private_runtime_and_unsafe_base(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'XDG_RUNTIME_DIR': tmp}):
            self.assertEqual(runtime_dir(), Path(tmp) / 'boreal')
            Path(tmp).chmod(0o777)
            with self.assertRaises(PermissionError):
                runtime_dir()
            Path(tmp).chmod(0o700)

    def test_runtime_base_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'real').mkdir(mode=0o700)
            (base / 'link').symlink_to(base / 'real')
            with patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(base / 'link')}):
                with self.assertRaises(PermissionError):
                    runtime_dir()

    def test_foreign_owner_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'XDG_RUNTIME_DIR': tmp}):
            original = Path.lstat

            def different(path):
                if path == Path(tmp):
                    return SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=os.getuid() + 1)
                return original(path)

            with patch.object(Path, 'lstat', different):
                with self.assertRaises(PermissionError):
                    runtime_dir()

    def test_lock_links_rejected_and_contents_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'target'
            target.write_text('preserve')
            target.chmod(0o600)
            link = root / 'lock'
            link.symlink_to(target)
            with self.assertRaises(OSError):
                open_lock(link)
            self.assertEqual(target.read_text(), 'preserve')
            target.chmod(0o644)
            with open_lock(target):
                pass
            self.assertEqual(target.read_text(), 'preserve')
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            link.unlink()
            os.link(target, link)
            with self.assertRaises(PermissionError):
                open_lock(link)

    def test_other_server_uid_rejected_before_sending(self):
        client = Mock()
        client.getsockopt.return_value = struct.pack('3i', 123, os.getuid() + 1, 123)
        context = Mock()
        context.__enter__ = Mock(return_value=client)
        context.__exit__ = Mock(return_value=False)
        with patch('boreal.transport.socket.socket', return_value=context), \
                patch('boreal.transport.socket_path', return_value=Path('/unused')):
            with self.assertRaises(PermissionError):
                rpc(True, 'snapshot')
        client.sendall.assert_not_called()
