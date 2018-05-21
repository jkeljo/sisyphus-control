from typing import Any, Dict
from socketIO_client_nexus import SocketIO, SocketIONamespace

import aiohttp
import asyncio
import json

class TableTransport:
    def __init__(self, ip, callback = None):
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
        return await post(self._ip, endpoint, data, timeout)

    def _run_socket(self):
        transport = self
        class SisyphusNamespace(SocketIONamespace):
            def on_set(self, *args):
                transport._on_set(args)

        socket = SocketIO(
            self._ip,
            3002,
            SisyphusNamespace,
            transports=['websocket'])

        while not self._wants_to_close:
            socket.wait(seconds=1)

        socket.disconnect()

    def _on_set(self, *args):
        if self._callback:
            self._event_loop.call_soon(self._callback, *args)


async def post(
        ip: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        timeout: float = 5):
    data = data or {}
    try:
        url = "http://{ip}/sisbot/{endpoint}".format(ip=ip,
                                                     endpoint=endpoint)

        json_data = {
            "data": data,
        }

        form_data = {"data": json.dumps(json_data)}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form_data,
                                    timeout=timeout) as r:
                r = await r.json()
                if r["err"]:
                    raise Exception(r["error"])

                return r["resp"]
    except:
        raise
