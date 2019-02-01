#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from trio.abc import Stream
import trio

import os
import sys
import uuid

from .http import *
from .log import logger

PEEK_BUFFER_SIZE = os.getenv('PEEK_BUFFER_SIZE', 128)
RELAY_BUFFER_SIZE = os.getenv('PROXY_BUFFER_SIZE', 1024 * 512)


class Hookit(object):
    def __init__(self, host: str, port: int, tls=False):
        self.host = host
        self.port = port
        self.tls = tls
        self._call_hook = False

    def listen(self, port: int):
        trio.run(self._listen, port)

    async def _listen(self, port: int):
        try:
            logger.info(f'Listening on {port}')
            await trio.serve_tcp(self._proxy, port)
        except KeyboardInterrupt:
            logger.info('Bye')
            sys.exit(0)

    async def check(self, request):
        raise NotImplementedError

    async def hook(self, response):
        raise NotImplementedError

    async def _relay_client(self, client_stream: Stream, server_stream: Stream):
        buf = b''
        client_id = uuid.uuid4().hex
        logger.debug(f'Connected to client {client_id}')
        while True:
            try:
                while True:
                    try:
                        tail = buf.index(b'\r\n\r\n') + 4
                        break
                    except ValueError:
                        pass

                    chunk = await client_stream.receive_some(PEEK_BUFFER_SIZE)
                    if not chunk:
                        logger.debug(f'Connection to client {client_id} closed')
                        await server_stream.aclose()
                        return
                    buf += chunk

                header_bytes = buf[:tail]
                request = HttpRequestHeader(header_bytes)
                self._call_hook = await self.check(request)

                request.headers['host'] = self.host
                header_bytes = request.encode()
                await server_stream.send_all(header_bytes)
                buf = buf[tail:]

                length = int(request.headers.get('content-length', 0))
                while True:
                    if length <= len(buf):
                        await server_stream.send_all(buf[:length])
                        buf = buf[length:]
                        break
                    else:
                        await server_stream.send_all(buf)
                        length -= len(buf)
                        buf = b''

                    chunk = await client_stream.receive_some(RELAY_BUFFER_SIZE)
                    if not chunk:
                        logger.debug(f'Connection to client {client_id} closed')
                        await server_stream.aclose()
                        return
                    buf += chunk

                logger.debug(f'{request}(length={length}) relayed')

            except trio.ClosedResourceError:
                logger.debug(f'Connection to client {client_id} closed by server')
                return
            except Exception as ex:
                logger.exception(ex)
                return

    async def _relay_server(self, client_stream: Stream, server_stream: Stream):
        buf = b''
        while True:
            try:
                while True:
                    try:
                        tail = buf.index(b'\r\n\r\n') + 4
                        break
                    except ValueError:
                        pass

                    chunk = await server_stream.receive_some(PEEK_BUFFER_SIZE)
                    if not chunk:
                        logger.debug(f'Connection to {self.host}:{self.port} closed')
                        await client_stream.aclose()
                        return
                    buf += chunk

                header_bytes = buf[:tail]
                response = HttpResponseHeader(header_bytes)
                if self._call_hook:
                    self._call_hook = False
                    await self.hook(response)

                header_bytes = response.encode()
                await client_stream.send_all(header_bytes)
                buf = buf[tail:]

                length = int(response.headers.get('content-length', 0))
                while True:
                    if length <= len(buf):
                        await client_stream.send_all(buf[:length])
                        buf = buf[length:]
                        break
                    else:
                        await client_stream.send_all(buf)
                        length -= len(buf)
                        buf = b''

                    chunk = await server_stream.receive_some(RELAY_BUFFER_SIZE)
                    if not chunk:
                        logger.debug(f'Connection to {self.host}:{self.port} closed')
                        await client_stream.aclose()
                        return
                    buf += chunk

                logger.debug(f'{response}(length={length}) relayed')

            except trio.ClosedResourceError:
                logger.debug(f'Connection to {self.host}:{self.port} closed by client')
                return
            except Exception as ex:
                logger.exception(ex)
                return

    async def _proxy(self, client_stream: Stream):
        if self.tls:
            server_stream = await trio.open_ssl_over_tcp_stream(self.host, self.port, https_compatible=False)
        else:
            server_stream = await trio.open_tcp_stream(self.host, self.port)
        logger.debug(f'Connected to {self.host}:{self.port}')
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self._relay_client, client_stream, server_stream)
            nursery.start_soon(self._relay_server, client_stream, server_stream)


__all__ = ['Hookit']
