"""Workspace entry point for the host's correctness-only Lean checker."""
import json
from pathlib import Path
import socket
import sys


def main():
    workspace = Path(__file__).resolve().parent
    connection = json.loads((workspace / 'validity_service.json').read_text())
    path = Path(sys.argv[1])
    if not path.is_absolute():
        path = workspace / path
    code = path.read_text()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(600)
        client.connect(connection['socket'])
        client.sendall(json.dumps({'code': code}, ensure_ascii=False).encode() + b'\n')
        with client.makefile('rb') as stream:
            response = json.loads(stream.readline(2 * 1024 * 1024))
    if 'error' in response:
        raise RuntimeError(response['error'])
    print(json.dumps(response['feedback'], ensure_ascii=False))


if __name__ == '__main__':
    main()
