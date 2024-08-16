# :coding: utf-8
# :copyright: Copyright (c) 2024 Backlight

import logging
import argparse
import itertools
import time
from uuid import UUID

import ftrack_api
import ftrack_api.attribute

logging.basicConfig()

# Setting `auto_populate` to False to not fetch more data than necessary in
# queries. Since we (likely) will be dealing with large structures of data, and
# we won't be copying *all* attributes, a way to keep the number of requests to
# the server/database down is to turn off auto-population and manually fetch the
# data that we want to duplicate.
session = ftrack_api.Session(auto_populate=False)


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'source_entity_id',
        help=('ID of source entity (root) to duplicate.')
    )
    parser.add_argument(
        'destination_entity_id',
        help=(
            'ID of destination entity where to parent the duplicate '
            'structure under.'
        )
    )

    return parser.parse_args()

def validate_args(args):
    try:
        UUID(args.source_entity_id)
        UUID(args.destination_entity_id)
        return True
    except Exception:
        return False

class DuplicateStructure(object):
    def __init__(self):
        self.logger = logging.getLogger('com.ftrack.recipes.tools.duplicate_structure')
        self.logger.setLevel(logging.INFO)

        self._dry_run = False
        if self._dry_run:
            self.logger.info(
                'Dry run mode enabled, nothing will be persisted to server.'
            )
    
    def process(self, source_entity_id, destination_entity_id):
        self._pre_actions()

        self._source_entity_id = source_entity_id
        self._destination_entity_id = destination_entity_id
        self._ignore_data_keys = [
            'project_id', 'ancestors', 'descendants', 'lists',
            'incoming_links', 'outgoing_links', 'status_changes',
            'parent_id', 'children', 'assets', 'timelogs', 'scopes',
            '_link', 'managers', 'appointments', 'allocations'
        ]
        self._ignore_data_keys_by_type = {
            'Task': ['split_parts'] + self._ignore_data_keys
        }
        self._entities_lookup = self._create_entity_lookup()

        self._run()
        self._post_actions()

    def _create_entity_lookup(self):
        self.logger.debug('Creating entity lookup dictionary...')
        entities_lookup = {}
        self.entities_to_copy = session.query(
            'select name, object_type.name, project.children, children, parent_id '
            f'from TypedContext where ancestors any (id={self._source_entity_id}) '
            f'or id is "{self._source_entity_id}"'
        ).all()
        for entity in self.entities_to_copy:
            entities_lookup[entity['id']] = entity
        self.logger.debug(
            f'Created entity lookup dictionary with {len(entities_lookup)} entries.'
        )
        return entities_lookup
    
    def _print_entity(self, entity):
        # For printing Task attributes while debugging
        for attribute in entity.attributes:
            if (
                attribute.name in self._ignore_data_keys['Task']
                or isinstance(attribute, ftrack_api.attribute.ReferenceAttribute)
            ):
                continue
            print("{: >20} {: >20}".format(*[attribute.name, str(entity[attribute.name])]))
    
    def _build_hierarchy_representation(self, entities, parent_id, level):
        self.logger.debug('Building hierarchy...')
        def iterate(entities, parent_id, level):
            def process_entity(entity, parent_id, level):
                level = level + 1
                entity_dict = {
                    'parent_id': parent_id,
                    'name': entity['name'],
                    'object_type': entity['object_type']['name'],
                    'metadata': {
                        'original_id': entity['id']
                    },
                    'level': level # primarily for debugging purposes
                }
                if len(entity['children']) > 0:
                    entity_dict['children'] = iterate(
                        entity['children'],
                        parent_id,
                        level
                    )
                return entity_dict
            return map(process_entity, entities, itertools.repeat(parent_id), itertools.repeat(level))
        return iterate(entities, parent_id, level)
    
    def _record_operations(self, entities, root, created_entities_ids):
        self.logger.debug('Recording operations...')
        for entity in entities:
            new_entity = session.create(entity['object_type'], {
                'parent_id': root,
                'name': entity['name'],
                'metadata': entity['metadata']
            })
            created_entities_ids.append(new_entity['id'])
            if 'children' in entity:
                self._record_operations(entity['children'], new_entity['id'], created_entities_ids)
        return created_entities_ids

    def _run(self):
        self.logger.debug('Running...')
        source_entity = self._entities_lookup[self._source_entity_id]
        self._created_entities_ids = []

        # Create a dict recursively of all TypedContext entities to duplicate
        # starting with the root at `_source_entity_id`
        hierarchy = self._build_hierarchy_representation([
            {
                'id': self._source_entity_id,
                'name': source_entity['name'] + str(time.time()),
                'object_type': source_entity['object_type'],
                'children': source_entity['children']
            }
        ], self._source_entity_id, 0)
        
        self._created_entities_ids = \
            self._record_operations(list(hierarchy), self._destination_entity_id, [])
        
        self._commit_operations()

    def _populate_entities(self):
        # TODO: move this to a job
        # TODO: improve error handling
        self.logger.debug('Populating entities...')

        # Retrieve the created, not yet fully populated TypedContext entities.
        created_entities = session.query(
            'select object_type, metadata, custom_attributes from TypedContext '
            'where id in ("' +
            '","'.join(self._created_entities_ids) +
            '")'
        ).all()

        # Create a set holding the types of objects created (Task, Shot, etc.)
        # to avoid fetching and working with all object types/schemas.
        object_types_created = set()
        for entity in created_entities:
            object_types_created.add(entity['object_type']['name'])

        # Create a dict of all immutable attributes (to later exclude from
        # attributes to populate)
        immutable_attributes = {}
        for schema in session.schemas:
            if schema['id'] in object_types_created:
                immutable_attributes[schema['id']] = schema['immutable']
        
        # Create dict of all attributes that should be retrieved and populated.
        attributes_to_populate = {}
        for object_type in object_types_created:
            for attribute in session.types[object_type].attributes:
                if (
                    attribute.name in immutable_attributes[object_type]
                    or (
                        ( # Skip if it's an attribute on the ignore list
                            object_type in self._ignore_data_keys_by_type
                            and attribute.name in self._ignore_data_keys_by_type[object_type]
                        )
                        or attribute.name in self._ignore_data_keys
                    )
                    or isinstance(attribute, ftrack_api.attribute.ReferenceAttribute)
                ):
                    continue

                if object_type not in attributes_to_populate:
                    attributes_to_populate[object_type] = []

                attributes_to_populate[object_type].append(attribute)
        
        original_entities_lookup = {}

        # Retrieve the original entities populated with the attributes we want
        # to copy to the new entities.
        for object_type in object_types_created:
            attribute_list = ", ".join([attribute.name for attribute in attributes_to_populate[object_type]])

            original_entities = session.query(
                f'select {attribute_list},assignments.resource_id from TypedContext where id in '
                '("' + '","'.join(self._entities_lookup.keys()) + '")'
            ).all()
            for entity in original_entities:
                original_entities_lookup[entity['id']] = entity
        
        # Copy data from the original entities to the new entities.
        for created_entity in created_entities:
            if 'original_id' in created_entity['metadata']:
                original_id = created_entity['metadata']['original_id']
            else:
                original_id = None
            original_entity = original_entities_lookup[original_id]

            for attribute in attributes_to_populate[created_entity['object_type']['name']]:
                if attribute.name in ['id', 'name']: # make sure to skip the `id` attribute
                    continue
                if isinstance(attribute, ftrack_api.attribute.ScalarAttribute):
                    created_entity[attribute.name] = original_entity[attribute.name]
                elif isinstance(attribute, ftrack_api.attribute.KeyValueMappedCollectionAttribute):
                    for metadata in original_entity['metadata'].items():
                        created_entity['metadata'][metadata[0]] = metadata[1]
                    for custom_attribute in original_entity['custom_attributes'].items():
                        created_entity['custom_attributes'][custom_attribute[0]] = custom_attribute[1]
                elif isinstance(attribute, ftrack_api.attribute.CollectionAttribute):
                    if attribute.name == 'assignments':
                        for assignee in original_entity['assignments']:
                            session.create('Appointment', {
                                'type': 'assignment',
                                'context_id': created_entity['id'],
                                'resource_id': assignee['resource_id']
                            })

        self._commit_operations()

    def _commit_operations(self):
        if not self._dry_run:
            try:
                session.commit()
            except Exception as error:
                self.logger.info('Server error on commit:')
                self.logger.exception(error)
    
    def _pre_actions(self):
        # TODO: Check if same schema
        pass
    
    def _post_actions(self):
        # TODO: Optionally delete source entities

        self._populate_entities()


if __name__ == '__main__':
    args = parse_arguments()

    if not validate_args(args):
        print('Invalid UUIDs provided.')

    duplicate_structure = DuplicateStructure()
    duplicate_structure.process(args.source_entity_id, args.destination_entity_id)
