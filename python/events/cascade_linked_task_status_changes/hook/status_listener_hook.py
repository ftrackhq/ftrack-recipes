#!/usr/bin/env python

import functools
import logging

import ftrack_api

logger = logging.getLogger('com.ftrack.recipes.cascade_status_change')

"""
When an upstream task status is set to "Approved", then set its downstream task
status to "Ready"

"""



def is_task_status_change(entity):
    '''Return if updated *entity* is a status change on an Asset Version.'''
    is_task_entity = entity['entityType'] == 'task'
    is_add_update = entity.get('action') in ('update')
    is_status_change = 'statusid' in entity.get('keys', [])
    return is_task_entity and is_add_update and is_status_change


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
                    'cascade_status_changes: ' 'Task status updated automatically'
                ),
            ),
            target='applicationId=ftrack.client.web and user.id="{0}"'.format(user_id),
        ),
        on_error='ignore',
    )


def get_status_list(task):
    project = session.query(
        'select project_schema from Project '
        'where id is "{0}"'.format(task['project_id'])
    ).first()

    project_schema = project['project_schema']

    task_workflow_schema = session.query(
        'WorkflowSchema where id is "{0}"'.format(
            project_schema['task_workflow_schema_id']
        )
    ).first()

    task_statuses = task_workflow_schema['statuses']

    return task_statuses


def status_lookup(task, status_id):
    status_list = get_status_list(task)
    for status in status_list:
        if status['id'] == status_id:
            return status['name']

def update_outgoing_task_status(session, event):
    '''Event callback printing all new or updated entities.'''

    user_id = event['source'].get('user', {}).get('id', None)
    status_changed = False

    entities = event['data'].get('entities', [])
    for entity in entities:

        if is_task_status_change(entity):

            print('---------------------------------------------------------------')

            print('An upstream task status has changed!')

            entity_id = entity['entityId']
            task = session.query(
                'Task where id is "{0}"'.format(entity_id)
            ).first()

            if task:
                task_statuses = get_status_list(task)

                print("Upstream task id: {}".format(entity_id))
                print("Upstream task name: {}".format(task['name']))
                try:
                    print("Upstream task old status: {}".format(status_lookup(task, entity['changes']['statusid']['old'])))
                    print("Upstream task new status: {}".format(status_lookup(task, entity['changes']['statusid']['new'])))
                except TypeError as e:
                    print("TypeError! {}".format(e))

                #if task['status']['name'] == 'Approved':
                if status_lookup(task, entity['changes']['statusid']['new']) == 'Approved':

                    print('Upstream Task is now "Approved"...')

                    session.populate(task, 'outgoing_links')
                    outgoing_links = task['outgoing_links']

                    print("Number of downstream tasks: {}".format(len(outgoing_links)))

                    for outgoing_link in outgoing_links:

                        task = outgoing_link.get('to')
                        session.populate(task, 'id,status')
                        downstream_task = session.query('Task where id = "{}"'.format(task['id'])).one()

                        if downstream_task.entity_type == 'Task':
                            print('Downstream link is a task')
                            print('Downstream task status: {}'.format(downstream_task['status']['name']))

                            ready_status = None
                            not_started_status = None
                            for status in task_statuses:
                                if status['name'] == 'Ready':
                                    ready_status = status
                                if status['name'] == 'Not Started':
                                    not_started_status = status

                            if downstream_task['status'] == not_started_status:
                                '''
                                Only change the status from "Not Started" to
                                "Ready" to trigger the notification to the artist
                                who's waiting on the up-steam task to complete.
                                '''
                                #
                                print('setting downstream task to "Ready"')
                                downstream_task['status'] = ready_status
                                status_changed = True
                            else:
                                print('NO ACTION because downstream task status is: {}'.format(downstream_task['status']['name']))
                                # from IPython import embed; embed()

            else:
                print('not a task')

    if not status_changed:
        return
    # Persist changes
    try:
        session.commit()
    except Exception:
        logger.exception('Failed to update task status')
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
    #handle_event = functools.partial(cascade_status_changes_event_listener, session)
    handle_event = functools.partial(update_outgoing_task_status, session)
    session.event_hub.subscribe('topic=ftrack.update', handle_event)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Remember, in version version 2.0 of the ftrack-python-api the default
    # behavior will change from True to False.
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)
    logging.info('Registered actions and listening for events. Use Ctrl-C to abort.')
    session.event_hub.wait()

