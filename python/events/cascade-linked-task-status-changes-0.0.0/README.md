# Cascade Linked Task Status Change

If you have a series of linked tasks, this event handler will trigger
downstream task status changes. When an upstream task status is set to
"Approved" then this event handler then sets any linked, outgoing (downstream)
tasks to a status of "Ready".

## Scope

-   Monitor Task status changes
-   Update linked, outgoing (downstream) task status if appropriate

## Install and setup

1\. Make the plugin available to the API either by setting the
FTRACK_EVENT_PLUGIN_PATH environment variable to
\<custom-location-folder\>. Alternatively use the plugin_paths in the
ftrack_api.Session constructor and point it to
\<custom-location-folder\>.

## Dependencies

-   None

