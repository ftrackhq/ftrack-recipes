# :coding: utf-8
# :copyright: Copyright (c) 2016-2022 ftrack

import os
import sys
import logging

import ftrack_api

logger = logging.getLogger('per_project_location_hook')


LOCATION_DIRECTORY = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'location')
)
sys.path.append(LOCATION_DIRECTORY)


def appendPath(path, key, environment):
    '''Append *path* to *key* in *environment*.'''
    try:
        environment[key] = os.pathsep.join([environment[key], path])
    except KeyError:
        environment[key] = path

    return environment


def modify_application_launch(event):
    '''Modify the application environment to include  our location plugin.'''
    environment = event['data'].get('options', {}).get('env', {})

    appendPath(LOCATION_DIRECTORY, 'FTRACK_EVENT_PLUGIN_PATH', environment)

    appendPath(LOCATION_DIRECTORY, 'PYTHONPATH', environment)

    logger.info(
        'Connect plugin modified launch hook to register location plugin.'
    )


def register(api_object, **kw):
    '''Register plugin to api_object.'''

    # Validate that session is an instance of ftrack_api.session.Session. If
    # not, assume that register is being called from an old or incompatible API
    # and return without doing anything.
    if not isinstance(api_object, ftrack_api.Session):
        return

    import per_project_location

    per_project_location.register(api_object)

    # Location will be available from within the dcc applications.
    api_object.event_hub.subscribe(
        'topic=ftrack.connect.application.launch', modify_application_launch
    )

    # Location will be available from actions
    api_object.event_hub.subscribe(
        'topic=ftrack.action.launch', modify_application_launch
    )
