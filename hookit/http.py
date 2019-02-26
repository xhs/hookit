#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class HttpHeader(object):
    def __init__(self, buf: bytes):
        self._lines = buf[:-4].decode().split('\r\n')
        self.headers = {}
        self._parse_headers()

    def _parse_headers(self):
        for line in self._lines[1:]:
            name, value = line.split(':', maxsplit=1)
            self.headers[name.strip().lower()] = value.strip()

    def encode_headers(self):
        ls = []
        for name, value in self.headers.items():
            ls.append(f'{name}: {value}')
        return '\r\n'.join(ls).encode() + b'\r\n\r\n'


class HttpRequestHeader(HttpHeader):
    def __init__(self, buf: bytes):
        super().__init__(buf)
        self._parse()

    def encode(self):
        return f'{self.method} {self.path} {self.version}\r\n'.encode() + self.encode_headers()

    def _parse(self):
        method, path, version = self._lines[0].split(' ')
        self.method = method
        self.path = path
        self.version = version

    def __str__(self):
        return f'HttpRequestHeader{{{self.method}, {self.path}, {self.version}, {self.headers}}}'


class HttpResponseHeader(HttpHeader):
    def __init__(self, buf: bytes):
        super().__init__(buf)
        self._parse()

    def encode(self):
        return f'{self.version} {self.code} {self.status}\r\n'.encode() + self.encode_headers()

    def _parse(self):
        version, code, status = self._lines[0].split(' ', maxsplit=2)
        self.version = version
        self.code = int(code)
        self.status = status

    def __str__(self):
        return f'HttpResponseHeader{{{self.version}, {self.code}, {self.status}, {self.headers}}}'


__all__ = ['HttpRequestHeader', 'HttpResponseHeader']
