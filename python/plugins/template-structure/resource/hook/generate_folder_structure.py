# :coding: utf-8
# :copyright: Copyright (c) 2014-2020 ftrack

import os
import sys
import ftrack_api
import logging
from pprint import pformat

dependencies_directory = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'dependencies')
)
sys.path.append(dependencies_directory)


from ftrack_action_handler.action import BaseAction

logger = logging.getLogger(__file__)


class GenearateFolderStructureAction(BaseAction):
    '''Create report action class.'''

    label = 'Generate Folder Structure'
    identifier = 'com.ftrack.recipes.generate-folder-structure'
    description = 'Generate folder structure from the selected project.'

    @property
    def session(self):
        '''Return convenient exposure of the self._session reference.'''
        return self._session

    def validate_selection(self, entities):
        '''Return True if the selection is valid.

        Utility method to check *entities* validity.

        '''
        print entities
        if not entities:
            return False

        entity_type, entity_id = entities[0]
        if entity_type == 'Project':
            return True

        return False

    def discover(self, session, entities, event):
        '''Return True if the action can be discovered.

        Check if the current selection can discover this action.

        '''
        return self.validate_selection(entities)

    def launch(self, session, entities, event):
        location = self.session.pick_location()
        self.logger.info('Using location {}'.format(location['name']))
        prefix = location.accessor.prefix
        templates = location.structure._templates

        # assets might not be existing ....
        contexts = session.query(
            'TypedContext where project.id is "{}"'.format(entities[0][1])
        ).all()

        for context in contexts:
            data = {}
            for link in context['link']:
                entity_type = session.get(
                    link['type'],
                    link['id']
                ).entity_type.lower()

                data[entity_type] = {
                    'name': link['name'].lower(),
                    'type': entity_type
                }

            for template in templates:

                try:
                    result_path = template.format(data)
                except Exception as error:
                    self.logger.warning(str(error))
                    continue

                full_result_path = os.path.join(prefix, result_path)
                self.logger.info('Creating {}'.format(full_result_path))
                if not os.path.exists(full_result_path):
                    os.makedirs(full_result_path)
                else:
                    self.logger.warning('skipping {} as it already exist.'.format(full_result_path))

        return True


def register(api_object, **kw):
    '''Register hook with provided *api_object*.'''
    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(api_object, ftrack_api.session.Session):
        return
    action = GenearateFolderStructureAction(api_object)
    action.register()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Remember, in version version 2.0 of the ftrack-python-api the default
    # behavior will change from True to False.
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()