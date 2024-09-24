#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import os
import tempfile
import logging
import json
import urllib.request 

import ftrack_api
import xlsxwriter

from ftrack_action_handler.action import BaseAction


class CreateReviewReportAction(BaseAction):
    '''Create report action class.'''

    label = 'Create Review Report Action'
    identifier = 'com.ftrack.recipes.create_review_report'
    description = 'Create example report from selected Review'

    @property
    def session(self):
        '''Return convenient exposure of the self._session reference.'''
        return self._session

    @property
    def ftrack_server_location(self):
        '''Return the ftrack.server location.'''
        return self.session.query("Location where name is 'ftrack.server'").one()

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

        entity_type, entity_id = entities[0]
        review_session = session.get(entity_type, entity_id)

        # Create a new running Job.
        job = self._create_job(event)

        file_path = tempfile.NamedTemporaryFile(
            prefix='example_review_report', suffix='.xlsx', delete=False
        ).name

        try:
            self.create_excel_file(review_session, file_path)
        except Exception as error:
            self.logger.error(error)
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
        job_file = os.path.basename(file_path).replace('.xlsx', '')
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
        return {'success': True, 'message': 'Successfully generated project report.'}


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
                    {'description': str('Review Report Export (click to download)')}
                ),
            },
        )
        self.session.commit()
        return job

    def _get_review_thumbnails(self, review_session_object):
        thumb_local_urls = []
        rsoac = session.query(f"ReviewSessionObjectAnnotationComponent where review_session_object_id is '{review_session_object['id']}'").all()
        for thumb in rsoac:
            thumb_url = thumb['thumbnail_url']['url']
            thumb_name = f'{thumb["component_id"]}.jpg'
            tmpdir = tempfile.mkdtemp()
            thumb_path = os.path.join(tmpdir, thumb_name)
            self.logger.info(f'thumbanil url {thumb_url} --> {thumb_path}')

            thumb_local_url, header = urllib.request.urlretrieve(thumb_url, thumb_path)
            thumb_local_urls.append(thumb_local_url)
        return thumb_local_urls


    def create_excel_file(self, review_session, file_path):
        '''Generate excel file from *project_name* and output *file_path*.'''
        review_session_objects = review_session["review_session_objects"]
        self.logger.info(f'Extracting data from {review_session["name"]}')

        # Prepare excel file.
        xlsFile = xlsxwriter.Workbook(file_path)

        # Define bold style.
        bold16 = xlsFile.add_format(
            {
                'bold': True,
                'font_size': 16,
            }
        )

        # Define blue bold style.
        blue = xlsFile.add_format({'bold': True})
        blue.set_bg_color('588FBF')

        # Create worksheet.
        sheet = xlsFile.add_worksheet('Report')
        sheet.set_landscape()  # Set orientation
        sheet.set_paper(9)  # Set print size


        # Start populating excel file.
        sheet.write(0, 1, 'Review report for {0}'.format(review_session['name']), bold16)
        # Set styles on cells
        sheet.write(2, 1, 'Review Session', bold16)
        sheet.set_column(2, 1, 200)

        sheet.write(2, 2, 'Description', bold16)
        sheet.set_column(2, 2, 200)

        sheet.write(2, 3, 'Status', bold16)
        sheet.set_column(2, 3, 200)

        sheet.write(2, 4, 'Thumbnail', bold16)
        sheet.set_column(2, 4, 200)       

        # Write shot data into cells.
        for idx, review_object in enumerate(review_session_objects):
            self.logger.info(f'Processing data from {review_object}')

            thumbnails = self._get_review_thumbnails(review_object)
            print(thumbnails)
            for tid, thumbnail in enumerate(thumbnails):
                sheet.insert_image(idx + 3, tid + 4, thumbnail)
            # Get shot status color from server.
            # status_color = review_object['status']['color']

            # xls_shot_status = xlsFile.add_format({'bold': True, 'font_size': 20})
            # xls_shot_status.set_bg_color(status_color)

            # sheet.write(idx + 3, 1, review_object['name'], blue)
            # sheet.set_column(idx + 3, 1, 200)

            # sheet.write(idx + 3, 2, review_object['description'])
            # sheet.set_column(idx + 3, 2, 200)

            # sheet.write(idx + 3, 3, review_object['status']['name'], xls_shot_status)
            # sheet.set_column(idx + 3, 3, 200)

        xlsFile.close()


def register(api_object, **kw):
    '''Register hook with provided *api_object*.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(api_object, ftrack_api.session.Session):
        return

    action = CreateReviewReportAction(api_object)
    action.register()


if __name__ == '__main__':
    # To be run as standalone code.
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)

    # Wait for events
    logging.info('Registered actions and listening for events. Use Ctrl-C to abort.')
    session.event_hub.wait()
