#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hookit import Hookit
from loguru import logger
import trio


class HookProxy(Hookit):
    async def check(self, request):
        logger.info(request)
        logger.info("Let's call hook()")
        return True

    async def hook(self, response, body=None):
        logger.info('hook() is called')
        logger.info(response)
        logger.info(body.decode())
        return 3

    async def background(self, seconds):
        await trio.sleep(seconds)
        logger.info('Task completed')


if __name__ == '__main__':
    proxy = HookProxy('httpbin.org', 443, tls=True)
    proxy.listen(8088)
