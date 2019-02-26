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
        trio.run(self.async_listen, port)

    async def async_listen(self, port: int):
        try:
            logger.info(f'Listening on port {port}')
            await trio.serve_tcp(self._proxy, port)
        except KeyboardInterrupt:
            logger.info('Bye')
            sys.exit(0)

    async def check(self, request: HttpRequestHeader):
        raise NotImplementedError

    async def hook(self, response: HttpResponseHeader, body: bytes = None):
        raise NotImplementedError

    async def background(self, task):
        pass

    @staticmethod
    async def _read_header_tail(buffer, read_stream: Stream):
        while True:
            try:
                tail = buffer.index(b'\r\n\r\n') + 4
                break
            except ValueError:
                pass

            chunk = await read_stream.receive_some(PEEK_BUFFER_SIZE)
            if not chunk:
                raise HookitConnectionError
            buffer += chunk

        return buffer, tail

    @staticmethod
    async def _relay_chunked_data(buffer, read_stream: Stream, write_stream: Stream):
        while True:
            try:
                length_end = buffer.index(b'\r\n')
                chunk_length = int(buffer[:length_end].decode('ascii'), 16)

                if chunk_length == 0:
                    # handle last chunk and trailer
                    trailer_end = buffer.index(b'\r\n\r\n')
                    tail = trailer_end + 4
                    await write_stream.send_all(buffer[:tail])
                    buffer = b''

                    logger.debug(f'Last chunk and trailer relayed')
                    break

                if len(buffer[length_end + 2:]) >= chunk_length + 2:
                    tail = length_end + 2 + chunk_length + 2
                    await write_stream.send_all(buffer[:tail])
                    buffer = buffer[tail:]

                    logger.debug(f'Chunk(length={chunk_length}) relayed')
                    continue
            except ValueError:
                pass

            chunk = await read_stream.receive_some(RELAY_BUFFER_SIZE)
            if not chunk:
                raise HookitConnectionError
            buffer += chunk

        return buffer

    @staticmethod
    async def _relay_data(buffer, length: int, read_stream: Stream, write_stream: Stream):
        while True:
            if length <= len(buffer):
                await write_stream.send_all(buffer[:length])
                buffer = buffer[length:]
                break
            else:
                await write_stream.send_all(buffer)
                length -= len(buffer)
                buffer = b''

            chunk = await read_stream.receive_some(RELAY_BUFFER_SIZE)
            if not chunk:
                raise HookitConnectionError
            buffer += chunk

        return buffer
    
    async def _relay_client(self, client_id: str, client_stream: Stream, server_stream: Stream):
        buf = b''
        logger.debug(f'Connected to client {client_id}')
        while True:
            try:
                buf, tail = await self._read_header_tail(buf, client_stream)
                header_bytes = buf[:tail]
                request = HttpRequestHeader(header_bytes)
                if request.headers.get('upgrade'):
                    logger.warning('Upgrade is not supported')
                    await client_stream.aclose()
                    await server_stream.aclose()
                    return

                self._call_hook = await self.check(request)

                request.headers['host'] = self.host
                header_bytes = request.encode()
                await server_stream.send_all(header_bytes)
                buf = buf[tail:]

                encoding = request.headers.get('transfer-encoding')
                if encoding and 'chunked' in encoding:
                    buf = await self._relay_chunked_data(buf, client_stream, server_stream)
                else:
                    length = int(request.headers.get('content-length', 0))
                    buf = await self._relay_data(buf, length, client_stream, server_stream)
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

    @staticmethod
    async def _read_body_tail(buffer, response: HttpResponseHeader, header_tail: int, read_stream: Stream):
        encoding = response.headers.get('transfer-encoding')
        if encoding and 'chunked' in encoding:
            chunk_start = tail = header_tail
            while True:
                try:
                    length_end = buffer[chunk_start:].index(b'\r\n')
                    chunk_length = int(buffer[chunk_start:length_end].decode('ascii'), 16)

                    if chunk_length == 0:
                        # handle last chunk and trailer
                        trailer_end = buffer.index(b'\r\n\r\n')
                        tail = trailer_end + 4
                        return buffer, tail

                    if len(buffer[chunk_start + length_end + 2:]) >= chunk_length + 2:
                        tail += length_end + 2 + chunk_length + 2
                        chunk_start = tail
                        continue
                except ValueError:
                    pass

                chunk = await read_stream.receive_some(RELAY_BUFFER_SIZE)
                if not chunk:
                    raise HookitConnectionError
                buffer += chunk
        else:
            length = int(response.headers.get('content-length', 0))
            while True:
                if length <= len(buffer[header_tail:]):
                    return buffer, header_tail + length

                chunk = await read_stream.receive_some(RELAY_BUFFER_SIZE)
                if not chunk:
                    raise HookitConnectionError
                buffer += chunk

    async def _relay_server(self, client_stream: Stream, server_stream: Stream, task_queue: SendChannel):
        buf = b''
        while True:
            try:
                buf, header_tail = await self._read_header_tail(buf, server_stream)
                header_bytes = buf[:header_tail]
                response_header = HttpResponseHeader(header_bytes)
                if self._call_hook:
                    self._call_hook = False

                    buf, body_tail = await self._read_body_tail(buf, response_header, header_tail, server_stream)
                    body = buf[header_tail:body_tail]
                    task = await self.hook(response_header, body)
                    if task is not None:
                        logger.debug(f'Working on task {task} in background')
                        await task_queue.send(task)

                    header_bytes = response_header.encode()
                    await client_stream.send_all(header_bytes + buf[header_tail:body_tail])
                    buf = buf[body_tail:]
                    continue

                header_bytes = response_header.encode()
                await client_stream.send_all(header_bytes)
                buf = buf[header_tail:]

                encoding = response_header.headers.get('transfer-encoding')
                if encoding and 'chunked' in encoding:
                    buf = await self._relay_chunked_data(buf, server_stream, client_stream)
                else:
                    length = int(response_header.headers.get('content-length', 0))
                    buf = await self._relay_data(buf, length, server_stream, client_stream)
                    logger.debug(f'{response_header}(length={length}) relayed')

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

    async def _worker(self, queue_id: str, task_queue: ReceiveChannel):
        while True:
            try:
                task = await task_queue.receive()
                await self.background(task)
            except (trio.EndOfChannel, trio.ClosedResourceError):
                logger.debug(f'Task queue {queue_id} closed')
                break

    async def _proxy(self, client_stream: Stream):
        if self.tls:
            server_stream = await trio.open_ssl_over_tcp_stream(self.host, self.port, https_compatible=False)
        else:
            server_stream = await trio.open_tcp_stream(self.host, self.port)
        logger.debug(f'Connected to {self.host}:{self.port}')

        unique_id = uuid.uuid4().hex
        send_channel, receive_channel = trio.open_memory_channel(TASK_QUEUE_SIZE)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self._worker, unique_id, receive_channel)
            nursery.start_soon(self._relay_client, unique_id, client_stream, server_stream)
            nursery.start_soon(self._relay_server, client_stream, server_stream, send_channel)


__all__ = ['Hookit']
