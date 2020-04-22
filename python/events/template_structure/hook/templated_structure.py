# :coding: utf-8
# :copyright: Copyright (c) 2014-2020 ftrack

import os
import logging
import functools

import ftrack_api
import ftrack_api.structure.standard
import ftrack_connect.application
import lucidity

# Pick the current folder location name.
this_dir = os.path.abspath(os.path.dirname(__file__))



class TemplatedStructure(ftrack_api.structure.standard.StandardStructure):

    location_name = 'recipe.templated-structure'
    mount_points = {
        'win32': 'P://ftrack_projects',
        'linux2': '/mnt/projects',
        'darwin': '/mnt/projects'
    }

    def __init__(self, templates):
        super(TemplatedStructure, self).__init__()
        self._templates = templates

    def _get_template_from_component(self, component):
        '''Return template from *component*.

        Raise :py:exc:`ValueError` if a template for the *component* is not
        found.
        '''
        template_name = 'project-base-maya'

        for template in self._templates:
            if template.name == template_name:
                return template

        raise ValueError(
            'Template name {0} was not found in input templates'.format(
                template_name
            )
        )

    def get_resource_identifier(self, entity, context=None):
        '''Return a resource identifier from *component*.

        Raise :py:exc:`ValueError` if *component* is not attached to a version.

        '''
        version = entity.get('version')
        if not version:
            raise ValueError(
                'Input component is expected to be connected to a version.'
            )

        # Construct template data.
        project = version['asset']['parent']['project']
        shot = version['asset']['parent']['parent']

        template_data = {
            'shot': {
                'name': shot['name']
            },
            'project': {
                'name': project['name']
            }
        }

        # At the moment file names are not handled with lucidity. It can be done
        # but for the simplicity of this example the basename is just copied.

        standard_file_path = super(
            TemplatedStructure, self
        ).get_resource_identifier(
            entity, context=context
        )
        file_name = os.path.basename(standard_file_path)

        # Get a lucidity template and format with templateData.
        template = self._get_template_from_component(entity)

        file_path = os.path.join(
            template.format(template_data),
            file_name
        )

        return file_path


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

    # Ensure new location.
    my_location = session.ensure(
        'Location', {'name': TemplatedStructure.location_name}
    )

    ftrack_api.mixin(
        my_location, ftrack_api.entity.location.UnmanagedLocationMixin
    )

    # Create TemplatedStructure.
    templates = lucidity.discover_templates(
        paths=[os.path.join(this_dir, '..', 'templates')]
    )
    structure = TemplatedStructure(templates=templates)

    # Set new structure in location.
    my_location.structure = structure

    mount_point = TemplatedStructure.mount_points.get(os.platform)
    # Create new Accessor
    if os.path.exists(mount_point):
        my_accessor = ftrack_api.accessor.disk.DiskAccessor(mount_point)

    else:
        raise IOError('Mount point {} does not exist.'.format(mount_point))

    # Set accessor.
    my_location.accessor = my_accessor

    # Set priority.
    my_location.priority = 30

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