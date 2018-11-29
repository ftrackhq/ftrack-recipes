# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import functools
import logging

import ftrack_api

logger = logging.getLogger('com.ftrack.recipes.cascade_status_change')


def get_status_by_state(project, state):
    '''Return a valid Status which matches *state*, for the given *project*.

    Raise an exception if the Shot Schema for *project* has no Status with the
    given *state*.
    '''
    for status in project['project_schema'].get_statuses('Shot'):
        if status['state']['short'] == state:
            return status

    raise ValueError(
        'No valid Shot status matching state {} for project {}'.format(
            state, project['full_name']))


def is_status_change(entity):
    '''Return if updated *entity* is a status change.'''
    is_task_entity = entity['entityType'] == 'task'
    is_add_update = entity.get('action') in ('add', 'update')
    is_status_change = 'statusid' in entity.get('keys', [])
    return (
        is_task_entity and is_add_update and is_status_change
    )


def get_state_name(task):
    '''Return the short name of *task*'s state, if valid, othertwise None.'''
    try:
        state = task['status']['state']['short']
    except KeyError:
        logger.info(u'Child {} has no status'.format(
            ftrack_api.inspection.identity(task)
        ))
        return
    if state not in ('BLOCKED', 'DONE', 'IN_PROGRESS', 'NOT_STARTED'):
        logger.warning(u'Unknown state returned: {}'.format(state))
        return
    return state


def get_new_shot_status(shot, tasks):
    '''Update *shot* based on status of *tasks*.

    Given a *shot* and a list of *tasks* belonging to that shot, determine
    the shots' status based on the task status'.
    '''
    logger.info('Current shot status: {}'.format(shot['status']['name']))

    task_states = set([get_state_name(task) for task in tasks], )
    task_states.discard(None)
    project = shot['project']
    new_status = None

    if task_states == set([u'DONE'], ):
        new_status = get_status_by_state(project, 'DONE')
    elif task_states == set([u'NOT_STARTED'], ):
        new_status = get_status_by_state(project, 'NOT_STARTED')
    elif 'BLOCKED' in task_states:
        new_status = get_status_by_state(project, 'BLOCKED')
    elif 'IN_PROGRESS' in task_states:
        new_status = get_status_by_state(project, 'IN_PROGRESS')

    if new_status is None:
        logger.info(u'No appropriate state to set')
        return None
    logger.info(u'New shot status is {} ({})'.format(
        new_status['name'], new_status['id']))
    return new_status['id']


def send_message_to_user(session, user_id):
    '''Send a success message to the active user.

    Use the event hub of *session* to pop up a message for the user with
    *user_id*. (Functionality new in ftrack 3.3.31.)
    '''
    session.event_hub.publish(
        ftrack_api.event.base.Event(
            topic='ftrack.action.trigger-user-interface',
            data=dict(
                type='message',
                success=True,
                message=('cascade_status_changes: '
                         'Shot status updated automatically')
            ),
            target='applicationId=ftrack.client.web and user.id="{0}"'.format(
                user_id)
        ),
        on_error='ignore'
    )


def cascade_status_changes_event_listener(session, event):
    '''Handle *event*.'''
    user_id = event['source'].get('user', {}).get('id', None)
    status_changed = False

    entities = event['data'].get('entities', [])
    for entity in entities:
        if not is_status_change(entity):
            continue

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
            if shot['status_id'] == new_shot_status_id:
                logger.info('Status is unchanged.')
                continue
            if new_shot_status_id is None:
                continue
            shot['status_id'] = new_shot_status_id
            status_changed = True

        else:
            logger.info('No shot found, ignoring update')

    if not status_changed:
        return
    # Persist changes
    try:
        session.commit()
    except Exception:
        logger.exception('Failed to update status')
        # Since we failed to synchronize our changes with the server, revert
        # our state to match what was on the server when we started.
        session.rollback()
        raise

    if not user_id:
        return

    send_message_to_user(session, user_id)


def register(session, **kw):
    '''Register event listener.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an incompatible API
    # and return without doing anything.
    if not isinstance(session, ftrack_api.Session):
        return

    # Register the event handler
    handle_event = functools.partial(cascade_status_changes_event_listener,
                                     session)
    session.event_hub.subscribe('topic=ftrack.update', handle_event)


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
