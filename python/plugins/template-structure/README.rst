..
    :copyright: Copyright (c) 2014-2020 ftrack


.. warning::

    This plugin works only on python 2.7 for current limitation on the library used.


===================
Templated Structure
===================

The ftrack structure can be customised and make fit many custom naming conventions.
In this example we provide a structure which use the `lucidity <https://pypi.org/project/Lucidity/>`_
python module to provide a templated system to define folders and files.


Scope
-----

* Build a self contained plugin able to provide a templated structure.

Dependencies
------------

* lucidity
* ftrack-action-handler


.. note::

    For the template Syntax please please refer to the lucidity `manual <https://lucidity.readthedocs.io/en/stable/>`_