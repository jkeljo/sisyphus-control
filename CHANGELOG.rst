Changelog
*********

sisyphus-control
++++++++++++++++

[3.0] - 2020-09-06
==================
Added
-----
* Track remaining/total time support (requires recent firmware)
* Test shell program
Changed
-------
* Reworked the data model to match how Sisyphus itself does it. This fixes crashes that were occurring working with tables that have the latest firmware, but may break things with older firmwares.
* Switched to `python-socketio` for Socket.IO support, as it is more actively maintained than `SocketIO-client-nexus`.
* Switched to VSCode for development

[2.2.1] - 2019-08-17
====================
Fixed
-----
* Fixed a crash when closing the socket coincides with shutting down the event loop

[2.2] - 2019-03-27
==================
Added
-----
* Property for getting the table's UUID
* Handling of intermittent connections

[2.1] - 2018-07-12
====================

Added
-----
* You can now pass in your own ``aiohttp.ClientSession``
* Added some more log statements

Changed
-------
* Callbacks on the Table object may be coroutines or normal functions
* Timeouts are now properly treated as socket connect timeouts instead of total time timeouts
* SocketIO socket properly closed on exception

[2.0] - 2018-05-20
====================

Changed
-------
* Changed the package name from ``sisyphus.control`` to ``sisyphus_control`` so as to be more ecosystem-friendly

[1.1.1] - 2018-05-10
====================

Changed
-------
Updated requirements to newer versions and pruned unnecessary ones.

[1.1.0] - 2018-05-10
====================

Added
-----
* ``name`` property on ``Table``
* ``get_thumbnail_url`` method on ``Track``

Changed
-------
* ``Table.active_track`` works now

Removed
-------
* Don't force a particular logging config

[1.0.1] - 2018-05-03
====================

Added
-----
* Missing dependency in ``setup.py``

[1.0.0] - 2018-05-01
====================

Added
-----
* Support for firmware 1.2.0 (``is_sleeping``, ``sleep``, and ``wakeup`` methods on ``Table``)
* Change notifications, including when changes are made from another app (``add_listener`` and ``remove_listener`` methods on ``Table``)

Changed
-------
* ``Table.close`` must now be called when the ``Table`` is no longer needed, either directly or via ``async with``

Removed
-------
* ``Playlist.get_track_by_index`` (doesn't make sense; ``get_tracks`` already returns the tracks in sorted order)

[0.1.2] - 2018-03-07
====================

Changed
-------
* More complete hotfix for firmware 1.2.0

[0.1.1] - 2018-03-07
====================

Changed
-------
* Hotfix for protocol changes in firmware 1.2.0

[0.1.0] - 2018-02-19
====================

Just getting this code out there. I've done some manual testing locally but haven't yet dreamt up a reasonable way to
automate the tests. Next step is to hook this in to Home Assistant!