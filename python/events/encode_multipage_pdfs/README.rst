..
    :copyright: Copyright (c) 2020 ftrack

=====================
Encode Multipage PDFs
=====================

Currently, PDFs uploaded through Connect or the API are rendered as an image.
The new player supports paging through multipage PDFs, but requires that the
relevant Component have a certain metadata key. We present here a replacement
for the default hook in Connect which replicates functionality found in the web
UI.

Scope
-----

* Subscribe to proper event with high priority
* Upload and tag published PDF
* Stop event so default hook doesn't run


Install and setup
-----------------

1. Make the plugin available to the API either by setting the
FTRACK_EVENT_PLUGIN_PATH environment variable to <custom-location-folder>.
Alternatively use the plugin_paths in the ftrack_api.Session constructor and
point it to <custom-location-folder>.


Dependencies
------------

* ftrack_python_api
