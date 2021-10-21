# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

import json
import sys
import argparse
import logging
import threading
import collections

import ftrack_api
import ftrack_api.exception
import ftrack_action_handler.action

SUPPORTED_ENTITY_TYPES = ('AssetVersion', 'TypedContext', 'Project', 'Component')


def async(fn):
    '''Run *fn* asynchronously.'''

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()

    return wrapper


def get_filter_string(entity_ids):
    '''Return a comma separated string of quoted ids from *entity_ids* list.'''
    return ', '.join('"{0}"'.format(entity_id) for entity_id in entity_ids)


class TransferComponentsAction(ftrack_action_handler.action.BaseAction):
    '''Action to transfer components between locations.'''

    #: Action identifier.
    identifier = 'transfer-components'

    #: Action label.
    label = 'Transfer component(s)'

    #: Action description.
    description = 'Transfer component(s) between locations.'

    #: Excluded Locations
    excluded_locations = ['ftrack.origin', 'ftrack.connect']

    def validate_entities(self, entities):
        '''Return if *entities* is valid.'''
        if len(entities) >= 1 and all(
            [entity_type in SUPPORTED_ENTITY_TYPES for entity_type, _ in entities]
        ):
            self.logger.info('Selection is valid')
            return True
        else:
            self.logger.info('Selection is _not_ valid')
            return False

    def discover(self, session, entities, event):
        '''Return True if action is valid.'''
        self.logger.info('Discovering action with entities: {0}'.format(entities))
        return self.validate_entities(entities)

    def get_components_in_location(self, session, entities, location):
        '''Return list of components in *entities*.'''
        component_queries = []
        entity_groups = collections.defaultdict(list)
        for entity_type, entity_id in entities:
            entity_groups[entity_type].append(entity_id)

        if entity_groups['Project']:
            component_queries.append(
                'Component where (version.asset.parent.project.id in ({0}) or '
                'version.asset.parent.id in ({0}))'.format(
                    get_filter_string(entity_groups['Project'])
                )
            )

        if entity_groups['TypedContext']:
            component_queries.append(
                'Component where (version.asset.parent.ancestors.id in ({0}) or '
                'version.asset.parent.id in ({0}))'.format(
                    get_filter_string(entity_groups['TypedContext'])
                )
            )

        if entity_groups['AssetVersion']:
            component_queries.append(
                'Component where version_id in ({0})'.format(
                    get_filter_string(entity_groups['AssetVersion'])
                )
            )

        if entity_groups['Component']:
            component_queries.append(
                'Component where id in ({0})'.format(
                    get_filter_string(entity_groups['Component'])
                )
            )

        components = set()
        for query_string in component_queries:
            components.update(
                session.query(
                    '{0} and component_locations.location_id is "{1}"'.format(
                        query_string, location['id']
                    )
                ).all()
            )

        self.logger.info('Found {0} components in selection'.format(len(components)))
        return list(components)

    @async
    def transfer_components(
        self,
        entities,
        source_location,
        target_location,
        user_id=None,
        ignore_component_not_in_location=False,
        ignore_location_errors=False,
    ):
        '''Transfer components in *entities* from *source_location*.

        if *ignore_component_not_in_location*, ignore components missing in
        source location. If *ignore_location_errors* is specified, ignore all
        locations-related errors.

        Reports progress back to *user_id* using a job.

        '''

        session = ftrack_api.Session(auto_connect_event_hub=False)
        job = session.create(
            'Job',
            {
                'user_id': user_id,
                'status': 'running',
                'data': json.dumps(
                    {'description': 'Transfer components (Gathering...)'}
                ),
            },
        )
        session.commit()
        try:
            components = self.get_components_in_location(
                session, entities, source_location
            )
            amount = len(components)
            self.logger.info('Transferring {0} components'.format(amount))

            for index, component in enumerate(components, start=1):
                self.logger.info(
                    'Transferring component ({0} of {1})'.format(index, amount)
                )
                job['data'] = json.dumps(
                    {
                        'description': 'Transfer components ({0} of {1})'.format(
                            index, amount
                        )
                    }
                )
                session.commit()

                try:
                    target_location.add_component(component, source=source_location)
                except ftrack_api.exception.ComponentInLocationError:
                    self.logger.info(
                        'Component ({}) already in target location'.format(component)
                    )
                except ftrack_api.exception.ComponentNotInLocationError:
                    if ignore_component_not_in_location or ignore_location_errors:
                        self.logger.exception('Failed to add component to location')
                    else:
                        raise
                except ftrack_api.exception.LocationError:
                    if ignore_location_errors:
                        self.logger.exception('Failed to add component to location')
                    else:
                        raise

            job['status'] = 'done'
            session.commit()

            self.logger.info('Transfer complete ({0} components)'.format(amount))

        except BaseException:
            self.logger.exception('Transfer failed')
            session.rollback()
            job['status'] = 'failed'
            session.commit()

    def launch(self, session, entities, event):
        '''Launch edit meta data action.'''
        self.logger.info('Launching action with selection: {0}'.format(entities))
        values = event['data']['values']
        self.logger.info('Received values: {0}'.format(values))

        source_location = session.get('Location', values['from_location'])
        target_location = session.get('Location', values['to_location'])
        if source_location == target_location:
            return {
                'success': False,
                'message': 'Source and target locations are the same.',
            }

        ignore_component_not_in_location = (
            values.get('ignore_component_not_in_location') == 'true'
        )
        ignore_location_errors = values.get('ignore_location_errors') == 'true'

        self.logger.info(
            'Transferring components from {0} to {1}'.format(
                source_location, target_location
            )
        )
        user_id = event['source']['user']['id']
        self.transfer_components(
            entities,
            source_location,
            target_location,
            user_id=user_id,
            ignore_component_not_in_location=ignore_component_not_in_location,
            ignore_location_errors=ignore_location_errors,
        )
        return {'success': True, 'message': 'Transferring components...'}

    def interface(self, session, entities, event):
        '''Return interface.'''
        values = event['data'].get('values', {})

        if not values:
            locations = [
                location
                for location in session.query('select name, label from Location').all()
                if location.accessor
            ]
            # Sort by priority.
            locations = sorted(locations, key=lambda location: location.priority)

            # Remove built in locations
            locations = [
                location
                for location in locations
                if location['name'] not in self.excluded_locations
            ]
            self.logger.info(locations)

            locations_options = [
                {
                    'label': location['label'] or location['name'],
                    'value': location['id'],
                }
                for location in locations
            ]
            return [
                {'value': 'Transfer components between locations', 'type': 'label'},
                {
                    'label': 'Source location',
                    'type': 'enumerator',
                    'name': 'from_location',
                    'value': locations_options[0]['value'],
                    'data': locations_options,
                },
                {
                    'label': 'Target location',
                    'type': 'enumerator',
                    'name': 'to_location',
                    'value': locations_options[1]['value'],
                    'data': locations_options,
                },
                {'value': '---', 'type': 'label'},
                {
                    'label': 'Ignore missing',
                    'type': 'enumerator',
                    'name': 'ignore_component_not_in_location',
                    'value': 'false',
                    'data': [
                        {'label': 'Yes', 'value': 'true'},
                        {'label': 'No', 'value': 'false'},
                    ],
                },
                {
                    'label': 'Ignore errors',
                    'type': 'enumerator',
                    'name': 'ignore_location_errors',
                    'value': 'false',
                    'data': [
                        {'label': 'Yes', 'value': 'true'},
                        {'label': 'No', 'value': 'false'},
                    ],
                },
            ]


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = TransferComponentsAction(session)
    action_handler.register()


def main(arguments=None):
    '''Set up logging and register action.'''
    if arguments is None:
        arguments = []

    parser = argparse.ArgumentParser()
    # Allow setting of logging level from arguments.
    loggingLevels = {}
    for level in (
        logging.NOTSET,
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ):
        loggingLevels[logging.getLevelName(level).lower()] = level

    parser.add_argument(
        '-v',
        '--verbosity',
        help='Set the logging output verbosity.',
        choices=list(loggingLevels.keys()),
        default='info',
    )
    namespace = parser.parse_args(arguments)

    # Set up basic logging
    logging.basicConfig(level=loggingLevels[namespace.verbosity])

    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)

    # Wait for events
    logging.info('Registered actions and listening for events. Use Ctrl-C to abort.')
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
