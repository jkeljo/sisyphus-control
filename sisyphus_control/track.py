from enum import IntEnum
from typing import Any, Dict, Union

from sisyphus_control.data import Model

from . import table
from . import playlist
from .log import log_data_change
from .transport import TableTransport


class Track:
    """Represents a track in the context of a Playlist or Table.

Every track known to a table is represented by a Track object whose parent
is the appropriate Table object.

Every track in a playlist is represented by a Track object whose parent is the
Playlist. If a given track appears multiple times in the playlist, each
occurrence is represented by its own Track object."""
    class ThumbnailSize(IntEnum):
        SMALL = 50
        MEDIUM = 100
        LARGE = 400

    def __init__(self, parent: Union['playlist.Playlist', 'table.Table'], transport: TableTransport, data: Model):
        self.parent: Union['playlist.Playlist', 'table.Table'] = parent
        self._transport: TableTransport = transport
        self._data: Model = data

    def __str__(self) -> str:
        return self.name

    @property
    def id(self) -> str:
        """UUID of the track design, not of the Track instance."""
        return self._data["id"]

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def is_in_playlist(self) -> bool:
        return "_index" in self._data

    @property
    def index_in_playlist(self) -> int:
        """
This track's index in the owning playlist when the playlist is not shuffled"""
        return self._data["_index"]

    async def play(self) -> None:
        if not self.is_in_playlist:
            await self._transport.post("set_track", self._data.data)
            await self.parent.play()
        else:
            # Ignore type error; if it's in a playlist the parent is the playlist, and that play() method takes a track
            await self.parent.play(self)  # type: ignore

    def get_thumbnail_url(self, size: int) -> str:
        return "http://{host}:3001/thumbnail/{size}/{id}".format(
            host=self._transport.ip,
            size=size,
            id=self.id)
