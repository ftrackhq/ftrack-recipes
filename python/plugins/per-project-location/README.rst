..
    :copyright: Copyright (c) 2014-2020 ftrack


.. warning::

    This plugin works only on python 2.7 for current limitation on the library used.


===================
Per Project Location
===================

The ftrack location can be customised to make fit any custom use.
In this example we provide a Location which make use of the project Storage / project folder attribute available in the project, to provide a way to publish different project in different mount points.

.. note::

    Due to the use of just ftrack api, there's no need to build.
    The plugin can be dropped into the FTRACK_CONNECT_PLUGIN_PATH as it is.

Scope
-----

* Build a self contained plugin able to provide a custom location.
