# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import functools
import logging

import ftrack_api

logger = logging.getLogger('com.ftrack.recipes.server-to-local-storage')


def transfer_to_local(session, event):
    current_location = session.pick_location()

    component_id = event['data'].get('component_id')
    location_id = event['data'].get('location_id')
    print(component_id, location_id)

    if not component_id or not location_id:
        return

    component = session.get('Component', component_id)
    location = session.get('Location', location_id)

    current_location.add_component(component, location)


def register(session, **kw):
    '''Register event listener.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an incompatible API
    # and return without doing anything.
    if not isinstance(session, ftrack_api.Session):
        return

    # Register the event handler
    handle_event = functools.partial(transfer_to_local, session)
    session.event_hub.subscribe(
        'topic=ftrack.location.component-added and'
        ' source.applicationId="ftrack.client.web"', 
        handle_event
    )


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Remember, in version version 2.0 of the ftrack-python-api the default
    # behavior will change from True to False.
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()