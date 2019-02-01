#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from trio.abc import Stream, SendChannel, ReceiveChannel
import trio

import sys
import uuid

from .config import *
from .exc import HookitConnectionError
from .http import *
from .log import logger


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

    async def check(self, request: HttpRequestHeader):
        raise NotImplementedError

    async def hook(self, response: HttpResponseHeader):
        raise NotImplementedError

    async def background(self, task):
        pass
    
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
                        raise HookitConnectionError
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
                        raise HookitConnectionError
                    buf += chunk

                logger.debug(f'{request}(length={length}) relayed')

            except HookitConnectionError:
                logger.debug(f'Connection to client {client_id} closed')
                await server_stream.aclose()
                return
            except trio.ClosedResourceError:
                logger.debug(f'Connection to client {client_id} closed by server')
                return
            except Exception as ex:
                logger.exception(ex)
                return

    async def _relay_server(self, client_stream: Stream, server_stream: Stream, task_queue: SendChannel):
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
                        raise HookitConnectionError
                    buf += chunk

                header_bytes = buf[:tail]
                response = HttpResponseHeader(header_bytes)
                if self._call_hook:
                    self._call_hook = False
                    task = await self.hook(response)
                    if task is not None:
                        logger.debug(f'Working on task {task} in background')
                        await task_queue.send(task)

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
                        raise HookitConnectionError
                    buf += chunk

                logger.debug(f'{response}(length={length}) relayed')

            except HookitConnectionError:
                logger.debug(f'Connection to {self.host}:{self.port} closed')
                await client_stream.aclose()
                await task_queue.aclose()
                return
            except trio.ClosedResourceError:
                logger.debug(f'Connection to {self.host}:{self.port} closed by client')
                await task_queue.aclose()
                return
            except Exception as ex:
                logger.exception(ex)
                return

    async def _worker(self, task_queue: ReceiveChannel):
        while True:
            try:
                task = await task_queue.receive()
                await self.background(task)
            except (trio.EndOfChannel, trio.ClosedResourceError):
                logger.debug(f'Task queue closed')
                break

    async def _proxy(self, client_stream: Stream):
        if self.tls:
            server_stream = await trio.open_ssl_over_tcp_stream(self.host, self.port, https_compatible=False)
        else:
            server_stream = await trio.open_tcp_stream(self.host, self.port)
        logger.debug(f'Connected to {self.host}:{self.port}')

        send_channel, receive_channel = trio.open_memory_channel(TASK_QUEUE_SIZE)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self._worker, receive_channel)
            nursery.start_soon(self._relay_client, client_stream, server_stream)
            nursery.start_soon(self._relay_server, client_stream, server_stream, send_channel)


__all__ = ['Hookit']
