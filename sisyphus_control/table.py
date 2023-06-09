from datetime import datetime, timedelta, timezone
from types import TracebackType
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type, TypeVar, Union

import asyncio
import logging

import aiohttp

from .data import Collection, Model
from .log import log_data_change
from .playlist import Playlist
from .sisbot_json import parse_bool
from .track import Track
from .transport import TableTransport, post
from .util import ensure_coroutine


_LOGGER = logging.getLogger("sisyphus-control")

TableListenerType = Union[Callable[[], None], Callable[[], Awaitable[None]]]


class Table:
    """Represents one Sisyphus table on the local network."""
    @classmethod
    async def find_table_ips(
            cls: Type['Table'],
            session: Optional[aiohttp.ClientSession] = None) -> List[str]:
        _LOGGER.info("Searching for tables...")
        import netifaces

        for iface in netifaces.interfaces():
            ifaddresses = netifaces.ifaddresses(iface)
            if netifaces.AF_INET not in ifaddresses:
                continue

            for ifaddress in ifaddresses[netifaces.AF_INET]:
                local_addr = ifaddress["addr"]
                if local_addr == '127.0.0.1':
                    continue

                broadcast = ifaddress["broadcast"]

                _LOGGER.debug(
                    "Searching for tables on interface %s", local_addr)
                root = local_addr[:local_addr.rindex('.') + 1]
                pings = []
                for i in range(1, 256):
                    table_addr = root + str(i)
                    if table_addr != local_addr and table_addr != broadcast:
                        pings.append(
                            asyncio.Task(
                                _ping_table(table_addr, session=session)))

                result = [ip for ip in await asyncio.gather(*pings) if ip]
                if not result:
                    _LOGGER.info("No tables found.")
                return result
        return []

    @classmethod
    async def connect(
            cls: Type['Table'],
            ip: str,
            session: Optional[aiohttp.ClientSession] = None) -> 'Table':
        """Connect to the table with the given IP and return a Table object
        that can be used to control it"""
        table = Table()
        table._transport = TableTransport(
            ip,
            callback=table._try_update_table_state,
            session=session)
        await table._transport.post("connect")

        _LOGGER.debug("Connected to %s (%s)", table.name, ip)
        return table

    def __init__(self):
        self._transport: Optional[TableTransport] = None
        self._collection: Collection = Collection()
        self._data: Model = Model({})
        self._listeners: List[TableListenerType] = []
        self._updated: asyncio.Event = asyncio.Event()
        self._remaining_time: timedelta = timedelta()
        self._total_time: timedelta = timedelta()
        self._remaining_time_as_of: Optional[datetime] = None
        self._connected: bool = False
        self._collection.add_listener(self._notify_listeners)

    async def close(self) -> None:
        if self._transport is not None:
            await self._transport.close()
            _LOGGER.info(
                "Closed connection to %s (%s)",
                self.name,
                self._transport.ip)

    async def __aenter__(self) -> 'Table':
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]) -> bool:
        await self.close()
        return False

    @property
    def data(self) -> Model:
        return self._data

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def id(self) -> str:
        return self._data["id"]

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def firmware_version(self) -> Optional[str]:
        # Data also has a "firmware_version", but it appears to always be 1.0
        return self._data.get("software_version")

    @property
    def mac_address(self) -> Optional[str]:
        return self._data.get("mac_address")

    @property
    def state(self) -> str:
        """
Returns the current state of the table. The following is a (possibly
incomplete) list of possible values:
  - playing: the table is currently playing a track or playlist
  - paused: the table is paused in the midst of playing a track or playlist
  - homing: the table is moving the ball to the center position, typically
    in response to being given a new track/playlist to play
  - waiting: the table has finished any tracks or playlists it has been told to
    play and is awaiting further instructions
"""
        return self._data["state"]

    async def pause(self) -> None:
        if self.state != 'paused':
            await self._get_transport().post("pause")

    async def play(self) -> None:
        if self.state != 'playing':
            await self._get_transport().post("play")

    @property
    def is_sleeping(self) -> bool:
        return parse_bool(self._data["is_sleeping"])

    async def sleep(self) -> None:
        if not self.is_sleeping:
            await self._get_transport().post("sleep_sisbot")

    async def wakeup(self) -> None:
        if self.is_sleeping:
            await self._get_transport().post("wake_sisbot")

    @property
    def playlists(self) -> List[Playlist]:
        return list(filter(None, [
            self.get_playlist_by_id(playlist_id)
            for playlist_id in self._data["playlist_ids"]]))

    def get_playlists_named(self, name: str) -> List[Playlist]:
        return [
            playlist
            for playlist in self.playlists if playlist.name == name]

    def get_playlist_by_id(self, playlist_id: str) -> Optional[Playlist]:
        model = self._collection.get(playlist_id)
        if model is None or model["type"] != "playlist":
            return None
        return Playlist(self, self._get_transport(), model)

    @property
    def tracks(self) -> List[Track]:
        return list(filter(None, [
            self.get_track_by_id(track_id)
            for track_id in self._data["track_ids"]]))

    def get_tracks_named(self, name: str) -> List[Track]:
        return [track for track in self.tracks if track.name == name]

    def get_track_by_id(self, track_id: int) -> Optional[Track]:
        model = self._collection.get(track_id)
        if model is None or model["type"] != "track":
            return None
        return Track(self, self._get_transport(), model)

    @property
    def active_playlist(self) -> Optional[Playlist]:
        active_playlist_id = self._data["active_playlist_id"]
        if active_playlist_id == "false":
            return None

        return self.get_playlist_by_id(active_playlist_id)

    @property
    def active_track(self) -> Track:
        owner = self
        if self.active_playlist:
            owner = self.active_playlist

        return Track(owner, self._get_transport(), self._data["active_track"])

    @property
    def brightness(self) -> float:
        return self._data["brightness"]

    async def set_brightness(self, level: float) -> None:
        if not 0 <= level <= 1.0:
            raise ValueError("Brightness must be between 0 and 1 inclusive")
        await self._get_transport().post(
            "set_brightness",
            {"value": level})

    @property
    def speed(self) -> float:
        return self._data["speed"]

    async def set_speed(self, speed: float) -> None:
        if not 0 <= speed <= 1.0:
            raise ValueError("Speed must be between 0 and 1 inclusive")
        await self._get_transport().post(
            "set_speed",
            {"value": speed})

    @property
    def is_shuffle(self) -> bool:
        return parse_bool(self._data["is_shuffle"])

    async def set_shuffle(self, value: bool) -> None:
        if not self.active_playlist:
            raise Exception("Cannot shuffle when there is no active playlist")

        await self.active_playlist.set_shuffle(value)
        self._data["is_shuffle"] = str(value).lower()

    @property
    def is_loop(self) -> bool:
        return parse_bool(self._data["is_loop"])

    async def set_loop(self, value: bool) -> None:
        await self._get_transport().post(
            "set_loop",
            {"value": str(value).lower()})

    @property
    def active_track_total_time(self) -> timedelta:
        return self._total_time

    @property
    def active_track_remaining_time(self) -> timedelta:
        return self._remaining_time

    @property
    def active_track_remaining_time_as_of(self) -> Optional[datetime]:
        return self._remaining_time_as_of

    async def refresh(self) -> None:
        await self._get_transport().post("state")
        await self._get_transport().post("get_track_time")

    async def wait_for(self, pred: Callable[[], bool]) -> None:
        while True:
            await self._updated.wait()
            self._updated.clear()
            if pred():
                return

    def add_listener(self, listener: TableListenerType) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: TableListenerType) -> None:
        self._listeners.remove(listener)

    async def _notify_listeners(self) -> None:
        listeners = list(self._listeners)
        for listener in listeners:
            await ensure_coroutine(listener)()  # type: ignore
        self._updated.set()

    def _get_transport(self) -> TableTransport:
        if self._transport is not None:
            return self._transport

        raise Exception("Table not connected")

    async def _try_update_table_state(self, table_result: Optional[List[Dict[str, Any]]]) -> bool:
        if isinstance(table_result, dict):
            table_result = [table_result]

        if isinstance(table_result, list):
            self._connected = True
            for data in table_result:
                if "id" in data:
                    id = data["id"]
                    await self._collection.add(Model(data))
                    data = self._collection.get(id)
                    assert data is not None
                    if not self._data and data["type"] == "sisbot":
                        self._data = data
                elif "remaining_time" in data:
                    self._remaining_time = timedelta(
                        milliseconds=data["remaining_time"])
                    self._total_time = timedelta(
                        milliseconds=data["total_time"])
                    self._remaining_time_as_of = datetime.now(timezone.utc)
                    await self._notify_listeners()
                else:
                    continue

        elif table_result is None:
            self._connected = False
            await self._notify_listeners()
        else:
            return False

        return True


# noinspection PyBroadException
async def _ping_table(
        ip: str,
        session: Optional[aiohttp.ClientSession] = None) -> Optional[str]:
    try:
        await post(
            ip,
            "exists",
            session=session,
            timeout=1.25)
        _LOGGER.info("Found a table at %s", ip)
        return ip
    except Exception as e:
        _LOGGER.debug("%s: %s", ip, e)
        return None
