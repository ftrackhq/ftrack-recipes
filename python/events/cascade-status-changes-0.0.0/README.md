# Cascade Status Change

Just like Tasks, a Shot Object has its own status, separate from the
statuses of its child Tasks. However, on the Tasks spreadsheet, this
underlying status is not displayed; instead the Shot status reflects
that of its children. We will add an event handler to update a Shot
status as appropriate when a child Task is updated.

## Scope

-   Monitor Task status changes
-   Update Shot status if appropriate

## Install and setup

1\. Make the cascade plugin available to the API either by setting the
FTRACK_EVENT_PLUGIN_PATH environment variable to
\<custom-location-folder\>. Alternatively use the plugin_paths in the
ftrack_api.Session constructor and point it to
\<custom-location-folder\>.

## Dependencies

-   None