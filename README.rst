====================
``sisyphus-control``
====================

Control your `Sisyphus Kinetic Art Table <https://www.sisyphus-industries.com>`_
from Python 3.6 with ``asyncio``!

This initial release is mainly targeting the functionality needed for basic integrations with home automation systems such as `Home Assistant <https://www.home-assistant.io/components/sisyphus/>`_:

* Status queries (playing/paused/current playlist/current/track/brightness/speed)
* Play controls (play/pause/shuffle/loop/set playlist/set track)
* Table controls (movement speed, LED brightness)

*************
Usage example
*************

Finding tables on your network
==============================
To find the IP addresses of all tables on your local network. This is a very naive search; it assumes your subnet
mask is ``255.255.255.0``::

  from sisyphus_control import Table

  ip_addrs = await Table.find_table_ips()

Once you know the IP address, connect to the table::

  async with await Table.connect(ip_addr) as Table:
    # Do stuff here

Change notifications
====================
Register for state change notifications::

  table.add_listener(my_listener)

Basic controls
==============
In addition to a bunch of properties for querying the current state of the table, ``Table`` has several methods that
allow simple control::

  await table.set_brightness(1.0)  # Set maximum LED brightness
  await table.set_speed(0.5)  # Set half speed
  await table.play()  # Resume playing (if not already playing)

Working with playlists and tracks
=================================
``Playlist`` and ``Track`` objects represent playlists and tracks, respectively. The following code will start playing
the Default Playlist, beginning at the track named "Hep" (note that neither playlists nor tracks are required to be
uniquely named)::

  default_playlist = table.get_playlists_named("Default Playlist")[0]
  hep_track = default_playlist.get_tracks_named("Hep")[0]
  await hep_track.play()

********************
Future opportunities
********************

The following features would be reasonable to include; I'll happily accept pull requests:

* Playlist editing
* Upload tracks to table
* Track thumbnail rendering
* Table administration (wifi settings, etc.)
* Interactions with Sisyphus cloud
