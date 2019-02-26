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
```

```python
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
```

```
2019-02-26 16:04:57.689 | INFO     | hookit.hookit:async_listen:28 - Listening on port 8088
2019-02-26 16:05:01.671 | DEBUG    | hookit.hookit:_proxy:251 - Connected to httpbin.org:443
2019-02-26 16:05:01.672 | DEBUG    | hookit.hookit:_relay_client:114 - Connected to client c6f324e5ab404157b640c00e218ee160
2019-02-26 16:05:01.673 | INFO     | __main__:check:11 - HttpRequestHeader{POST, /anything, HTTP/1.1, {'accept': 'application/json, */*', 'accept-encoding': 'identity', 'connection': 'keep-alive', 'content-type': 'text/plain', 'transfer-encoding': 'chunked', 'host': 'localhost:8088', 'trailer': 'X-Hello, X-World', 'user-agent': 'HTTPie/1.0.2'}}
2019-02-26 16:05:01.673 | INFO     | __main__:check:12 - Let's call hook()
2019-02-26 16:05:02.301 | DEBUG    | hookit.hookit:_relay_chunked_data:81 - Chunk(length=3) relayed
2019-02-26 16:05:02.303 | DEBUG    | hookit.hookit:_relay_chunked_data:81 - Chunk(length=3) relayed
2019-02-26 16:05:02.304 | DEBUG    | hookit.hookit:_relay_chunked_data:81 - Chunk(length=6) relayed
2019-02-26 16:05:02.304 | DEBUG    | hookit.hookit:_relay_chunked_data:73 - Last chunk and trailer relayed
2019-02-26 16:05:02.609 | INFO     | __main__:hook:16 - hook() is called
2019-02-26 16:05:02.609 | INFO     | __main__:hook:17 - HttpResponseHeader{HTTP/1.1, 200, OK, {'access-control-allow-credentials': 'true', 'access-control-allow-origin': '*', 'content-type': 'application/json', 'date': 'Tue, 26 Feb 2019 08:05:02 GMT', 'server': 'nginx', 'content-length': '420', 'connection': 'keep-alive'}}
2019-02-26 16:05:02.610 | INFO     | __main__:hook:18 - {
  "args": {}, 
  "data": "foobar\r\nbazz", 
  "files": {}, 
  "form": {}, 
  "headers": {
    "Accept": "application/json, */*", 
    "Accept-Encoding": "identity", 
    "Content-Length": "12", 
    "Content-Type": "text/plain", 
    "Host": "httpbin.org", 
    "User-Agent": "HTTPie/1.0.2"
  }, 
  "json": null, 
  "method": "POST", 
  "origin": "58.37.73.70, 58.37.73.70", 
  "url": "https://httpbin.org/anything"
}

2019-02-26 16:05:02.610 | DEBUG    | hookit.hookit:_relay_server:204 - Working on task 3 in background
2019-02-26 16:05:02.612 | DEBUG    | hookit.hookit:_relay_client:142 - Connection to client c6f324e5ab404157b640c00e218ee160 closed
2019-02-26 16:05:02.613 | DEBUG    | hookit.hookit:_relay_server:230 - Connection to httpbin.org:443 closed by client
2019-02-26 16:05:05.615 | INFO     | __main__:background:23 - Task completed
2019-02-26 16:05:05.615 | DEBUG    | hookit.hookit:_worker:243 - Task queue c6f324e5ab404157b640c00e218ee160 closed
2019-02-26 16:05:28.797 | INFO     | hookit.hookit:async_listen:31 - Bye
```
