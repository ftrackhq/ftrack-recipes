# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack
import json

import functools
import logging
import os

import ftrack_api

import logging
logger = logging.getLogger()
logger.setLevel("INFO")

ALLOWED_STATES = ('BLOCKED', 'DONE', 'IN_PROGRESS', 'NOT_STARTED')

SUCCESS_RESPONSE = {
    "statusCode": 200,
    "body": json.dumps({
        "message": "SUCCESS",
    }),
}


ERROR_RESPONSE = {
    "statusCode": 400,
    "body": json.dumps({
        "error": "An error occurred during the lambda execution. Please check logs",
    }),
}


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
                message=(
                    'cascade_status_changes: ' 'Shot status updated automatically'
                ),
            ),
            target=f'applicationId=ftrack.client.web and user.id="{user_id}"'
        ),
        on_error='ignore',
    )

def get_status_by_state(project, state):
    '''Return a valid Status which matches *state*, for the given *project*.

    Raise an exception if the Shot Schema for *project* has no Status with the
    given *state*.
    '''
    for status in project['project_schema'].get_statuses('Shot'):
        if status['state']['short'] == state:
            return status

    raise ValueError(
        f'No valid Shot status matching state {state} for project { project["full_name"]}'
    )


def get_state_name(task):
    '''Return the short name of *task*'s state, if valid, othertwise None.'''
    try:
        state = task['status']['state']['short']
    except KeyError:
        task_identity = ftrack_api.inspection.identity(task)
        logger.info(
            f'Child {task_identity} has no status'
        )
        return
    if state not in ALLOWED_STATES:
        logger.warning(f'Unknown state returned: {state}')
        return
    return state


def get_new_shot_status(shot, tasks):
    '''Update *shot* based on status of *tasks*.

    Given a *shot* and a list of *tasks* belonging to that shot, determine
    the shots' status based on the task status'.
    '''
    logger.info(f'Current shot status: {shot["status"]["name"]}')

    task_states = set(
        [get_state_name(task) for task in tasks],
    )
    task_states.discard(None)
    project = shot['project']
    new_status = None

    if task_states == set(['DONE'],):
        new_status = get_status_by_state(project, 'DONE')
    elif task_states == set(['NOT_STARTED'],):
        new_status = get_status_by_state(project, 'NOT_STARTED')
    elif 'BLOCKED' in task_states:
        new_status = get_status_by_state(project, 'BLOCKED')
    elif 'IN_PROGRESS' in task_states:
        new_status = get_status_by_state(project, 'IN_PROGRESS')

    if new_status is None:
        logger.info('No appropriate state to set')
        return None
    logger.info(
        'New shot status is {} ({})'.format(new_status['name'], new_status['id'])
    )
    return new_status['id']

def cascade_status_changes_event_listener(session, event):
    '''Handle *event*.'''
    user_id = event['metadata']['resource_id']

    status_changed = False
    
    entity_id = event['entity']['id'][0]
    logger.info(f'entity_id : {entity_id}')
    
    shot_query = f'select status_id, status.name from Shot where children any (id is "{entity_id}")'
    logger.info(f'shot_query: {shot_query}')

    shot = session.query(shot_query).first()
    logger.info(f'shot : {shot}')

    if shot:
        shot_id = shot['id']
        tasks = session.query(
            'select type.name, status.state.short from Task '
            f'where parent_id is "{shot_id}"'
        )
        new_shot_status_id = get_new_shot_status(shot, tasks)
        if shot['status_id'] == new_shot_status_id:
            logger.info('Status is unchanged.')
            return ERROR_RESPONSE
        
        if new_shot_status_id is None:
            return ERROR_RESPONSE
        
        shot['status_id'] = new_shot_status_id
        logger.info(f'Status has been updated to id : {new_shot_status_id}')

        status_changed = True

    else:
        logger.info('No shot found, ignoring update')

    if not status_changed:
        return ERROR_RESPONSE
    
    # Persist changes
    try:
        session.commit()
    except Exception:
        logger.exception('Failed to update status')
        # Since we failed to synchronize our changes with the server, revert
        # our state to match what was on the server when we started.
        session.rollback()
        raise

    send_message_to_user(session, user_id)

    return SUCCESS_RESPONSE

def lambda_handler(event, context):
    logger.info('starting lambda call')
    event_body = json.loads(event['body'])
    session = ftrack_api.Session(auto_connect_event_hub=True, schema_cache_path=False)
    return cascade_status_changes_event_listener(session, event_body)
