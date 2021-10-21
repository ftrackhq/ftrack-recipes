#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import datetime
import logging

from ftrack_action_handler.action import BaseAction
import ftrack_api


class UserInterface(BaseAction):

    label = 'User interface'
    identifier = 'com.ftrack.recipes.user_interface'
    description = 'Example action returning a user interface.'

    def discover(self, session, entities, event):
        '''Return True if the action can be discovered.

        Check if the current selection can discover this action.

        '''
        # Always show this action.
        return True

    def interface(self, session, entities, event):
        widgets = [
            {
                'label': 'My String',
                'type': 'text',
                'value': 'no string',
                'name': 'my_string'
            }, {
                'label': 'My String2',
                'type': 'text',
                'value': 'no string2',
                'name': 'my_string2'
            }, {
                'label': 'My Date',
                'type': 'date',
                'name': 'my_date',
                'value': datetime.date.today().isoformat()
            }, {
                'label': 'My Number',
                'type': 'number',
                'name': 'my_number',
                'empty_text': 'Type a number here...'
            }, {
                'value': '## This is a label. ##',
                'type': 'label'
            }, {
                'label': 'Enter your text',
                'name': 'my_textarea',
                'value': 'some text',
                'type': 'textarea'
            }, {
                'label': 'My Boolean',
                'name': 'my_boolean',
                'value': True,
                'type': 'boolean'
            }, {
                'value': 'This field is hidden',
                'name': 'my_hidden',
                'type': 'hidden'
            }, {
                'label': 'My Enum',
                'type': 'enumerator',
                'name': 'my_enumerator',
                'data': [
                    {
                        'label': 'Option 1',
                        'value': 'opt1'
                    }, {
                        'label': 'Option 2',
                        'value': 'opt2'
                    }
                ]
            }
        ]

        return widgets

    def launch(self, session, entities, event):
        if 'values' in event['data']:
            values = event['data']['values']
            self.logger.info('Got values: {0}'.format(values))

            return {
                'success': True,
                'message': 'Ran my custom action successfully!'
            }


def register(session, **kw):
    '''Register plugin.'''
    if not isinstance(session, ftrack_api.Session):
        return

    action = UserInterface(session)
    action.register()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)

    session.event_hub.wait()
