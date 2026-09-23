import json
import os
import select
import socket
import stat
import struct
import subprocess
import sys
import time
from pathlib import Path

MAX_MESSAGE = 1048576


def private_directory(path):
    st = path.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise PermissionError("Boreal-Laufzeitordner muss privat (0700) und benutzereigen sein")


def runtime_dir():
    configured = os.environ.get("XDG_RUNTIME_DIR")
    base = Path(configured or f"/tmp/boreal-{os.getuid()}")
    if not base.is_absolute() or '..' in base.parts:
        raise PermissionError('Absoluter privater Laufzeitordner erforderlich')
    parent = base.parent
    info = parent.lstat()
    trusted_owner = info.st_uid in (0, os.getuid())
    protected_tmp = parent == Path('/tmp') and bool(info.st_mode & stat.S_ISVTX)
    writable_without_sticky = info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX
    if (not stat.S_ISDIR(info.st_mode) or not (trusted_owner or protected_tmp)
            or writable_without_sticky):
        raise PermissionError('Unsicherer übergeordneter Laufzeitordner')
    if not configured:
        base.mkdir(mode=0o700, exist_ok=True)
        legacy = base.lstat()
        if not stat.S_ISDIR(legacy.st_mode) or legacy.st_uid != os.getuid():
            raise PermissionError('Unsicherer Boreal-Fallbackordner')
        if legacy.st_mode & 0o077:
            base.chmod(0o700)
    private_directory(base)
    root = base / 'boreal'
    root.mkdir(mode=0o700, exist_ok=True)
    private_directory(root)
    return root


def open_lock(path):
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1):
            raise PermissionError('Unsichere Boreal-Lockdatei')
        os.fchmod(fd, 0o600)
        return os.fdopen(fd, 'r+')
    except Exception:
        os.close(fd)
        raise


def socket_path(demo):
    return runtime_dir() / ("demo.sock" if demo else "hardware.sock")


def receive(sock):
    data = bytearray()
    while not data.endswith(b"\n"):
        chunk = sock.recv(min(4096, MAX_MESSAGE + 1 - len(data)))
        if not chunk:
            raise ConnectionError("Verbindung ohne Antwort beendet")
        data.extend(chunk)
        if len(data) > MAX_MESSAGE:
            raise ValueError("Nachricht zu groß")
    return json.loads(data)


def rpc(demo, op, **args):
    from .errors import BorealError
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(3)
        client.connect(str(socket_path(demo)))
        _, uid, _ = struct.unpack('3i', client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if uid != os.getuid():
            raise PermissionError('Boreal-Dienst gehört einem anderen Benutzer')
        client.sendall(json.dumps({"v": 2, "op": op, **args}, allow_nan=False).encode() + b"\n")
        response = receive(client)
        if not response.get('ok'):
            error = response.get('error', {})
            if isinstance(error, str): raise BorealError(error, 'version')
            raise BorealError(error.get('message','Unbekannter Fehler'), error.get('code','operation'),
                              error.get('component','service'), error.get('retryable',False))
        return response['result']


def request(demo, op, **args):
    """CLI/test convenience; UI polls jobs asynchronously without blocking its main loop."""
    from .errors import BorealError
    result = rpc(demo, op, **args)
    if not isinstance(result, dict) or 'job_id' not in result: return result
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        job=rpc(demo,'job',job_id=result['job_id'])
        if job['state']=='done': return job.get('result')
        if job['state']=='failed':
            e=job['error']; raise BorealError(e['message'],e['code'],e['component'],e['retryable'])
        time.sleep(.05)
    raise BorealError('Auftrag dauert länger; Status in der Oberfläche prüfen','timeout')


class Worker:
    def __init__(self, demo=False):
        self.demo = demo
        self.process = None

    def call(self, op, *args):
        if self.process is None:
            command = [sys.executable, "-m", "boreal.worker"] + (["--demo"] if self.demo else [])
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            bufsize=0)
        process = self.process
        try:
            process.stdin.write(json.dumps({"op": op, "args": args}, allow_nan=False).encode() + b"\n")
            deadline = time.monotonic() + (20 if op == "screen" else 8)
            data = bytearray()
            while not data.endswith(b"\n"):
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
                    raise TimeoutError("Hardware antwortet nicht rechtzeitig; Verbindung gesperrt")
                chunk = os.read(process.stdout.fileno(), 4096)
                if not chunk:
                    raise ConnectionError("Hardwareprozess wurde beendet")
                data.extend(chunk)
                if len(data) > MAX_MESSAGE:
                    raise ValueError("Hardwareantwort zu groß")
            response = json.loads(data)
        except Exception:
            self.close()
            raise
        if not response["ok"]:
            raise RuntimeError(response["error"])
        return response.get("result")

    def close(self):
        if self.process:
            self.process.kill()
            self.process.wait(timeout=3)
            self.process.stdin.close()
            self.process.stdout.close()
            self.process = None
