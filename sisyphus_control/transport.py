from typing import Any, Dict, Optional
from socketIO_client_nexus import SocketIO, SocketIONamespace

import aiohttp
import asyncio
import json

class TableTransport:
    def __init__(
            self,
            ip,
            callback = None,
            session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._ip = ip
        self._callback = callback
        self._wants_to_close = False
        self._event_loop = asyncio.get_event_loop()
        self._socket_closed = self._event_loop.run_in_executor(
            None,
            lambda: self._run_socket())

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False

    @property
    def ip(self):
        return self._ip

    async def close(self):
        if self._socket_closed:
            self._wants_to_close = True
            await self._socket_closed

    async def post(
            self,
            endpoint: str,
            data: Dict[str, Any] = None,
            timeout: float = 5):
        return await post(
            self._ip,
            endpoint,
            data,
            timeout,
            session=self._session)

    def _run_socket(self):
        transport = self
        class SisyphusNamespace(SocketIONamespace):
            def on_disconnect(self):
                transport._on_disconnect()

            def on_set(self, *args):
                transport._on_set(args)

        with SocketIO(
            self._ip,
            3002,
            SisyphusNamespace,
            transports=['websocket']) as socket:
            while not self._wants_to_close:
                try:
                    socket.wait(seconds=1)
                except IndexError as e:
                    # IndexError can happen on disconnects; eat it so that
                    # SocketIO can reconnect
                    pass

    def _on_set(self, *args):
        if self._callback:
            asyncio.run_coroutine_threadsafe(
                asyncio.coroutine(self._callback)(*args),
                self._event_loop).result()

    def _on_disconnect(self):
        if self._callback:
            asyncio.run_coroutine_threadsafe(
                asyncio.coroutine(self._callback)(None),
                self._event_loop).result()


async def post(
        ip: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        timeout: float = 5,
        session: Optional[aiohttp.ClientSession] = None):

    if not session:
        async with aiohttp.ClientSession() as session:
            return await post(ip, endpoint, data, timeout, session)

    data = data or {}
    try:
        url = "http://{ip}/sisbot/{endpoint}".format(ip=ip,
                                                     endpoint=endpoint)

        json_data = {
            "data": data,
        }

        form_data = {"data": json.dumps(json_data)}

        async with session.post(
                url,
                data=form_data,
                timeout=aiohttp.ClientTimeout(sock_connect=timeout)) as r:
            r = await r.json()
            if r["err"]:
                raise Exception(r["error"])

            return r["resp"]
    except:
        raise
