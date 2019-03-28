#!/usr/bin/env python2
# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

import logging

from ftrack_action_handler.action import BaseAction
import ftrack_api


class UpdateReviewClips(BaseAction):
    label = 'Update Clips'
    identifier = 'com.ftrack.recipes.update_clips'
    description = 'Update review session clips based on original filename'

    def discover(self, session, entities, event):
        '''Return True to be discovered when *entities* contains a review.

        This action should only be available when a review session is selected.
        For the moment we trust that our user has permissions to perform the
        needed actions.
        '''
        if not entities:
            return False

        entity_type, entity_id = entities[0]
        return entity_type == 'ReviewSession'

    def launch(self, session, entities, event):
        entity_type, entity_id = entities[0]

        review_session_objects = session.query(
            'ReviewSessionObject where review_session_id is "{0}"'.format(
                entity_id
            )
        ).all()

        for review_session_object in review_session_objects:
            self._update_review_session_object(review_session_object)
        session.commit()

        return True

    def _update_review_session_object(self, review_session_object):
        review_component = self.session.query(
            'select metadata from Component where name is ftrackreview-mp4'
            ' and version_id is "{0}"'.format(
                review_session_object['version_id']
            )
        ).one()
        source_component = self.session.get(
            'Component',
            review_component['metadata']['source_component_id']
        )
        ## Chose one
        self._update_clip_label(review_session_object, source_component['name'])
        # self.comment_on_clip(review_session_object, source_component['name'])

    def _comment_on_clip(self, review_session_object, source_name):
        current_user = self.session.query(
            u'User where username is {0}'.format(self.session.api_user)).one()
        review_session_object.create_note(source_name, current_user)

    def _update_clip_label(self, review_session_object, source_name):
        # These three fields control the label on the clips in the timeline.
        review_session_object['name'] = ''
        review_session_object['description'] = ''
        review_session_object['version'] = source_name

    def process_event(self, event):
        '''When a clip is added to a review, update it with the filename.'''
        for entity in event['data']['entities']:
            if entity['action'] != 'add':
                continue
            if entity['entityType'] != 'reviewsessionobject':
                continue
            review_session_object = self.session.get(
                'ReviewSessionObject',
                entity['entityId']
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
    ## Chose one
    # To enable an action witin a client review
    action.register()
    # To automatically update clips
    # api_object.event_hub.subscribe('topic=ftrack.update', action.process_event)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Remember, in version version 2.0 of the ftrack-python-api the default
    # behavior will change from True to False.
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)
    logging.info(
        'Registered actions and listening for event. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()
