# :coding: utf-8
# :copyright: Copyright (c) 2014-2020 ftrack

import os
import sys
import logging
import functools
import platform
import ftrack_api
import ftrack_api.structure.standard


dependencies_directory = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'dependencies')
)
sys.path.append(dependencies_directory)

import lucidity

# Pick the current folder location name.
this_dir = os.path.abspath(os.path.dirname(__file__))


class TemplatedStructure(ftrack_api.structure.standard.StandardStructure):

    description = 'Templated example structure from ftrack-recipes'
    name = 'recipe.templated-structure'

    mount_points = {
        'windows': 'P://ftrack/projects',
        'linux': '/mnt/ftrack/projects',
        'darwin': '/mnt/ftrack/projects'
    }

    def __init__(self, templates):
        super(TemplatedStructure, self).__init__()
        self.logger = logging.getLogger(
            __name__ + '.' + self.__class__.__name__
        )

        self._templates = templates
        
        # assets can be published only under a version template
        self._template_filter = 'version' 

    def _get_templates(self, component):
        '''Return version template from *component*.

        We expect to find at least one template containing teh template_filter
        word (version) in order to be able to publish
        '''

        templates = []
        for template in self._templates:
            if self._template_filter in template.name:
                self.logger.info('adding {}'.format(template.name))
                templates.append(template)

        if not templates:
            raise ValueError('No version template found!')

        return templates

    def get_resource_identifier(self, entity, context=None):
        '''Return a resource identifier from *component*.

        Raise :py:exc:`ValueError` if *component* is not attached to a version.

        '''
        version = entity.get('version')
        if not version:
            raise ValueError(
                'Input component is expected to be connected to a version.'
            )

        data = {}
        context = version['asset']['parent']
        for link in context['link']:
            entity_type = entity.session.get(
                link['type'],
                link['id']
            ).entity_type.lower()


            data[entity_type] = {
                'name': link['name'].lower(),
                'type': entity_type
            }

            data['asset'] = {
                'name': version['asset']['name'],
                'type': version['asset']['type']['name'],
                'version': str(version['version'])
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
        templates = self._get_templates(entity)

        file_path = None
        for template in templates:
            try:
                file_path = template.format(data)
            except Exception as error:
                self.logger.warning(error)
                continue

        if not file_path:
            raise IOError('No Valid template found')

        file_path = os.path.join(
            file_path,
            file_name
        )

        return file_path


def configure_location(session, event):
    '''Configure locations for *session* and *event*.'''

    logging.info('Configuring location....')

    # Ensure environment variables options are available in event.
    if 'options' not in event['data']:
        event['data']['options'] = {'env': {}}

    environment = event['data']['options']['env']

    # Add this script path to the FTRACK_EVENT_PLUGIN_PATH.
    location_path = os.path.normpath(this_dir)
    environment['FTRACK_EVENT_PLUGIN_PATH'] = os.pathsep.join([
        location_path,
        environment.get('FTRACK_EVENT_PLUGIN_PATH', '')
    ])

    # Ensure new location.
    my_location = session.ensure(
        'Location', {
            'name': TemplatedStructure.name,
            'description': TemplatedStructure.description
        }
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

    mount_point = TemplatedStructure.mount_points.get(platform.system().lower())
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


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Remember, in version version 2.0 of the ftrack-python-api the default
    # behavior will change from True to False.
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)
    logging.info(
        'Registered location {} and listening'
        ' for events. Use Ctrl-C to abort.'.format(TemplatedStructure.name)
    )
    session.event_hub.wait()