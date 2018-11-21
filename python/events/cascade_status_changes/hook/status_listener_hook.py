# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import functools
import logging

import ftrack_api

logger = logging.getLogger('cascade_status_changes_event_listener')


def get_status_by_state(project, state):
    '''Return a Status matching *state* belonging to the Schema for *project*,
    if available.

    '''
    shot_id = session.query(
        'select id from ObjectType where name is "Shot"').one()['id']

    shot_schema = [schema
                   for schema in project['project_schema']['_schemas']
                   if schema['type_id'] == shot_id][0]
    for status in shot_schema['statuses']:
        if status['task_status']['state']['short'] == state:
            return status['task_status']
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


def get_new_shot_status(shot, tasks):
    '''Update *shot* based on status of *tasks*.

    Given a *shot* and a list of *tasks* belonging to that shot, determine
    the shots' status based on the task status\''''
    logger.info('Current shot status: {}'.format(shot['status']['name']))

    any_blocked = False
    all_not_started = True
    any_in_progres = False
    all_done = True

    # TODO convert to set of states
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

    project = session.get('Project', shot['project_id'])
    new_status = None
    if all_done:
        new_status = get_status_by_state(project, 'DONE')
    elif all_not_started:
        new_status = get_status_by_state(project, 'NOT_STARTED')
    elif any_blocked:
        new_status = get_status_by_state(project, 'BLOCKED')
    elif any_in_progres:
        new_status = get_status_by_state(project, 'IN_PROGRESS')

    if new_status is None:
        logger.info(u'No appropriate state to set')
        return None
    logger.info(u'Updating shot status to {} ({})'.format(
        new_status['name'], new_status['id']))
    return new_status['id']


def cascade_status_changes_event_listener(session, event):
    '''Handle *event*.'''
    user_id = event['source'].get('user', {}).get('id', None)
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
