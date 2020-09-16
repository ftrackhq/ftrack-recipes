..
    :copyright: Copyright (c) 2018 ftrack

======================
Manage Project Schemas
======================

A command line tools that export a single or all project schemas to JSON, with an option to restore schemas.

Scope
-----

* Backup project schema(s)
* Restore project schema(s), with rename.

Limitations
-----------------

* If exporting to a different Ftrack instance, the target instance must have the same entity types and statuses their definitions are not included in export.

Running
-------


Backing up a specific schema:

.. code-block:: python

     python manage_project_schemas.py backup --schema=VFX --filename=/tmp/test.json
..


Restoring:

.. code-block:: python

     python manage_project_schemas.py restore --schema==VFX --restore=VFX2 --filename=/tmp/test.json
..


Help:

.. code-block:: python

    python manage_project_schemas.py --help
..

Dependencies
------------

* ftrack_api
