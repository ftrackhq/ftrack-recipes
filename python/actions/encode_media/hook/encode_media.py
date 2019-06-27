#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

import logging

from ftrack_action_handler.action import BaseAction
import ftrack_api


class EncodeMedia(BaseAction):
    '''Demonstrates two methods of marking review clips with the name of the
    original media they represent. While presented as an action, the
    proces_event() method is suitable for use as an event listener, running on
    clips as they are added to a review.
    '''
    label = 'Encode Media'
    identifier = 'com.ftrack.recipes.encode_media'
    description = 'Encode media from a main component.'

    def discover(self, session, entities, event):
        '''Return True to be discovered when *entities* contains a review.

        This action should only be available when a review session is selected.
        For the moment we trust that our user has permissions to perform the
        needed actions.

        *session* is a ftrack_api.Session instance.

        *entities* is a list of tuples each containing the entity type and the
        entity id. If the entity is a hierarchical you will always get the
        entity type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* is the unmodified original event.
        '''
        if len(entities) != 1:
            return False

        entity_type, entity_id = entities[0]

        if entity_type != 'AssetVersion':
            return False

        version = session.get(entity_type, entity_id)
        components = version['components']

        if not [comp for comp in components if comp['name'] == 'main']:
            return False

        if [comp for comp in components if comp['name'].startswith('ftrackreview-')]:
            return False

        return True

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
        entity_type, entity_id = entities[0]

        version = session.get(entity_type, entity_id)
        main = [comp for comp in version['components'] if comp['name'] == 'main'][0]
        filepath = main['component_locations'][0]['location'].get_filesystem_path(main)
        version.encode_media(filepath)

        return True


def register(api_object, **kw):
    '''Register hook with provided *api_object*.

    Validate that session is an instance of ftrack_api.Session. If not, assume
    that register() is being called from an old or incompatible API and return
    without doing anything.
    '''

    if not isinstance(api_object, ftrack_api.Session):
        return

    action = EncodeMedia(api_object)
    action.register()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)
    logging.info(
        'Registered actions and listening for event. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()
