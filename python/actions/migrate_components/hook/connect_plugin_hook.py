# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import os
import sys
import logging

import ftrack_api

LOCATION_DIRECTORY = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'location')
)

sys.path.append(LOCATION_DIRECTORY)

logger = logging.getLogger('com.ftrack.recipes.customise_structure.hook')



def append_path(path, key, environment):
    '''Append *path* to *key* in *environment*.'''
    try:
        environment[key] = (
            os.pathsep.join([
                environment[key], path
            ])
        )
    except KeyError:
        environment[key] = path

    return environment


def modify_application_launch(event):
    '''Modify the application environment to include  our location plugin.'''
    environment = event['data'].get('options', {}).get('env', {})

    append_path(
        LOCATION_DIRECTORY, 'FTRACK_EVENT_PLUGIN_PATH', environment
    )

    append_path(LOCATION_DIRECTORY, 'PYTHONPATH', environment)

    logger.info('Connect plugin modified launch hook to register location plugin.')


def register(api_object, **kw):
    '''Register plugin to api_object.'''

    # Validate that api_object is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an incompatible API
    # and return without doing anything.
    if not isinstance(api_object, ftrack_api.Session):
        # Exit to avoid registering this plugin again.
        return

    logger.info('Connect plugin discovered.')

    import custom_location_plugin

    custom_location_plugin.register(api_object)

    # Location will be available from within the dcc applications.
    api_object.event_hub.subscribe(
        'topic=ftrack.connect.application.launch', modify_application_launch
    )

    # Location will be available from actions
    api_object.event_hub.subscribe(
        'topic=ftrack.action.launch', modify_application_launch
    )
