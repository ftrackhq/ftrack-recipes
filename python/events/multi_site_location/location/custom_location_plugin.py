# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

import os
import sys
import functools
import logging

import ftrack_api
import ftrack_api.accessor.disk
import ftrack_api.structure.standard

logger = logging.getLogger(
    'com.ftrack.recipes.multi_site_location.custom_location_plugin'
)

# retrieve current location from the environment variables
current_location = os.environ.get('FTRACK_LOCATION')


def configure_location(session, location_setup, event):
    '''Listen.'''

    for location_name, disk_prefixes in location_setup.items():

        # Get mount point for the correct os in use
        disk_prefix = disk_prefixes.get(sys.platform)

        if not disk_prefix:
            logger.error(
                'No disk prefix configured for location {0}'.format(
                    location_name
                )
            )
            continue

        if not os.path.exists(disk_prefix) or not os.path.isdir(disk_prefix):
            logger.error(
                'Disk prefix for location {} does not exist.'.format(
                    location_name
                )
            )
            continue

        location = session.ensure('Location', {'name': location_name})

        location.accessor = ftrack_api.accessor.disk.DiskAccessor(
            prefix=disk_prefix
        )
        location.structure = ftrack_api.structure.standard.StandardStructure()
        if location_name == current_location:
            location.priority = 1  # lower value == higher priority !
        else:
            location.priority = 10

        logger.warning(
            u'Registered location {0} at {1} with priority {2}'.format(
                location_name, disk_prefix, location.priority)
        )


def register(api_object, location_setup=None):
    '''Register location with *session*.'''

    if not isinstance(api_object, ftrack_api.Session):
        return

    api_object.event_hub.subscribe(
        'topic=ftrack.api.session.configure-location',
        functools.partial(
            configure_location,
            api_object,
            location_setup
        )
    )
