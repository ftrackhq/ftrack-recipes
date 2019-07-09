#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

import os
import json
import functools

import ftrack_api
from ftrack_action_handler.action import BaseAction


class TransferComponent(BaseAction):

    current_location = os.environ.get('FTRACK_LOCATION')
    identifier = 'com.ftrack.recipes.multi_site_location.transfer_components'
    description = 'Migrate project components from one location to another'
    label = 'Transfer Component'
    variant = 'to {}'.format(current_location)

    def validate_selection(self, entities):
        ''' Utility method to check *entities* validity.

        Return True if the selection is valid.
        '''
        if not entities:
            return False

        entity_type, _ = entities[0]
        print entity_type
        if entity_type == 'Component':
            return True

        return False

    def transfer(self, component_id, source_location, destination_location):
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

        # Collect all the components attached to the project. 
        component_objects = self.session.query(
            'Component where id is "{}" '
            'and component_locations.location_id is "{}"'.format(
                component_id, source_location_object['id']
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
                self.logger.error(error)

            finally:
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
                'data': [],
                'name': 'source_location',
                'type': 'enumerator'
            },
            {
                'label': 'current location',
                'value': self.session.pick_location()['name'],
                'name': 'destination_location',
                'type': 'text'
            }
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
        
        for location in self.session.query('select name from Location').all():
            if location.accessor is ftrack_api.symbol.NOT_SET:
                # Remove non accessible locations.
                continue

            if location['name'] in excluded_locations:
                # Remove source location as well as ftrack default ones.
                continue
 
            widgets[0]['data'].append(
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

    def _discover(self, event):
        result = super(TransferComponent, self)._discover(event)
        for item in result['items']:
            item['location'] = self.current_location

        return result

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
        self.transfer(
            entity_id, source_location, destination_location
        )

        # Set job status as done.
        # This will notify the user in the web ui.
        job['status'] = 'done'
        self.session.commit()

        return True

    def register(self):
        current_location_object = self.session.pick_location()
        print current_location_object['name'], self.current_location

        if current_location_object['name'] != self.current_location:
            self.logger.warning(
                'Not registering action {} for location {} on {}'.format(
                    self.identifier, self.current_location,
                    current_location_object['name']
                ))
            return

        self.session.event_hub.subscribe(
            'topic=ftrack.action.discover and data.location="{0}"'.format(self.current_location),
            self._discover
        )

        self.session.event_hub.subscribe(
            'topic=ftrack.action.launch and data.actionIdentifier={0} and data.location="{1}"'.format(
                self.identifier, self.current_location
            ),
            self._launch
        )


def register_action(session, event):
    '''Register hook with provided *api_object*.'''
    print event
    action = TransferComponent(
        session
    )
    action.register()


def register(api_object):

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(api_object, ftrack_api.session.Session):
        return

    api_object.event_hub.subscribe(
        'topic=ftrack.api.session.ready',
        functools.partial(register_action, api_object)
    )