..
    :copyright: Copyright (c) 2018 ftrack

===================
Customise Structure
===================

When publishing files with the ftrack-python-api or ftrack Connect a location 
plugin is used to determine where to write the output file. 
This example can be as boilerplate when creating a custom location to be used in
ftrack Connect or through the API.

A location consist of an accessor that is used to read and write the file from 
the storage, and a structure plugin that is used to generate the target path 
given an ftrack component. 
In this example we use a DiskAccessor from the ftrack-python-api, and a 
Structure plugin that we have copied from the StandardStructure in the 
ftrack-python-api.

Scope
-----

* Customise Structure
* Register custom structure


Install and setup
-----------------

1. Update the DISK_PREFIX variable in 
<custom-location-folder>/location/custom_location_plugin.py to the root path 
where you want to publish to.

2. Make the location plugin available to the API either by setting the 
FTRACK_EVENT_PLUGIN_PATH environment variable to <custom-location-folder>. 
Alternatively use the plugin_paths in the ftrack_api.Session constructor 
and point it to <custom-location-folder>.

Customise
---------

To modify the file names and paths that are generated when you publish to this 
location, you will want to modify the sturcture plugin's get_resource_identifier 
method. The structure plugin is found in location/structure.py.

Dependencies
------------

* None

