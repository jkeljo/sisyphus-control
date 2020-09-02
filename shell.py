import argparse
import asyncio
import aiohttp
import cmd
import io
import logging
import shlex
import sys
import threading

from sisyphus_control import Table


class SisyphusShell(cmd.Cmd):
    intro = "sisyphus_control CLI"
    prompt = "(sisyphus) "
    file = None

    def __init__(self, loop):
        super().__init__()
        self._loop = loop
        self._table = None
        self._running_cmd = False

    def _update_prompt(self):
        prompt = io.StringIO()
        prompt.write("\n{table_name} ({table_id}) - ".format(
            table_name=self._table.name, table_id=self._table.id))
        if not self._table.is_connected:
            prompt.write("disconnected\n")
        elif self._table.is_sleeping:
            prompt.write("asleep\n")
        else:
            prompt.write("{state}\n".format(state=self._table.state))
            playlist = self._table.active_playlist
            track = self._table.active_track
            if playlist:
                prompt.write("Playlist: {name} ({id})".format(
                    name=playlist.name, id=playlist.id))
                if playlist.is_shuffle:
                    prompt.write(" - shuffle")
                if playlist.is_loop:
                    prompt.write(" - loop")
                prompt.write("\n")
                if track:
                    prompt.write(
                        "Track: {index} - {name}\n".format(index=track.index_in_playlist, name=track.name))
            elif track:
                prompt.write("Track: {name}\n".format(name=track.name))

            if self._table.active_track_remaining_time_as_of:
                prompt.write("Time remaining: {remaining} (of {total}) (as of {as_of})\n".format(
                    remaining=self._table.active_track_remaining_time, total=self._table.active_track_total_time, as_of=self._table.active_track_remaining_time_as_of))

            prompt.write("Speed: {speed}\n".format(speed=self._table.speed))
            prompt.write("Brightness: {brightness}\n".format(
                brightness=self._table.brightness))
        prompt.write("(sisyphus) ")

        self.prompt = prompt.getvalue()

    def _update_received(self):
        self._update_prompt()
        if not self._running_cmd:
            print("\nState update received.\n{prompt}".format(
                prompt=self.prompt), end='')

    def postloop(self):
        if self._table:
            self._async_do(self._table.close())

    def precmd(self, line):
        self._running_cmd = True
        return line

    def postcmd(self, stop, *args):
        self._running_cmd = False
        return stop

    def emptyline(self):
        if self._table:
            self._async_do(self._table.refresh())

    def do_EOF(self, *args):
        return True

    def do_exit(self, *args):
        return True

    def do_quit(self, *args):
        return True

    def do_connect(self, addr):
        self._table = self._async_do(Table.connect(addr))
        self._table.add_listener(self._update_received)
        self._update_prompt()

    def do_state(self, *args):
        if self._expect_connected():
            print("Current state: ({awake}, {state})".format(
                name=self._table.name, awake="asleep" if self._table.is_sleeping else "awake", state=self._table.state))

    def do_play(self, arg):
        if self._expect_connected():
            args = shlex.split(arg)
            if len(args) >= 1:
                id = args[0]
                playlist = self._table.get_playlist_by_id(id)
                track = None
                if playlist is None:
                    track = self._table.get_track_by_id(id)
                    if track is None:
                        print("No playlist or track with id {id}".format(
                            id))
                        return
                    self._async_do(track.play())
                    return

                if len(args) >= 2:
                    track_index = int(args[1])
                    track = playlist.tracks[track_index]

                self._async_do(playlist.play(track))
            else:
                self._async_do(self._table.play())
            self._async_do(self._table.wait_for(
                lambda: self._table.state == 'playing'))

    def do_pause(self, *args):
        if self._expect_connected():
            self._async_do(self._table.pause())
            self._async_do(self._table.wait_for(
                lambda: self._table.state == 'paused'))

    def do_wakeup(self, *args):
        if self._expect_connected():
            self._async_do(self._table.wakeup())
            self._async_do(self._table.wait_for(
                lambda: not self._table.is_sleeping))

    def do_sleep(self, *args):
        if self._expect_connected():
            self._async_do(self._table.sleep())
            self._async_do(self._table.wait_for(
                lambda: self._table.is_sleeping))

    def do_speed(self, *args):
        if self._expect_connected():
            print("Current speed: {speed}".format(speed=self._table.speed))

    def do_set_speed(self, speed):
        if self._expect_connected():
            speed = float(speed)
            self._async_do(self._table.set_speed(speed))
            self._async_do(self._table.wait_for(
                lambda: self._table.speed == speed))

    def do_brightness(self, *args):
        if self._expect_connected():
            print("Current brightness: {brightness}".format(
                brightness=self._table.brightness))

    def do_set_brightness(self, brightness):
        if self._expect_connected():
            brightness = float(brightness)
            self._async_do(self._table.set_brightness(brightness))
            self._async_do(self._table.wait_for(
                lambda: self._table.brightness == brightness))

    def do_show_table(self, *args):
        if self._expect_connected():
            print_table(self._table)

    def do_show_playlists(self, *args):
        if self._expect_connected():
            playlists = self._table.playlists
            for playlist in playlists:
                print_playlist(playlist)
                print("\n")

    def do_show_playlist(self, id):
        if self._expect_connected():
            playlist = self._table.get_playlist_by_id(id)
            if playlist is None:
                print("No playlist with ID {id}".format(id=id))
            else:
                print_playlist(playlist)

    def _async_do(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def _expect_connected(self):
        if self._table is None:
            print("Must connect to a table first!")
            return False

        if not self._table.is_connected:
            print("Connection to {name} was lost.".format(
                name=self._table.name))

        return self._table.is_connected


def print_playlist(playlist):
    print("""Playlist {name}:
    ID: {id}
    Description: {description}
    Loop: {loop}
    Shuffle: {shuffle}
    Version: {version}
    Created: {created}
    Updated: {updated}
    Active Track: {active_track}
    Tracks:
        {tracks}""".format(
        id=playlist.id,
        name=playlist.name,
        description=playlist.description,
        loop=playlist.is_loop,
        shuffle=playlist.is_shuffle,
        version=playlist.version,
        created=playlist.created_time,
        updated=playlist.updated_time,
        active_track=playlist.active_track.name if playlist.active_track else "<none>",
        tracks="\n        ".join(
            ["{index} - {name}".format(index=track.index_in_playlist, name=track.name) for track in playlist.tracks])
    )

    )


async def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("addr")
    args = arg_parser.parse_args()

    await test(args.addr)


async def test(addr):
    async with aiohttp.ClientSession() as session:
        async with await Table.connect(addr, session) as table:
            table.add_listener(lambda: dump_table(table))
            dump_table(table)
            while True:
                await asyncio.sleep(1)

            """
            TODO: Provide a REPL
            TODO: Connect, dump table details
            TODO: Test different commands..
                play
                pause
                speed
                brightness
                shuffle
                loop
                sleep
                wake
                play a playlist(optionally from a specific track)
                """


def print_table(table):
    print("""Table {name}
    is_connected: {is_connected}
    id: {id}
    state: {state}
    brightness: {brightness}
    speed: {speed}
    is_sleeping: {is_sleeping}
    is_shuffle: {is_shuffle}
    is_loop: {is_loop}
    playlists:
    {playlists}
    active_playlist: {active_playlist}
    tracks:
    {tracks}
    active_track: {active_track}""".format(
        is_connected=table.is_connected,
        name=table.name,
        id=table.id,
        state=table.state,
        brightness=table.brightness,
        speed=table.speed,
        is_sleeping=table.is_sleeping,
        is_shuffle=table.is_shuffle,
        is_loop=table.is_loop,
        playlists='\n'.join(["\t{name} ({id})".format(name=playlist.name, id=playlist.id)
                             for playlist in table.playlists]),
        active_playlist=table.active_playlist.id,
        tracks='\n'.join(["\t{name} ({id})".format(name=track.name, id=track.id)
                          for track in table.tracks]),
        active_track=table.active_track.id,
    )
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    loop_thread = threading.Thread(target=loop.run_forever)
    loop_thread.start()

    cmd = SisyphusShell(loop)
    cmd.cmdloop()

    loop.call_soon_threadsafe(loop.stop)
    loop_thread.join()
    loop.close()
