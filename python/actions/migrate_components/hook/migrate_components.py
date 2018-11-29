#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import json
import logging

import ftrack_api
from ftrack_action_handler.action import BaseAction


class MigrateComponents(BaseAction):

    label = 'Migrate Components'
    identifier = 'com.ftrack.recipes.migrate_components'
    description = 'Migrate project components from one location to another'

    def validate_selection(self, entities):
        '''Return True if the selection is valid.

        Utility method to check *entities* validity.

        '''
        if not entities:
            return False

        entity_type, _ = entities[0]
        if entity_type == 'Project':
            return True

        return False

    def migrate(self, project_id, source_location, destination_location):
        '''Run migration of *project_id* from *source_location* 
        to *destination_location*.
        '''
        
        # Get the source location entity.
        source_location_object = self.session.query(
            'Location where name is "{}"'.format(source_location)
        ).one()

        # Get the destination location entity.
        destination_location_object = self.session.query(
            'Location where name is "{}"'.format(destination_location)
        ).one()

        # Get the project entity.
        project_object = self.session.query(
            'Project where id is "{}"'.format(
                project_id
            )
        ).one()
        
        # Collect all the components attached to the project. 
        component_objects = self.session.query(
            'Component where version.asset.parent.project_id is "{}" '
            'and component_locations.location_id is "{}"'.format(
                project_object['id'], source_location_object['id']
                )
        ).all()

        component_count = 0

        # Phiscally copy the components.
        for component in component_objects:
            try:
                destination_location_object.add_component(
                    component, source_location_object
                )
            except ftrack_api.exception.LocationError as error:
                self.logger.warning(error)
                # as has failed does not count.
                component_count -= 1

            component_count += 1

        self.session.commit()
        return component_count

    def interface(self, session, entities, event):
        '''Return interface for *entities*.'''
        values = event['data'].get('values', {})
        # Interface will be raised as long as there's no value set.
        # here is a good place where to put validations.
        if values:
            return

        # Populate ui with the project name.
        widgets = [
            {
                'label': 'source location',
                'value': self.session.pick_location()['name'],
                'name': 'source_location',
                'type': 'text'
            },
            {
                'label': 'destination location',
                'data': [],
                'name': 'destination_location',
                'type': 'enumerator'
            },

        ]
        
        # Internal ftrack locations we are not interested in. 
        excluded_locations = [
            'ftrack.origin', 
            'ftrack.connect', 
            'ftrack.unmanaged', 
            'ftrack.server', 
            'ftrack.review', 
            self.session.pick_location()['name']
        ]
        
        for location in self.session.query('Location').all():
            if location.accessor is ftrack_api.symbol.NOT_SET:
                # Remove non accessible locations.
                continue

            if location['name'] in excluded_locations:
                # Remove source location as well as ftrack default ones.
                continue
 
            widgets[-1]['data'].append(
                {
                    'label': location['name'],
                    'value': location['name']
                }
            )

        return widgets

    def _create_job(self, event, message):
        '''Return new job from *event*.

        ..note::
        
            This function will auto-commit the session.

        '''

        user_id = event['source']['user']['id']
        job = self.session.create(
            'Job',
            {
                'user': self.session.get('User', user_id),
                'status': 'running',
                'data': json.dumps({
                    'description': unicode(
                         message
                    )}
                )
            }
        )
        self.session.commit()
        return job

    def discover(self, session, entities, event):
        '''Return True if the action can be discovered.

        Check if the current selection can discover this action.

        '''
        return self.validate_selection(entities)

    def launch(self, session, entities, event):
        '''Return result of running action.'''

        values = event['data'].get('values', {})

        # If there's no value coming from the ui, we can bail out.
        if not values:
            return
    
        source_location = values['source_location']
        destination_location = values['destination_location']
    
        # Create a new running Job.
        job = self._create_job(
            event, 'Copying components from {} to {}'.format(
                source_location,
                destination_location
            )
        )
        
        _, entity_id = entities[0]
        component_count = self.migrate(
            entity_id, source_location, destination_location
        )

        # Set job status as done.
        job['status'] = 'done'
        self.session.commit()
an
anessage to the user with the amount of components copied and
ancations involved.
an
an': 'True',
an': '{} components have been copied from :{} to :{}'.format(
anonent_count, source_location, destination_location
an
an
an

def register(api_object, **kw):
    '''Register hook with provided *api_object*.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(api_object, ftrack_api.session.Session):
        return

    action = MigrateComponents(
        api_object
    )
    action.register()


if __name__ == '__main__':
    # To be run as standalone code.
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session()
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()
