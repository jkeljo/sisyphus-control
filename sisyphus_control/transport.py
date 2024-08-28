from types import TracebackType
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Type

import aiohttp
import asyncio
import json
import socketio_v4 as socketio

TransportCallback = Callable[[Optional[List[Dict[str, Any]]]], Awaitable[None]]


class TableTransport:
    def __init__(
        self,
        ip: str,
        callback: Optional[TransportCallback] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self._session = session
        self._ip = ip
        self._callback = callback
        self._wants_to_close = False
        self._event_loop = asyncio.get_event_loop()
        self._socket_closed = self._event_loop.create_task(self._run_socket())

    async def __aenter__(self) -> "TableTransport":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        await self.close()
        return False

    @property
    def ip(self) -> str:
        return self._ip

    async def close(self) -> None:
        if self._socket_closed:
            self._wants_to_close = True
            await self._socket_closed

    async def post(
        self, endpoint: str, data: Dict[str, Any] = None, timeout: float = 5
    ) -> None:
        response = await post(self._ip, endpoint, data, timeout, session=self._session)
        if self._callback:
            await self._callback(response)

    async def _run_socket(self) -> None:
        sio = socketio.AsyncClient()

        @sio.event
        async def disconnect() -> None:
            if self._callback is not None:
                await self._callback(None)

        @sio.event
        async def set(updates: List[Dict[str, Any]]) -> None:
            if self._callback is not None:
                await self._callback(updates)

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
    session: Optional[aiohttp.ClientSession] = None,
) -> List[Dict[str, Any]]:

    if not session:
        async with aiohttp.ClientSession() as session:
            return await post(ip, endpoint, data, timeout, session)

    data = data or {}
    try:
        url = "http://{ip}/sisbot/{endpoint}".format(ip=ip, endpoint=endpoint)

        json_data = {
            "data": data,
        }

        form_data = {"data": json.dumps(json_data)}

        async with session.post(
            url, data=form_data, timeout=aiohttp.ClientTimeout(sock_connect=timeout)
        ) as r:  # type: ignore
            r = await r.json()
            if r["err"]:
                raise Exception(r["err"])

            return r["resp"]
    except:
        raise
