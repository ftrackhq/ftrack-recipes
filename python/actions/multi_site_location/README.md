# multi site locations

This recipe will show how to easily setup a multi site location system
with ftrack.

As assumption we take that there'll be 2 locations at play. Both able to
access each other mount points (eg: through vpn):

-   location1
-   location2

Each site will register its location with names:

-   location1 -\> custom.location1
-   location2 -\> custom.location2

In a production scenario these names is suggested to reflect the storage
scope, and the location name eg:

-   mycompany.central.uk
-   mycompany.central.es

Note

In order for multi location setup to work, you'll have to *disable the
storage scenario* using: **reset to automatic storage scenario** from
the Media Management settings of the ftrack server.

Warning

If a previous storage scenario has been used, please make sure the
affected location set the same name, structure and accessor as the
storage scenario.

## Setup

The following instructions will have to be followed for all the
locations. Each location will define a different and unique location
name.

### Installing the locations

#### (Option 1) Centralised connect plugins

Create a shared folder on the local server where to store this code.
Create an environment variable to point to the newly created folder.

``` 
(osx and linux)
export FTRACK_CONNECT_PLUGIN_PATH=/path/to/shared/folder/:${FTRACK_CONNECT_PLUGIN_PATH}
```

On windows machines, please set this environment variable through the
AdvancedSystemSettings.

``` 
(windows)
FTRACK_CONNECT_PLUGIN_PATH /path/to/shared/folder/;$FTRACK_CONNECT_PLUGIN_PATH
```

Note

This environment variable should be set on each machine

#### (Option 2) Local connect plugins

Otherwise ,you can simply install the code on each and every machine
under the
[local](http://ftrack-connect.rtd.ftrack.com/en/stable/developing/plugins.html)
connect plugin folder.

### Define current location

We are creating here a custom environment variable named
**FTRACK_LOCATION** to store the current location name.

(Osx and Linux)

``` bash
export FTRACK_LOCATION='custom.location<N>'
```

On windows machines, please set this environment variable through the
AdvancedSystemSettings.

(Windows)

``` bash
FTRACK_LOCATION 'custom.location<N>'
```

Note

The location variable name will be different based on the site is
installed into. where \<N\> of the name is the location number where you
are located.

Note

This environment variable should be set on each machine

### Configure locations

Location configurations are contained in the local json file <span
class="title-ref">locations.json</span>. This file contains one entry
for each location name and a mapping of mount points for each OS at
play.

Example file:

``` json
{
    "custom.location1": {
        "linux2": "/path/to/mount/point1",
        "win32": "Z:\\path\\to\\mount\\point1",
        "darwin": "/path/to/mount/point1"
    },
    "custom.location2": {
        "linux2": "/path/to/mount/point2",
        "win32": "Z:\\path\\to\\mount\\point2",
        "darwin": "/path/to/mount/point2"
    }
}
```

### Running the transfer component action

In order to copy one component from one location to another, select the
component you want to transfer and click on the **A** icon next to it.
Once clicked the server will present a list of available actions for it,
among which, you'll be able to find the **Transfer Component to
\<location name\>**.

Click on it and select the **source location** from where the component
should be transfer from. The destination location will be set to your
current one.

Note

The *transfer component* action will be visible on components only.

### Dependencies

-   ftrack_python_api
-   ftrack_action_handler