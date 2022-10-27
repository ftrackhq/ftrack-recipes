..
    :copyright: Copyright (c) 2018 ftrack

============================
Cascade Thumbnails to Parent
============================

When publishing a new asset, it could be convenient to have the thumbnail of the newly published entity bubble up to the parent entity and (optionally) associated task.
This script will show you how to be able to intercept thumbnail creation at publish time and set the same thumbnail ID on related entities.

Scope
-----

* Check thumbnails creation on AssetVersions.
* Update the thumbnail on parent entities.


Install and setup
-----------------

1. Make the cascade plugin available to the API either by setting the
FTRACK_EVENT_PLUGIN_PATH environment variable to <custom-location-folder>.
Alternatively use the plugin_paths in the ftrack_api.Session constructor and
point it to <custom-location-folder>.


Dependencies
------------

* ftrack-python-api
