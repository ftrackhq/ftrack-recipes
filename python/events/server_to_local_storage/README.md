..
    :copyright: Copyright (c) 2019 ftrack

=======================
Server to local storage
=======================

When uploading files through the web interface, these will be registered in the
ftrack.server location. This event will intercept the upload and when is saved
on the server it'll also transfer it on the main local storage making the uploaded
file available locally.


Scope
-----

* Transfer data between locations

Install and setup
-----------------

1. Make the location plugin available to the API either by setting the 
FTRACK_EVENT_PLUGIN_PATH environment variable to <custom-location-folder>. 

Dependencies
------------

* None

