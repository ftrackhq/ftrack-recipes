# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import os
import functools
import logging

import ftrack_api
import ftrack_api.accessor.disk
import ftrack_api.structure.standard


logger = logging.getLogger('com.ftrack.recipes.location.custom_location_plugin')

# Name of the location plugin.
LOCATION_NAME = None

# Disk mount point.
DISK_PREFIX = None


def configure_location(session, event):
    '''Listen.'''
    location = session.ensure('Location', {'name': LOCATION_NAME})

    location.accessor = ftrack_api.accessor.disk.DiskAccessor(prefix=DISK_PREFIX)

    # use the same structure as the storage scenario.
    location.structure = ftrack_api.structure.standard.StandardStructure()
    location.priority = 2  # lower than storage scenario

    logger.info('Registered location {0} at {1}.'.format(LOCATION_NAME, DISK_PREFIX))


def register(api_object, **kw):
    '''Register location with *session*.'''

    if not isinstance(api_object, ftrack_api.Session):
        return

    if not DISK_PREFIX:
        logger.error('No disk prefix configured for location.')
        return

    if not os.path.exists(DISK_PREFIX) or not os.path.isdir(DISK_PREFIX):
        logger.error('Disk prefix location does not exist.')
        return

    api_object.event_hub.subscribe(
        'topic=ftrack.api.session.configure-location',
        functools.partial(configure_location, api_object),
    )
