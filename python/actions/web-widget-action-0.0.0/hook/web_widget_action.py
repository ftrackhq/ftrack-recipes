# :coding: utf-8
# :copyright: Copyright (c) 2024 ftrack

import logging
import ftrack_api
from ftrack_action_handler.action import BaseAction


class MyWebWidgetAction(BaseAction):
    identifier = 'my.webwidget.action'
    label = 'My Web Widget Action'
    description = 'This is an example action'

    def discover(self, session, entities, event):
        """
        Method that responds to the discovery message.

        This will always return the action in any context.
        """
        return True
    
    def launch(self, session, entities, event):
        """
        Method that responds to messages to launch the action.

        This will simply just return a web widget with the specified URL.
        """
        return {
            'success': True,
            'message': 'success', # Required
            'type': 'widget',
            'url': 'https://www.example.com',
            'title': 'My Web Widget Action'
        }


def register(session, **kw):
    '''Register plugin.'''
    if not isinstance(session, ftrack_api.Session):
        return

    action = MyWebWidgetAction(session)
    action.register()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)

    session.event_hub.wait()



