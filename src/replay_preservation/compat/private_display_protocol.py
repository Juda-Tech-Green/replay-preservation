"""Fixed-size RGB and allowlisted key events over a disposable Unix socket; no file/command API."""
import argparse, json, os, socket, struct
from pathlib import Path
from .private_x11 import Display, W, H
FRAME_BYTES = W * H * 3
MAX_REQUEST = 256

def receive(sock, n):
    result = bytearray()
    while len(result) < n:
        data = sock.recv(n - len(result))
        if not data:
            raise EOFError('Private viewer disconnected')
        result.extend(data)
    return bytes(result)

class Client:

    def __init__(self, path):
        self.s = socket.socket(socket.AF_UNIX)
        self.s.settimeout(3)
        self.s.connect(str(path))

    def request(self, op, **kw):
        data = json.dumps({'op': op, **kw}, separators=(',', ':')).encode()
        if not len(data) <= MAX_REQUEST:
            raise ValueError('Invalid compatibility-helper state')
        self.s.sendall(struct.pack('>H', len(data)) + data)
        kind = receive(self.s, 1)
        n = struct.unpack('>I', receive(self.s, 4))[0]
        if kind == b'F':
            if n != FRAME_BYTES:
                raise ValueError('Invalid fixed frame length')
            return receive(self.s, n)
        if kind != b'J' or n > 4096:
            raise ValueError('Invalid reply')
        r = json.loads(receive(self.s, n))
        if not r.get('ok') is True:
            raise ValueError(r)
        return r

    def close(self):
        self.s.close()

def serve(path):
    if not path == '/ipc/display.sock':
        raise ValueError('Invalid compatibility-helper state')
    if not Path('/ipc').is_dir():
        raise ValueError('Invalid compatibility-helper state')
    if not not Path(path).exists():
        raise ValueError('Invalid compatibility-helper state')
    os.umask(63)
    display = Display()
    server = socket.socket(socket.AF_UNIX)
    server.bind(path)
    server.listen(1)
    server.settimeout(1)
    print(json.dumps({'private_viewer_server_ready': True, 'protocol': 'fixed RGB 800x600; allowlisted key down/up only; no file/clipboard/command operations'}), flush=True)
    try:
        while True:
            try:
                peer, _ = server.accept()
            except socket.timeout:
                continue
            peer.settimeout(3)
            try:
                while True:
                    n = struct.unpack('>H', receive(peer, 2))[0]
                    if not 0 < n <= MAX_REQUEST:
                        raise ValueError('Request too large')
                    req = json.loads(receive(peer, n))
                    if not isinstance(req, dict):
                        raise ValueError('Invalid compatibility-helper state')
                    if req == {'op': 'frame'}:
                        data = display.frame()
                        kind = b'F'
                    elif set(req) == {'op', 'key', 'down'} and req['op'] == 'key' and (type(req['down']) is bool) and isinstance(req['key'], str):
                        display.focus()
                        display.key(req['key'], req['down'])
                        data = b'{"ok":true}'
                        kind = b'J'
                    else:
                        raise ValueError('Operation not permitted')
                    peer.sendall(kind + struct.pack('>I', len(data)) + data)
            except (EOFError, ValueError, AssertionError, socket.timeout, BrokenPipeError, ConnectionResetError) as exc:
                print(json.dumps({'client_session_closed': type(exc).__name__}), flush=True)
            finally:
                peer.close()
    finally:
        server.close()
        display.close()
        Path(path).unlink(missing_ok=True)
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--server', choices=['/ipc/display.sock'], required=True)
    a = p.parse_args()
    serve(a.server)
