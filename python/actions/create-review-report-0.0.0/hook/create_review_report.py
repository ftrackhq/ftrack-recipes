#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import os
import tempfile
import logging
import json

import ftrack_api
from fpdf import FPDF

from ftrack_action_handler.action import BaseAction


class CreateReportAction(BaseAction):
    '''Create report action class.'''

    label = 'Create Review Report Action'
    identifier = 'com.ftrack.recipes.create_review_report'
    description = 'Create example report from selected Review'

    @property
    def session(self):
        '''Return convenient exposure of the self._session reference.'''
        return self._session

    @property
    def ftrack_review_location(self):
        '''Return the ftrack.review location.'''
        return self.session.query("Location where name is 'ftrack.review'").one()

    def validate_selection(self, entities):
        '''Return True if the selection is valid.

        Utility method to check *entities* validity.

        '''
        if not entities:
            return False

        entity_type, entity_id = entities[0]
        if entity_type == 'ReviewSession':
            return True

        return False

    def discover(self, session, entities, event):
        '''Return True if the action can be discovered.

        Check if the current selection can discover this action.

        '''
        return self.validate_selection(entities)

    def launch(self, session, entities, event):
        '''Return result of running action.'''

        self.logger.info('Launching action with selection {0}'.format(entities))
        review_session = self.session.get(entities[0][0], entities[0][1])

        # Create a new running Job.
        job = self._create_job(event)

        file_path = tempfile.NamedTemporaryFile(
            prefix='example_review_report', suffix='.pdf', delete=False
        ).name

        try:
            self.create_excel_file(review_session, file_path)
        except Exception as error:
            # If an exception happens in the document generation
            # mark the job as failed.
            job['status'] = 'failed'
            job['data'] = json.dumps({'description': str(error)})
            # Commit job status changes and description.
            self.session.commit()

            # Return an error message to the user.
            return {
                'success': False,
                'message': 'An error occured during the document generation.',
            }

        # Create component on the server, name it and attach it the job.
        job_file = os.path.basename(file_path).replace('.pdf', '')
        component = self.session.create_component(
            file_path, data={'name': job_file}, location=self.ftrack_server_location
        )
        self.session.commit()

        # Create job component.
        self.session.create(
            'JobComponent', {'component_id': component['id'], 'job_id': job['id']}
        )
        # Set job status as done.
        job['status'] = 'done'
        self.session.commit()

        # Return the successful status to the user.
        return {'success': True, 'message': 'Successfully generated review report.'}


    def _create_job(self, event):
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
                'data': json.dumps(
                    {'description': str('Project Report Export (click to download)')}
                ),
            },
        )
        self.session.commit()
        return job

    def create_excel_file(self, review_session, file_path):
        '''Generate excel file from *review_session* and output *file_path*.'''

        review_session_name = f"Review : {review_session['name']} \nProject: {review_session['project']['name']}"

        pdf = FPDF()
        pdf.set_author(self.session.api_user)
        pdf.set_title(review_session_name)

        # Write versions data into cells.
        review_session_objects = review_session['review_session_objects']
        for i, review_session_object in enumerate(review_session_objects):

            annotations = review_session_object['annotations']
            print(annotations)

            description = review_session_object['description']
            print(description)

            asset_version = review_session_objects['asset_version']
            print(asset_version)

            review_version = review_session_objects['version']
            print(review_version)

            review_status = review_session_objects['statuses']
            print(review_status)

            for annotation in annotations:
                print(annotation)
                frame_number = annotation['frame_number']
                data = annotation['data']
                created_at = annotation['created_at']
                print(data)

        print(file_path)
        pdf.output(file_path)



def register(api_object, **kw):
    '''Register hook with provided *api_object*.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(api_object, ftrack_api.session.Session):
        return

    action = CreateReportAction(api_object)
    action.register()


if __name__ == '__main__':
    # To be run as standalone code.
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)

    # Wait for events
    logging.info('Registered actions and listening for events. Use Ctrl-C to abort.')
    session.event_hub.wait()
