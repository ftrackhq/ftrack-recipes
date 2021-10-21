#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

import logging

from ftrack_action_handler.action import BaseAction
import ftrack_api


RUN_AS_ACTION = True  # Set to False to run as an event listener.
UPDATE_LABELS = True  # Set to False to create comments instead.


class UpdateReviewClips(BaseAction):
    '''Demonstrates two methods of marking review clips with the name of the
    original media they represent. While presented as an action, the
    proces_event() method is suitable for use as an event listener, running on
    clips as they are added to a review.
    '''

    label = 'Update Clips'
    identifier = 'com.ftrack.recipes.update_clips'
    description = 'Update review session clips based on original filename'

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
        if not entities:
            return False

        entity_type, entity_id = entities[0]
        return entity_type == 'ReviewSession'

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

        review_session_objects = session.query(
            'ReviewSessionObject where review_session_id is "{0}"'.format(entity_id)
        ).all()

        for review_session_object in review_session_objects:
            self._update_review_session_object(review_session_object)
        session.commit()

        return True

    def _update_review_session_object(self, review_session_object):
        '''Update a *review_session_object* with the uploaded media's filename.

        We find the filename on the metadata associated with the web-reviewable
        Component on the version which corresponds to *review_session_object*.

        *review_session_object* is a ReviewSessionObject representing the clip
        in question.
        '''
        review_component = self.session.query(
            'select metadata from Component where name like "ftrackreview-%"'
            ' and version_id is "{0}"'.format(review_session_object['version_id'])
        ).one()
        source_component = self.session.get(
            'Component', review_component['metadata']['source_component_id']
        )

        if UPDATE_LABELS:
            self._update_clip_label(review_session_object, source_component['name'])
        else:
            self.comment_on_clip(review_session_object, source_component['name'])

    def _comment_on_clip(self, review_session_object, source_name):
        '''Create a comment with content *source_name* on a clip.

        *review_session_object* is a ReviewSessionObject representing the clip
        in question.

        *source_name* is a string representing the desired label or filename.
        '''
        current_user = self.session.query(
            'User where username is {0}'.format(self.session.api_user)
        ).one()
        review_session_object.create_note(source_name, current_user)

    def _update_clip_label(self, review_session_object, source_name):
        '''Update fields comprising the label for a ReviewSessionObject clip.

        The three attributes which are displayed over clips in a ReviewSession
        timeline are "name", "description", and "version". Technically all
        optional, depending on how the clip was created and what its parent is,
        one or two may start out blank.

        *review_session_object* is a ReviewSessionObject representing the clip
        in question.

        *source_name* is a string representing the desired label or filename.
        '''
        review_session_object['name'] = ''
        review_session_object['description'] = ''
        review_session_object['version'] = source_name

    def process_event(self, event):
        '''When a clip is added to a review, update it with the filename.

        *event* is an ftrack_api.event.base.Event object.

        '''
        for entity in event['data']['entities']:
            if entity['action'] != 'add':
                continue
            if entity['entityType'] != 'reviewsessionobject':
                continue
            review_session_object = self.session.get(
                'ReviewSessionObject', entity['entityId']
            )
            self._update_review_session_object(review_session_object)
        self.session.commit()


def register(api_object, **kw):
    '''Register hook with provided *api_object*.

    Validate that session is an instance of ftrack_api.Session. If not, assume
    that register() is being called from an old or incompatible API and return
    without doing anything.
    '''

    if not isinstance(api_object, ftrack_api.Session):
        return

    action = UpdateReviewClips(api_object)

    if RUN_AS_ACTION:
        action.register()
    else:
        api_object.event_hub.subscribe('topic=ftrack.update', action.process_event)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)
    logging.info('Registered actions and listening for event. Use Ctrl-C to abort.')
    session.event_hub.wait()
