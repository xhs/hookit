# hookit

Trio-based semi-transparent HTTP proxy to enhance any API with hooks

```bash
pip install hookit-python
```

```python
from hookit import Hookit
from loguru import logger
import trio


class HookProxy(Hookit):
    async def check(self, request):
        logger.info("Let's call hook()")
        return True

    async def hook(self, response):
        logger.info('hook() is called')
        return 5

    async def background(self, seconds):
        await trio.sleep(seconds)
        logger.info('Task completed')


if __name__ == '__main__':
    proxy = HookProxy('httpbin.org', 443, tls=True)
    proxy.listen(8088)
```

```
2019-02-02 01:26:03.762 | INFO     | hookit.hookit:_listen:28 - Listening on 8088
2019-02-02 01:26:06.712 | DEBUG    | hookit.hookit:_proxy:173 - Connected to httpbin.org:443
2019-02-02 01:26:06.712 | DEBUG    | hookit.hookit:_relay_client:46 - Connected to client d5990f2f88bf41c4a2d9e7b8a164dfb0
2019-02-02 01:26:06.713 | INFO     | __main__:check:11 - Let's call hook()
2019-02-02 01:26:07.271 | DEBUG    | hookit.hookit:_relay_client:86 - HttpRequestHeader{POST, /anything, HTTP/1.1}(length=14) relayed
2019-02-02 01:26:07.559 | INFO     | __main__:hook:15 - hook() is called
2019-02-02 01:26:07.559 | DEBUG    | hookit.hookit:_relay_server:121 - Working on task 5 in background
2019-02-02 01:26:07.559 | DEBUG    | hookit.hookit:_relay_server:144 - HttpResponseHeader{HTTP/1.1, 200, OK}(length=461) relayed
2019-02-02 01:26:07.564 | DEBUG    | hookit.hookit:_relay_client:89 - Connection to client d5990f2f88bf41c4a2d9e7b8a164dfb0 closed
2019-02-02 01:26:07.564 | DEBUG    | hookit.hookit:_relay_server:152 - Connection to httpbin.org:443 closed by client
2019-02-02 01:26:07.566 | DEBUG    | hookit.hookit:_proxy:173 - Connected to httpbin.org:443
2019-02-02 01:26:07.566 | DEBUG    | hookit.hookit:_relay_client:46 - Connected to client 717501c7e6114109a229af51c485c191
2019-02-02 01:26:07.566 | INFO     | __main__:check:11 - Let's call hook()
2019-02-02 01:26:08.066 | DEBUG    | hookit.hookit:_relay_client:86 - HttpRequestHeader{POST, /anything, HTTP/1.1}(length=14) relayed
2019-02-02 01:26:08.314 | INFO     | __main__:hook:15 - hook() is called
2019-02-02 01:26:08.314 | DEBUG    | hookit.hookit:_relay_server:121 - Working on task 5 in background
2019-02-02 01:26:08.314 | DEBUG    | hookit.hookit:_relay_server:144 - HttpResponseHeader{HTTP/1.1, 200, OK}(length=461) relayed
2019-02-02 01:26:08.331 | DEBUG    | hookit.hookit:_relay_client:89 - Connection to client 717501c7e6114109a229af51c485c191 closed
2019-02-02 01:26:08.331 | DEBUG    | hookit.hookit:_relay_server:152 - Connection to httpbin.org:443 closed by client
2019-02-02 01:26:12.564 | INFO     | __main__:background:20 - Task completed
2019-02-02 01:26:12.564 | DEBUG    | hookit.hookit:_worker:165 - Task queue closed
2019-02-02 01:26:13.316 | INFO     | __main__:background:20 - Task completed
2019-02-02 01:26:13.316 | DEBUG    | hookit.hookit:_worker:165 - Task queue closed
2019-02-02 01:26:17.733 | INFO     | hookit.hookit:_listen:31 - Bye
```
