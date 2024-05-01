# Uncomment this to pass the first stage
import socket
from typing import NamedTuple

class HTTPRequest(NamedTuple):
    method: str
    path: str
    version: str

class HTTPHeader(dict):
    pass

def read(client: socket.socket,
         __chunk: int= 1024) -> tuple[HTTPRequest, HTTPHeader, str]:
    data = info = header = body = b''
    while True:
        tmp = client.recv(__chunk)
        if len(tmp) < __chunk:
            data += tmp
            break
        data += tmp
    splitted = data.split(b'\r\n')
    info = splitted[0]
    header = splitted[1:-1]
    body = splitted[-1]
    return (fetch_info(info), fetch_header(header), body.decode())

def fetch_info(req: bytes):
    data: list[bytes] = req.split(b' ')
    return HTTPRequest(data[0].decode(), data[1].decode(), data[2].decode())

def fetch_header(req: list[bytes]):
    header = HTTPHeader()
    if not req:
        return header

    for v in req:
        if not v:
            continue
        key, value = tuple(map(bytes.decode, v.split(b': ', maxsplit=1)))
        header[key] = value
    return header

def to_header(header: HTTPHeader) -> bytes:
    return ("\r\n"
                .join([f'{key}: {value}' for key, value in header.items()])
            ).encode()

def respond(status: tuple[int, str],
            header: HTTPHeader = HTTPHeader(),
            payload: str | bytes = '',
            ver: str = "HTTP/1.1") -> bytes:
    if isinstance(payload, (memoryview, bytearray)):
        raise TypeError(f"Expected bytes or str, got {type(payload).__name__}")
    s = f'{ver} {status[0]} {status[1]}\r\n'.encode()
    s += to_header(header) + b'\r\n\r\n'
    s += (payload if isinstance(payload, bytes) else payload.encode())
    print(s)
    return s

def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    # Uncomment this to pass the first stage
    
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    client, addr = server_socket.accept() # wait for client
    
    print(f"Connected to {addr[0]}:{addr[1]}")
    data = read(client)
    print(data)

    if data[0].path == '/':
        client.send(respond((200, 'OK')))

    if data[0].path.startswith('/echo/'):
        content = data[0].path.replace('/echo/', '', 1)
        header = HTTPHeader({
            'Content-Type': 'text/plain',
            'Content-Length': len(content)
        })
        client.send(respond((200, 'OK'),
                            header,
                            content
        ))

    if data[0].path == '/user-agent':
        content = data[1].get('User-Agent', '')
        header = HTTPHeader({
            'Content-Type': 'text/plain',
            'Content-Length': len(content)
        })
        client.send(respond((200, 'OK'),
                            header,
                            content
        ))

    else:
        client.send(respond((404, 'NOT FOUND')))

    client.close()
    server_socket.close()

if __name__ == "__main__":
    main()
