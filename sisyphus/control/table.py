from typing import List, Optional, Type, TypeVar

import asyncio

from .playlist import Playlist
from .track import Track
from .transport import TableTransport, post


TableType = TypeVar('Table', bound='Table')


class Table:
    """Represents one Sisyphus table on the local network."""
    @classmethod
    async def find_table_ips(cls: Type[TableType]) -> List[str]:
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

                root = local_addr[:local_addr.rindex('.') + 1]
                pings = []
                for i in range(1, 256):
                    table_addr = root + str(i)
                    if table_addr != local_addr and table_addr != broadcast:
                        pings.append(asyncio.Task(_ping_table(table_addr)))

                return [ip for ip in await asyncio.gather(*pings) if ip]

    @classmethod
    async def connect(cls: Type[TableType], ip: str) -> TableType:
        """Connect to the table with the given IP and return a Table object
        that can be used to control it"""
        transport = TableTransport(ip)
        connect_result = await transport.post("connect")
        return Table(transport, connect_result)

    def __init__(self, transport: TableTransport, connect_result):
        self._transport = transport
        self._data = None
        self._playlists = []
        self._tracks = []

        for data in connect_result:
            data_type = data["type"]
            if data_type == "sisbot":
                assert self._data is None
                self._data = data
            elif data_type == "playlist":
                self._playlists.append(Playlist(self, self._transport, data))
            elif data_type == "track":
                self._tracks.append(Track(self, self._transport, data))

        self._playlists_by_id = {
            playlist.id: playlist for playlist in self._playlists}
        self._tracks_by_id = {
            track.id: track for track in self._tracks}

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
            self._data = await self._transport.post("pause")

    async def play(self):
        if self.state != 'playing':
            self._data = await self._transport.post("play")

    @property
    def playlists(self) -> List[Playlist]:
        return self._playlists

    def get_playlists_named(self, name: str) -> List[Playlist]:
        return [
            playlist
            for playlist in self.playlists if playlist.name == name]

    def get_playlist_by_id(self, playlist_id: int) -> Playlist:
        return self._playlists_by_id[playlist_id]

    @property
    def tracks(self) -> List[Track]:
        return self._tracks

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

        active_track_id = self._data["active_track"]["id"]
        if active_track_id == "false":
            return None

        return owner.get_track_by_id(active_track_id)

    @property
    def brightness(self) -> float:
        return self._data["brightness"]

    async def set_brightness(self, level: float):
        if not 0 <= level <= 1.0:
            raise ValueError("Brightness must be between 0 and 1 inclusive")
        self._data["brightness"] = await self._transport.post(
            "set_brightness",
            {"value": level})

    @property
    def speed(self) -> float:
        return self._data["speed"]

    async def set_speed(self, speed: float):
        if not 0 <= speed <= 1.0:
            raise ValueError("Speed must be between 0 and 1 inclusive")
        self._data["speed"] = await self._transport.post(
            "set_speed",
            {"value": speed})

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
        self._data["is_loop"] = await self._transport.post(
            "set_loop",
            {"value": str(value).lower()})

    async def refresh(self) -> None:
        self._data = await self._transport.post("state")


# noinspection PyBroadException
async def _ping_table(ip) -> Optional[str]:
    try:
        await post(ip, "exists", timeout=1.25)
        return ip
    except Exception as e:
        return None
