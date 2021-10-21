#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

import logging

from ftrack_action_handler.action import BaseAction
import ftrack_api


class EditDescriptions(BaseAction):
    '''Action to allow updating the descriptions on AssetVersion Objects.'''
    label = 'Edit Description'
    identifier = 'com.ftrack.recipes.edit_descriptions'
    description = 'Edit descriptions for AssetVersions'

    def discover(self, session, entities, event):
        '''Return True to be discovered when *entities* is a valid selection.

        *entities* must contain either one or more AssetVersions or a non-empty
        List of AssetVersions.

        *session* is a ftrack_api.Session instance.

        *entities* is a list of tuples each containing the entity type and the
        entity id. If the entity is a hierarchical you will always get the
        entity type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* is the unmodified original event.
        '''
        if not entities:
            return False

        for entity_type, entity_id in entities:
            if entity_type == 'AssetVersion':
                return True

        if len(entities) > 1:
            return False

        entity_type, entity_id = entities[0]
        if entity_type != 'List':
            return False
        my_list = session.get(entity_type, entity_id)
        if my_list['system_type'] != 'assetversion':
            return False
        if not my_list['items']:
            return False

        return True

    def _get_versions(self, entities):
        '''Resolve the *entities* list into AssetVersion objects.'''
        if len(entities) == 1 and entities[0][0] == 'List':
            return self.session.get(*entities[0])['items']
        return (
            self.session.get(*entity)
            for entity in entities
            if entity[0] == 'AssetVersion'
        )

    def interface(self, session, entities, event):
        '''Return an interface if applicable else None.

        *session* is a `ftrack_api.Session` instance

        *entities* is a list of tuples each containing the entity type and the
        entity id. If the entity is a hierarchical you will always get the
        entity type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event
        '''
        values = event['data'].get('values', {})
        if values:
            return

        versions = self._get_versions(entities)
        widgets = [
            {
                'label': ' / '.join(link['name'] for link in version['link']),
                'type': 'text',
                'value': version['comment'],
                'name': version['id'],
            }
            for version in versions
        ]

        return widgets

    def launch(self, session, entities, event):
        '''Callback method for the custom action.

        Return either a bool (True if successful or False if the action failed)
        or a dictionary with they keys `message` and `success`, the message
        should be a string and will be displayed as feedback to the user,
        success should be a bool, True if successful or False if the action
        failed.

        *session* is a ftrack_api.Session instance.

        *entities* is a list of tuples each containing the entity type and the
        entity id. If the entity is a hierarchical you will always get the
        entity type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* is the unmodified original event.

        '''
        for id_, comment in list(event['data']['values'].items()):
            session.get('AssetVersion', id_)['comment'] = comment
        session.commit()

        return {
            'success': True,
            'message': 'Description(s) updated.'
        }


def register(session, **kw):
    '''Register hook with provided *api_object*.

    Validate that session is an instance of ftrack_api.Session. If not, assume
    that register() is being called from an old or incompatible API and return
    without doing anything.
    '''
    if not isinstance(session, ftrack_api.Session):
        return

    action = EditDescriptions(session)
    action.register()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)
    logging.info(
        'Registered actions and listening for event. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()
