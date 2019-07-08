# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import os
import sys
import logging

import ftrack_api
import ftrack_connect.application

LOCATION_DIRECTORY = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'location')
)
sys.path.append(LOCATION_DIRECTORY)
logger = logging.getLogger('com.ftrack.recipes.multi_site_location.hook')

LOCATIONS_DATA = {
    'custom.location1': '/mnt/zeus/storage/ftrack/projects/',
    'custom.location2': '/somewhere/else'
}


def modify_application_launch(event):
    '''Modify the application environment to include  our location plugin.'''

    environment = event['data']['options']['env']

    ftrack_connect.application.appendPath(
        LOCATION_DIRECTORY,
        'FTRACK_EVENT_PLUGIN_PATH',
        environment
    )
    ftrack_connect.application.appendPath(
        LOCATION_DIRECTORY,
        'PYTHONPATH',
        environment
    )
    logger.info(
        'Connect plugin modified launch hook to register location plugin.'
    )


def register(api_object, **kw):
    '''Register plugin to api_object.'''

    # Validate that api_object is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an incompatible API
    # and return without doing anything.
    if not isinstance(api_object, ftrack_api.Session):
        # Exit to avoid registering this plugin again.
        return

    import custom_location_plugin
    custom_location_plugin.register(api_object, location_setup=LOCATIONS_DATA)

    # Location will be available from within the dcc applications.
    api_object.event_hub.subscribe(
        'topic=ftrack.connect.application.launch',
        modify_application_launch
    )

    # Location will be available from actions
    api_object.event_hub.subscribe(
        'topic=ftrack.action.launch',
        modify_application_launch
    )