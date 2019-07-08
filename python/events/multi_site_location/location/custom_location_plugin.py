# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import os
import functools
import logging

import ftrack_api
import ftrack_api.accessor.disk
import ftrack_api.structure.standard

logger = logging.getLogger(
    'com.ftrack.recipes.multi_site_location.location.custom_location_plugin'
)
current_location = os.environ.get('FTRACK_LOCATION')


def configure_location(session, location_name, disk_prefix, event):
    '''Listen.'''
    location = session.ensure('Location', {'name': location_name})

    location.accessor = ftrack_api.accessor.disk.DiskAccessor(
        prefix=disk_prefix
    )
    location.structure = ftrack_api.structure.standard.StandardStructure()
    location.priority = 1

    logger.warning(
        u'Registered location {0} at {1}.'.format(location_name, disk_prefix)
    )


def register(api_object, location_setup=None):
    '''Register location with *session*.'''

    disk_prefix = location_setup.get(current_location)

    if not isinstance(api_object, ftrack_api.Session):
        return

    if not disk_prefix:
        logger.error('No disk prefix configured for location.')
        return

    if not os.path.exists(disk_prefix) or not os.path.isdir(disk_prefix):
        logger.error('Disk prefix location does not exist.')
        return

    api_object.event_hub.subscribe(
        'topic=ftrack.api.session.configure-location',
        functools.partial(
            configure_location, 
            api_object, 
            current_location, 
            disk_prefix
        )
    )
