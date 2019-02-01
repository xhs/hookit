#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hookit import Hookit
from loguru import logger


class HookProxy(Hookit):
    async def check(self, request):
        logger.info("Let's call hook()")
        return True

    async def hook(self, response):
        logger.info('hook() is called')


if __name__ == '__main__':
    proxy = HookProxy('httpbin.org', 443, tls=True)
    proxy.listen(8088)
