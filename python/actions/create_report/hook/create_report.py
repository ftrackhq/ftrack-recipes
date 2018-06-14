#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import os
import tempfile
import logging
import json

import ftrack_api
import xlsxwriter
import arrow

from ftrack_action_handler.action import BaseAction


class CreateReportAction(BaseAction):
    label = 'Create Report Action'
    identifier = 'com.ftrack.recipes.create_report'
    description = 'Create example report from selected Project'

    @property
    def session(self):
        '''Convenient exposure of the self._session reference.'''
        return self._session

    @property
    def ftrack_server_location(self):
        '''Return the ftrack.server location.'''
        return self.session.query(
            u"Location where name is 'ftrack.server'"
        ).one()

    def validate_selection(self, entities):
        '''
        Utility method to check *entities* validity.
        Return True if the selection is valid.
        '''
        if not entities:
            return False

        entity_type, entity_id = entities[0]
        if entity_type == 'Project':
            return True

        return False

    def discover(self, session, entities, event):
        '''
        Check if the current selection can discover this action.
        Return True if the action can be discovered.
        '''
        return self.validate_selection(entities)

    def launch(self, session, entities, event):
        '''If can be discovered, we can then run the action.'''

        self.logger.info(
            u'Launching action with selection {0}'.format(entities)
        )

        values = event['data'].get('values', {})

        # If there's no value coming from the ui, we can bail out.
        if not values:
            return

        # Create a new running Job.
        job = self._create_job(event)

        file_path = tempfile.NamedTemporaryFile(
            prefix='example_utilization_report', 
            suffix='.xlsx', 
            delete=False
        ).name

        try:
            self.create_excel_file(values['project_name'], file_path)
        except Exception as error:
            # If an exception happens in the document generation
            # mark the job as failed.
            job['status'] = 'failed'
            job['data'] = json.dumps({
                'description': unicode(error)
            })
            # Commit job status changes and description.
            self.session.commit()

            # Return an error message to the user.
            return {
                'success': False,
                'message': u'An error occured during the document generation.'
            }

        # Create component on the server, name it and attach it the job.
        job_file = os.path.basename(file_path).replace('.xlsx', '')
        component = self.session.create_component(
            file_path,
            data={'name': job_file},
            location=self.ftrack_server_location
        )
        self.session.commit()

        # Create job component.
        self.session.create(
            'JobComponent',
            {
                'component_id': component['id'], 
                'job_id': job['id']
            }
        )
        # Set job status as done.
        job['status'] = 'done'
        self.session.commit()

        # Return the successful status to the user.
        return {
            'success': True,
            'message': u'Successfully generated project report.'
        }

    def interface(self, session, entities, event):
        values = event['data'].get('values', {})
        # Interface will be raised as long as there's no value set.
        # here is a good place where to put validations.
        if values:
            return

        # Get the project object.
        project = self.session.get('Project', entities[0][1])

        # Populate ui with the project name.
        widgets = [
            {
                'label': 'Project',
                'value': project['name'],
                'name': 'project_name',
                'type': 'text'
            }
        ]

        return widgets

    def _create_job(self, event):
        '''
        Create and ftrack job entity from **event* 
        and set status to running.
        '''

        user_id = event['source']['user']['id']
        job = self.session.create(
            'Job',
            {
                'user': self.session.get('User', user_id),
                'status': 'running',
                'data': json.dumps({
                    'description': unicode(
                        'Project Report Export (click to download)'
                    )}
                )
            }
        )
        self.session.commit()
        return job

    def create_excel_file(self, project_name, file_path):
        '''
        Utility function to generate the excel file given
        *project_name* and the output *file_path*.
        '''

        # Prepare excel file.
        xlsFile = xlsxwriter.Workbook(file_path)

        # Define bold style.
        bold16 = xlsFile.add_format({'bold': True, 'font_size': 16, })

        # Define blue bold style.
        blue = xlsFile.add_format({'bold': True})
        blue.set_bg_color('588FBF')

        # Create worksheet.
        sheet = xlsFile.add_worksheet('Report')
        sheet.set_landscape()  # Set orientation
        sheet.set_paper(9)  # Set print size

        # Query server for data.
        project = self.session.query(
            'Project where name is "{0}"'.format(project_name)
        ).one()

        # Fetch shots from the project.
        shots = self.session.query('Shot where project.id is "{0}"'.format(
            project['id']
        )).all()

        # Start populating excel file.
        sheet.write(
            0,
            1,
            u'Project report for {0}'.format(
                project['name']
            ),
            bold16
        )
        # Set styles on cells
        sheet.write(2, 1, 'Shots', bold16)
        sheet.write(2, 2, 'Description', bold16)
        sheet.write(2, 3, 'Status', bold16)

        # Write shot data into cells.
        for idx, shot in enumerate(sorted(shots)):
            # Get shot status color from server.
            status_color = shot['status']['color']

            xls_shot_status = xlsFile.add_format(
                {'bold': True, 'font_size': 20}
            )
            xls_shot_status.set_bg_color(status_color)

            sheet.write(idx + 3, 1, shot['name'], blue)
            sheet.write(idx + 3, 2, shot['description'])
            sheet.write(idx + 3, 3, shot['status']['name'], xls_shot_status)

        xlsFile.close()


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
    session = ftrack_api.Session()
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()
