#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import trio
from trio.abc import Stream


async def send_chunked_data():
    payload = [
        'POST /anything HTTP/1.1\r\n',
        'Accept: application/json, */*\r\n',
        'Accept-Encoding: identity\r\n',
        'Connection: keep-alive\r\n',
        'Content-Type: text/plain\r\n',
        'Transfer-Encoding: chunked\r\n',
        'Host: localhost:8088\r\n',
        'Trailer: X-Hello, X-World\r\n',
        'User-Agent: HTTPie/1.0.2\r\n',
        '\r\n',
        '3\r\n',
        'foo\r\n',
        '3\r\n',
        'bar\r\n',
        '6\r\n',
        '\r\nbazz\r\n',
        '0\r\n',
        'X-Hello: hello\r\n',
        'X-World: world\r\n',
        '\r\n'
    ]
    payload_bytes = ''.join(payload).encode()
    stream: Stream = await trio.open_tcp_stream('localhost', 8088)
    await stream.send_all(payload_bytes)
    await stream.receive_some(4096)
    await stream.aclose()


if __name__ == '__main__':
    trio.run(send_chunked_data)
