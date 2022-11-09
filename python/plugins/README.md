# ftrack plugins

In this folder are collected examples regarding the writing of ftrack
self contained plugin.

Note

This is how most of the integrations are currently provided.

## build

The build process is a custom one integrated into the setup.py.

To build the plugin run:

``` 
$ python setup.py build_plugin
```

The result plugin will be available under the **build** folder

## install

Copy the result folder under *build* into your
*FTRACK_CONNECT_PLUGIN_PATH* or *FTRACK_EVENT_PLUGIN_PATH* (depending on
whether is a connect or api plugin).