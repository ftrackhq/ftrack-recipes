import os
import sys
import platform
import functools
import tempfile
import logging

import ftrack_api
from ftrack_api.entity.location import Location
from ftrack_api.accessor.disk import DiskAccessor
from ftrack_api.structure.standard import StandardStructure


logger = logging.getLogger('per_project_location')


class PerProjectLocation(Location):
    platform = platform.system()

    def _get_project_root(self, component):
        target_project = component['version']['asset']['parent']['project']

        # use :storage / project location: from project settings
        root_folder = target_project['root']
        if not root_folder:
            root_folder = target_project['disk'].get(
                platform.system().lower(), 'unix'
            )

        if not root_folder:
            raise IOError('Cannot get the root folder for the project.')

        return root_folder

    def _add_data(self, component, resource_identifier, source):
        root_folder = self._get_project_root(component)
        self.accessor.prefix = root_folder

        super(PerProjectLocation, self)._add_data(
            component, resource_identifier, source
        )

    def get_filesystem_path(self, component):
        resource_identifier = self.get_resource_identifier(component)
        root_folder = self._get_project_root(component)
        return os.path.join(root_folder, resource_identifier)


def configure_location(session, event):

    location = session.ensure('Location', {'name': 'perProjectLocation'})

    ftrack_api.mixin(location, PerProjectLocation, name='perProjectLocation')

    location.accessor = DiskAccessor('NOT_SET')
    location.structure = StandardStructure()
    location.priority = 1 - sys.maxsize

    logger.warning(
        f'Registering per project location {location} with accessor: {location.accessor} ,  structure: {location.structure} and priority: {location.priority} for platform {location.platform}'
    )


def register(api_object, **kw):
    '''Register location with *session*.'''

    if not isinstance(api_object, ftrack_api.Session):
        return

    api_object.event_hub.subscribe(
        'topic=ftrack.api.session.configure-location',
        functools.partial(configure_location, api_object),
    )
