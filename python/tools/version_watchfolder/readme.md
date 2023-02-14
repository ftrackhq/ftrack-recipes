copyright: Copyright (c) 2014-2022 ftrack

# Version watch folder

Daemon which will monitor a folder where to drop versions to be automatically published to ftrack.


## Scope

* Publish files to ftrack


## Usage

1) set an environment variable named **FTRACK_VERSION_WATCHFOLDER** to a local folder on disk
2) run the script , any files dropped into the given folder will be checked and uploaded to ftrack.
3) files will have to named as : <PROJECT>_<SHOT>_<TASK>_<VERSION>.<EXT>



## Dependencies

* watchdog
* psutil
* ftrack-python-api
