Changelog
*********

sisyphus-control
++++++++++++++++

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