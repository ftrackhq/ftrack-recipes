..
    :copyright: Copyright (c) 2020 ftrack

======================
Encode Image Sequences
======================

This event overrides the default make_web_playable event hook provided
with ftrack-connect to enable the users to review image sequences by
converting them to videos.

Scope
-----

* Subscribe to proper event with high priority
* If image sequence, shoot a movie with ffmpeg and upload
* Stop event so default hook doesn't run


Install and setup
-----------------

1) Make the required executables available on the system path
2) Please refer to the main ftrack-recipes python guide to enable the
   event listener


Dependencies
------------

* ftrack_python_api
* Requires ffmpeg available on the filesystem path.
