# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import functools
import logging

import ftrack_api

logger = logging.getLogger('cascade_status_changes_event_listener')


status_map = {
    'any_blocked': 'a0bc2444-15e2-11e1-b21a-0019bb4983d8',  # On Hold
    'all_not_started': '44dd9fb2-4164-11df-9218-0019bb4983d8',  # Not started
    'any_in_progres': '44ddd0fe-4164-11df-9218-0019bb4983d8',  # In progress
    'all_done': '44de097a-4164-11df-9218-0019bb4983d8'  # Approved
}


def is_status_change(entity):
    '''Return if updated *entity* is a status change.'''
    is_task_entity = entity['entityType'] == 'task'
    is_add_update = entity.get('action') in ('add', 'update')
    is_status_change = 'statusid' in entity.get('keys', [])
    return (
        is_task_entity and is_add_update and is_status_change
    )


def get_new_shot_status(shot, tasks):
    '''Update statuses for *shot*.'''
    logger.info('Current shot status: {}'.format(shot['status']['name']))

    any_blocked = False
    all_not_started = True
    any_in_progres = False
    all_done = True

    for child in tasks:
        try:
            state = child['status']['state']['short']
        except KeyError:
            logger.info(u'Child {} has no status'.format(
                ftrack_api.inspection.identity(child)
            ))
            continue

        if state == 'BLOCKED':
            all_not_started = False
            all_done = False
            any_blocked = True
        elif state == 'NOT_STARTED':
            all_done = False
        elif state == 'IN_PROGRESS':
            all_not_started = False
            all_done = False
            any_in_progres = True
        elif state == 'DONE':
            all_not_started = False
        else:
            logger.warning(u'Unknown state returned: {}'.format(state))
            continue

    new_status_id = None
    if all_done:
        new_status_id = status_map['all_done']
    elif all_not_started:
        new_status_id = status_map['all_not_started']
    elif any_blocked:
        new_status_id = status_map['any_blocked']
    elif any_in_progres:
        new_status_id = status_map['any_in_progres']

    logger.info(u'Updating shot status to {}'.format(new_status_id))
    return new_status_id


def cascade_status_changes_event_listener(session, event):
    '''Handle *event*.'''
    user_id = event['source'].get('user', {}).get('id', None)
    if not user_id:
        logger.warning('No source user...')
    status_changed = False

    entties = event['data'].get('entities', [])
    for entity in entties:
        if is_status_change(entity):
            entity_id = entity['entityId']
            shot = session.query(
                'select status_id, status.name from Shot '
                'where children any (id is "{0}")'.format(entity_id)
            ).first()
            if shot:
                tasks = session.query(
                    'select type.name, status.state.short from Task '
                    'where parent_id is "{}"'.format(shot['id'])
                )
                new_shot_status_id = get_new_shot_status(shot, tasks)
                if shot['status_id'] != new_shot_status_id:
                    shot['status_id'] = new_shot_status_id
                    status_changed = True
            else:
                logger.info('No shot found, ignoring update')

    if status_changed:
        # Persist changes
        try:
            session.commit()
        except Exception:
            logger.exception('Failed to update status')
            session.rollback()
            raise

    if user_id and status_changed:
        # Trigger a message to the user (new in ftrack 3.3.31)
        session.event_hub.publish(
            ftrack_api.event.base.Event(
                topic='ftrack.action.trigger-user-interface',
                data=dict(
                    type='message',
                    success=True,
                    message='Shot status updated automatically'
                ),
                target='applicationId=ftrack.client.web and user.id="{0}"'.format(
                    user_id)
            ),
            on_error='ignore'
        )


def register(session, **kw):
    '''Register event listener.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an incompatible API
    # and return without doing anything.
    if not isinstance(session, ftrack_api.Session):
        # Exit to avoid registering this plugin again.
        return

    # Register the event handler
    handle_event = functools.partial(cascade_status_changes_event_listener,
                                     session)
    session.event_hub.subscribe('topic=ftrack.update', handle_event)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session()
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()
