# Mark Running Jobs as Failed

Example action that mark long-running jobs as failed jobs in your
workspace's job queue.

The file contains a global variable that can be adjusted that is an age
cutoff beyond which a job is considered long running.

As of this writing this action is both a demo and a workaround to a
known issue. Sometimes a job can finish (usually a failure) and not
update it's representation in the queue. If someone stumbles on this and
winds up with jobs that have been apparently running for days, quickly
installing this action can help them clean up their queue.

## Scope

-   Setting up an action with our ftrack-action-handler.
-   Demo job manipulation
-   Show an action that is context independent
-   Show API querying that uses dates and times

## Install and setup

Please refer to the main ftrack-recipes python guide.

## Dependencies

-   ftrack_python_api
-   ftrack_action_handler