====================
Create Report Action
====================

Example action to show how to read data from the server and write them in an excel file.
The file will be available to download from within the web ui.

Scope
-----

* Setting up an action with our ftrack-action-handler.
* Run the action from a Project.
* Create a Job so that the user sees progress.
* Gather some data from the project (e.g. names and descriptions) and perhaps a filter.
* Create an excel from the data and attach it to the job.
* Set the job to completed.


Install and setup
-----------------
Please refer to the main ftrack-recipes python guide. 


Dependencies
------------

* xlsxwriter
* ftrack_python_api
* ftrack_action_handler