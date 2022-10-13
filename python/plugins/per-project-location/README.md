..
    :copyright: Copyright (c) 2014-2022 ftrack



# Per Project Location


The ftrack location can be customised to make fit any custom use. In
this example we provide a Location which make use of the project Storage
/ project folder attribute available in the project, to provide a way to
publish different project in different mount points. It also contains a
custom path resolver for connect to bypass current limitations of it.

Note

Due to the use of just ftrack api, there's no need to build. The plugin
can be dropped into the FTRACK_CONNECT_PLUGIN_PATH as it is.

# Scope

- Build a self contained plugin able to provide a custom location.

# Note

- Project['root'] is currently limited to 45 characters.
- The code relies on location legacy attributes which might disappear in a future release.
- As a different approach custom attributes could be used to store the project root path.