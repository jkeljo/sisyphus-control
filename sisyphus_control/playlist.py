from datetime import datetime
from typing import Any, Dict, ForwardRef, List, Optional, Type

from . import table
from .data import Model
from .log import log_data_change
from .track import Track
from .transport import TableTransport
from .sisbot_json import parse_bool


class Playlist:
    """Represents a playlist in the context of a table. If working with
multiple tables that have the same playlist loaded, multiple Playlist objects
will be created for that playlist -- one for each table that has it loaded."""

    parent: 'table.Table'

    def __init__(
            self,
            table: 'table.Table',
            transport: TableTransport,
            data: Model):
        self.parent = table
        self._transport: TableTransport = transport
        self._data: Model = data

    def __str__(self) -> str:
        return "{name} v{version} ({num_tracks} tracks)".format(
            name=self.name,
            version=self.version,
            num_tracks=len(self.tracks))

    @ property
    def id(self) -> str:
        return self._data["id"]

    @ property
    def name(self) -> str:
        return self._data["name"]

    @ property
    def tracks(self) -> List[Track]:
        return [
            self._get_track_by_index(index)
            for index in self._data["sorted_tracks"]]

    def get_tracks_named(self, name: str) -> List[Track]:
        return [track for track in self.tracks if track.name == name]

    def _get_track_by_index(self, index: int) -> Track:
        return Track(self, self._transport, self._data["tracks"][index])

    @ property
    def is_loop(self) -> bool:
        return parse_bool(self._data["is_loop"])

    @ property
    def is_shuffle(self) -> bool:
        return parse_bool(self._data["is_shuffle"])

    async def set_shuffle(self, value: bool) -> None:
        if self.parent.active_playlist != self:
            raise Exception(
                "set_shuffle may only be called on the active playlist")

        if value == self.is_shuffle:
            return

        await self._transport.post("set_shuffle",
                                   {"value": str(value).lower()})

    @ property
    def description(self) -> str:
        return self._data["description"]

    @ property
    def created_time(self) -> datetime:
        return _parse_date(self._data["created_at"])

    @ property
    def updated_time(self) -> datetime:
        return _parse_date(self._data["updated_at"])

    @ property
    def version(self) -> int:
        return int(self._data["version"])

    @ property
    def active_track(self) -> Optional[Track]:
        index = self._data["active_track_index"]
        if index < 0:
            return None
        return self._get_track_by_index(index)

    async def play(self, track: Optional[Track] = None) -> None:
        if track:
            if track.parent != self:
                raise ValueError("Track object is not part of this playlist")

            self._data["active_track_index"] = track.index_in_playlist
            self._data["active_track_id"] = track.id
        await self._transport.post("set_playlist", self._data.data)
        await self.parent.play()


def _parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
