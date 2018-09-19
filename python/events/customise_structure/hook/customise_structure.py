# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import os
import logging
import functools

import ftrack_api
from ftrack_api.structure.id import IdStructure
from ftrack_api.accessor.disk import DiskAccessor
import ftrack_connect.application


# Pick the current folder location name.
this_dir = os.path.abspath(os.path.dirname(__file__))


def configure_location(session, event):
    '''Configure locations for *session* and *event*.'''

    # Ensure environment variables options are available in event.
    if 'options' not in event['data']:
        event['data']['options'] = {'env': {}}

    environment = event['data']['options']['env']

    # Add this script path to the FTRACK_EVENT_PLUGIN_PATH.
    location_path = os.path.normpath(this_dir)
    ftrack_connect.application.appendPath(
        location_path,
        'FTRACK_EVENT_PLUGIN_PATH',
        environment
    )

    # Pick curent location in use.
    my_location = session.pick_location()

    # Replace StandardStructure with IdStructure.
    structure = IdStructure()

    # Set new structure in location.
    my_location.structure = structure

    logging.info('Setting {} to {}'.format(
            structure, my_location
        )
    )


def register(api_object):
    '''Register plugin with *api_object*.'''
    logger = logging.getLogger(
        'ftrack-recipes:configure_custom_structure.register'
    )

    # Validate that session is an instance of ftrack_api.Session. If not, assume
    # that register is being called from an old or incompatible API and return
    # without doing anything.
    if not isinstance(api_object, ftrack_api.Session):
        logger.debug(
            'Not subscribing plugin as passed argument {0} is not an '
            'ftrack_api.Session instance.'.format(api_object)
        )
        return

    # React to configure location event.
    api_object.event_hub.subscribe(
        'topic=ftrack.api.session.configure-location',
        functools.partial(configure_location, api_object),
        priority=0
    )

    # React to application launch event.
    # This way the location will be available from within the integrations.
    api_object.event_hub.subscribe(
        'topic=ftrack.connect.application.launch',
        functools.partial(configure_location, api_object),
        priority=0
    )

    # React to action launch event.
    # This way the location will be available from within the actions.
    api_object.event_hub.subscribe(
        'topic=ftrack.action.launch',
        functools.partial(configure_location, api_object),
        priority=0
    )
