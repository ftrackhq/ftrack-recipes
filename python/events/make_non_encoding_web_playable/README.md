..
    :copyright: Copyright (c) 2019 ftrack

==============================
Make non encoding web playable
==============================

This event replace and override the default make_web_playable event hook provided
with ftrack-connect, to make able the users to upload as playable any video already
correctly encoded.


Scope
-----

* Override default hook


Install and setup
-----------------

a. Make the location plugin available to the API either by setting the 
FTRACK_EVENT_PLUGIN_PATH environment variable to <custom-location-folder>. 


Dependencies
------------

* Require FFMPEG and FFPROBE available on the filesystem path.

