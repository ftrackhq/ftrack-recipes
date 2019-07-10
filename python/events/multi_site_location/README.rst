====================
multi site locations
====================

This recipe will show how to easily setup a multi site location system with ftrack.

As assumption we take that there'll be 2 location at play, able to access each other mount points (eg: through vpn):

* location1
* location2

Each site will register its location with names:

* location1 -> custom.location1
* location2 -> custom.location2

In a production scenario these names is suggested to make the name reflect the storage scope, and the location name eg:

* mycompany.central.uk
* mycompany.central.es


.. note::

    In order for multi location setup to work, you'll have to disable the 
    storage scenario using : reset to automatic storage scenario from the Media Management
    settings of the ftrack server.
    
.. warning:: 

    If a previous storage scenario has been used, please make sure
    the affected location set the same name, structure and accessor as the storage
    scenario.


Setup
=====

The following instructions will have to be followed for all the locations.
Each location though will define a different and unique location name.

Installing the locations:
-------------------------

(option1) Centralised connect plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a shared folder on the local server where to store this code.
Create an environment variable to point to the newly created folder.

.. code-block::

    (osx and linux)
    export FTRACK_CONNECT_PLUGIN_PATH=/path/to/shared/folder/:${FTRACK_CONNECT_PLUGIN_PATH}

On windows machines, please set this environment variable through the AdvancedSystemSettings

.. code-block::

    (windows)
    FTRACK_CONNECT_PLUGIN_PATH /path/to/shared/folder/;$FTRACK_CONNECT_PLUGIN_PATH

.. note::

    This environment variable should be set on each machine


(option2) Local connect plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Otherwise ,you can simply install the code on each and every machine under
the `local <http://ftrack-connect.rtd.ftrack.com/en/stable/developing/plugins.html>`_ connect plugin folder.


Define current location
-----------------------

We are creating here a custom environment variable named **FTRACK_LOCATION** to store the current location name

.. code-block::

    (Osx and Linux)
    export FTRACK_LOCATION='custom.location<N>'


On windows machines, please set this environment variable through the AdvancedSystemSettings

.. code-block::

    (Windows)
    FTRACK_LOCATION 'custom.location<N>'

.. note:: 

    The location variable name will be different based on the site is installed into.
    where <N> of the name is the location number where you are located.

.. note:: 

    This environment variable should be set on each machine


Configure locations
-------------------

Location configurations are contained in the local json file locations.json
This file contains one entry for each location name and a mapping of mount points for each os at play.

example file:

.. include:: hook/locations.json
   :literal:


