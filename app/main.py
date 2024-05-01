# Uncomment this to pass the first stage
import socket
from typing import NamedTuple
from threading import Thread
from sys import argv
from os.path import join, exists

def scan_through_argv():
    keys = ["program"]
    values = [argv[0]]
    for i in argv[1:]:
        if i.startswith('-'):
            keys.append(i)
            continue
        values.append(i)
        if len(values) != len(keys):
            keys.append(f'args-{len(values)}')
    return {key:value for key, value in zip(keys, values)}

argv_data = scan_through_argv()

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
    return s

def on_echo(client: socket.socket,
            data: tuple[HTTPRequest, HTTPHeader, str]):
    content = data[0].path.replace('/echo/', '', 1)
    header = HTTPHeader({
        'Content-Type': 'text/plain',
        'Content-Length': len(content)
    })
    client.send(respond((200, 'OK'),
                        header,
                        content
    ))

def on_useragent(client: socket.socket,
                 data: tuple[HTTPRequest, HTTPHeader, str]):
    content = data[1].get('User-Agent', '')
    header = HTTPHeader({
        'Content-Type': 'text/plain',
        'Content-Length': len(content)
    })
    client.send(respond((200, 'OK'),
                        header,
                        content
    ))

def on_files(client: socket.socket,
             data: tuple[HTTPRequest, HTTPHeader, str]):
    directory = argv_data['--directory']
    filename = join(directory, data[0].path.replace('/files/', '', 1))

    if not exists(filename):
        return client.send(respond((404, "Not Found")))

    with open(filename) as file:
        content = file.read()

    header = HTTPHeader({
        'Content-Type': 'application/octet-stream',
        'Content-Length': len(content)
    })
    client.send(respond(
        (200, "OK"),
        header,
        content
    ))

def on_files_upload(client: socket.socket,
                    data: tuple[HTTPRequest, HTTPHeader, str]):
    directory = argv_data['--directory']
    filename = join(directory, data[0].path.replace('/files/', '', 1))

    payload = data[2]
    with open(filename, 'w') as file:
        file.write(payload)
    client.send(respond(
        (201, "Created")
    ))

def thread_cycle(client: socket.socket, addr: tuple[str, int]):
    print(f"Connected to {addr[0]}:{addr[1]}")
    data = read(client)
    stat, _, _ = data
    print(data)

    if data[0].path == '/':
        client.send(respond((200, 'OK')))

    if data[0].path.startswith('/echo/'):
        on_echo(client, data)

    if data[0].path.startswith('/files'):
        if stat.method == 'GET':
            on_files(client, data)
        if stat.method == 'POST':
            on_files_upload(client, data)

    if data[0].path == '/user-agent':
        on_useragent(client, data)
    else:
        client.send(respond((404, 'Not Found')))

    client.close()


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")
    print("ARGV: ", argv_data)

    # Uncomment this to pass the first stage
    
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    
    while True:
        client, addr = server_socket.accept() # wait for client
        thread = Thread(target=thread_cycle, args=(client, addr))
        thread.start()

    server_socket.close()

if __name__ == "__main__":
    main()
