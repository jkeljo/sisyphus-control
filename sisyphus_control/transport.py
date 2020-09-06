from typing import Any, Dict, Optional

import aiohttp
import asyncio
import json
import socketio


class TableTransport:
    def __init__(
            self,
            ip,
            callback=None,
            session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._ip = ip
        self._callback = callback
        self._wants_to_close = False
        self._event_loop = asyncio.get_event_loop()
        self._socket_closed = self._event_loop.create_task(self._run_socket())

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

    async def _run_socket(self):
        sio = socketio.AsyncClient()

        @sio.event
        async def disconnect():
            await self._callback(None)

        @sio.event
        async def set(*args):
            await self._callback(args)

        await sio.connect("http://{ip}:{port}".format(ip=self._ip, port=3002))

        while not self._wants_to_close:
            await sio.sleep(1)

        await sio.disconnect()
        await sio.wait()


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
