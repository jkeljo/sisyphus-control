from typing import List, Optional, Type, TypeVar

import asyncio
import logging

import aiohttp

from .log import log_data_change
from .playlist import Playlist
from .sisbot_json import bool
from .track import Track
from .transport import TableTransport, post


TableType = TypeVar('Table', bound='Table')

logger = logging.getLogger("sisyphus-control")


class Table:
    """Represents one Sisyphus table on the local network."""
    @classmethod
    async def find_table_ips(
            cls: Type[TableType],
            session: Optional[aiohttp.ClientSession] = None) -> List[str]:
        logger.info("Searching for tables...")
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

                logger.debug("Searching for tables on interface %s", local_addr)
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
                    logger.info("No tables found.")
                return result

    @classmethod
    async def connect(
            cls: Type[TableType],
            ip: str,
            session: Optional[aiohttp.ClientSession] = None) -> TableType:
        """Connect to the table with the given IP and return a Table object
        that can be used to control it"""
        table = Table()
        table._transport = TableTransport(
            ip,
            callback=table._try_update_table_state,
            session=session)
        connect_result = await table._transport.post("connect")
        await table._try_update_table_state(connect_result)

        logger.debug("Connected to %s (%s)", table.name, ip)
        return table

    def __init__(self):
        self._transport = None
        self._data = None
        self._playlists_by_id = {}
        self._tracks_by_id = {}
        self._listeners = []
        self._connected = False

    async def close(self):
        result = await self._transport.close()
        logger.info(
            "Closed connection to %s (%s)",
            self.name,
            self._transport.ip)
        return result

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False

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

    async def pause(self):
        if self.state != 'paused':
            await self._try_update_table_state(
                await self._transport.post("pause"))

    async def play(self):
        if self.state != 'playing':
            await self._try_update_table_state(
                await self._transport.post("play"))

    @property
    def is_sleeping(self):
        return bool(self._data["is_sleeping"])

    async def sleep(self):
        if not self.is_sleeping:
            await self._try_update_table_state(
                await self._transport.post("sleep_sisbot"))

    async def wakeup(self):
        if self.is_sleeping:
            await self._try_update_table_state(
                await self._transport.post("wake_sisbot"))


    @property
    def playlists(self) -> List[Playlist]:
        return [
            self.get_playlist_by_id(playlist_id)
            for playlist_id in self._data["playlist_ids"]]

    def get_playlists_named(self, name: str) -> List[Playlist]:
        return [
            playlist
            for playlist in self.playlists if playlist.name == name]

    def get_playlist_by_id(self, playlist_id: str) -> Playlist:
        return self._playlists_by_id[playlist_id]

    @property
    def tracks(self) -> List[Track]:
        return [
            self.get_track_by_id(track_id)
            for track_id in self._data["track_ids"]]

    def get_tracks_named(self, name: str) -> List[Track]:
        return [track for track in self.tracks if track.name == name]

    def get_track_by_id(self, track_id: int) -> Track:
        return self._tracks_by_id[track_id]

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

        return Track(owner, self._transport, self._data["active_track"])

    @property
    def brightness(self) -> float:
        return self._data["brightness"]

    async def set_brightness(self, level: float):
        if not 0 <= level <= 1.0:
            raise ValueError("Brightness must be between 0 and 1 inclusive")
        result = await self._transport.post(
            "set_brightness",
            {"value": level})
        if not await self._try_update_table_state(result):
            self._data["brightness"] = result

    @property
    def speed(self) -> float:
        return self._data["speed"]

    async def set_speed(self, speed: float):
        if not 0 <= speed <= 1.0:
            raise ValueError("Speed must be between 0 and 1 inclusive")
        result = await self._transport.post(
            "set_speed",
            {"value": speed})
        if not await self._try_update_table_state(result):
            self._data["speed"] = result

    @property
    def is_shuffle(self) -> bool:
        return bool(self._data["is_shuffle"])

    async def set_shuffle(self, value: bool):
        if not self.active_playlist:
            raise Exception("Cannot shuffle when there is no active playlist")

        await self.active_playlist.set_shuffle(value)
        self._data["is_shuffle"] = str(value).lower()

    @property
    def is_loop(self) -> bool:
        return bool(self._data["is_loop"])

    async def set_loop(self, value: bool) -> None:
        result = await self._transport.post(
            "set_loop",
            {"value": str(value).lower()})
        if not await self._try_update_table_state(result):
            self._data["is_loop"] = result

    async def refresh(self) -> None:
        await self._try_update_table_state(await self._transport.post("state"))

    def add_listener(self, listener):
        self._listeners.append(listener)

    def remove_listener(self, listener):
        self._listeners.remove(listener)

    async def _notify_listeners(self):
        listeners = list(self._listeners)
        for listener in listeners:
            await asyncio.coroutine(listener)()

    async def _try_update_table_state(self, table_result):
        should_notify_listeners = False
        if isinstance(table_result, tuple):
            table_result = table_result[0]

        if isinstance(table_result, dict):
            table_result = [table_result]

        if isinstance(table_result, list):
            self._connected = True
            for data in table_result:
                data_type = data["type"]
                id = data["id"]
                if data_type == "sisbot":
                    log_data_change(self._data, data)
                    if self._data == data:
                        # Debounce; the table tends to send a lot of events
                        continue
                    self._data = data
                    should_notify_listeners = True
                elif data_type == "playlist":
                    if id in self._playlists_by_id:
                        if self.get_playlist_by_id(id)._set_data(data):
                            should_notify_listeners = True
                    else:
                        log_data_change(None, data)
                        new_playlist = Playlist(self, self._transport, data)
                        self._playlists_by_id[id] = new_playlist
                        should_notify_listeners = True
                elif data_type == "track":
                    if id in self._tracks_by_id:
                        if self.get_track_by_id(id)._set_data(data):
                            should_notify_listeners = True
                    else:
                        log_data_change(None, data)
                        new_track = Track(self, self._transport, data)
                        self._tracks_by_id[id] = new_track
                        should_notify_listeners = True
        elif table_result is None:
            self._connected = False
            should_notify_listeners = True
        else:
            return False

        playlist_ids = list(self._playlists_by_id.keys())
        for playlist_id in playlist_ids:
            if playlist_id not in self._data["playlist_ids"]:
                del self._playlists_by_id[playlist_id]
                should_notify_listeners = True

        track_ids = list(self._tracks_by_id.keys())
        for track_id in track_ids:
            if track_id not in self._data["track_ids"]:
                del self._tracks_by_id[track_id]
                should_notify_listeners = True

        if should_notify_listeners:
            await self._notify_listeners()

        return True



# noinspection PyBroadException
async def _ping_table(
        ip,
        session: Optional[aiohttp.ClientSession] = None) -> Optional[str]:
    try:
        await post(
            ip,
            "exists",
            session=session,
            timeout=1.25)
        logger.info("Found a table at %s", ip)
        return ip
    except Exception as e:
        logger.debug("%s: %s", ip, e)
        return None
