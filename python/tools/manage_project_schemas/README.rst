..
    :copyright: Copyright (c) 2014-2020 ftrack

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

     python manage_project_schemas.py backup --schema VFX --filename /tmp/test.json
..


Restoring:

.. code-block:: python

     python manage_project_schemas.py restore --schema VFX --destination VFX2 --filename /tmp/test.json
..


Help:

.. code-block:: python

    python manage_project_schemas.py --help
..

Dependencies
------------

* ftrack_api


Roundtrip for Schema crossdomain Replication
------------

* suffcient rights on the current role and/or api key are expected!

Backup:

.. code-block:: python

    set FTRACK_SERVER=olddomain
    python manage_schemas.py backup --schema "SCHEMANAME" --filename c:\temp\schemaname.json
..

Verify with dry_run against the new domain:

.. code-block:: python

    set FTRACK_SERVER=newdomain
    python manage_schemas.py verify --dry_run --filename c:\temp\schemaname.json
..

Verify without dry run:

* this creates missing types, object types and status

.. code-block:: python

    set FTRACK_SERVER=newdomain
    python manage_schemas.py verify --filename c:\temp\schemaname.json
..

Restore with dry run:

.. code-block:: python

    set FTRACK_SERVER=newdomain
    python manage_schemas.py restore --schema "SCHEMANAME" --destination "SCHEMANAME_OR_OTHERNAME" --dry_run --filename c:\temp\schemaname.json
..

Restore creates the schema:

.. code-block:: python

    set FTRACK_SERVER=newdomain
    python manage_schemas.py restore --schema "SCHEMANAME" --destination "SCHEMANAME_OR_OTHERNAME" --filename c:\temp\schemaname.json
..
