# Migrate Components

Example action to show how to copy all the components of a project from
one location to another.

> This example provide the registration of an extra location to transfer
> to.

## Scope

-   Setting up an action with our ftrack-action-handler.
-   Run the action from a Project.
-   Create a Job so that the user sees progress.
-   Gather all the components under the given project
-   Copy all the componets to the destination location.
-   Set the job to completed.

> Source location will be the location with higher priority. Destination
> location can be any available.

## Install and setup

Please refer to the main ftrack-recipes python guide.

## Dependencies

-   ftrack_python_api