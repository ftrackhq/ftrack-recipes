'''

Copyright (c) 2014-2020 ftrack

'''

import logging
import argparse
import sys
import json

import ftrack_api

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("com.ftrack.recipes.tools.manage_project_schemas")


class ManageProjectSchemas(object):
    def __init__(self):

        self.session = ftrack_api.Session(auto_connect_event_hub=True)

        self.filename = 'project_schemas.json'
        self.parser = self.args = None

        self.parse_arguments()

        # Cache up commonly used Ftrack entities
        logger.info('Loading object types from Ftrack...')
        self.object_types_by_id = {}
        for object_type in self.session.query('select id from ObjectType'):
            self.object_types_by_id[object_type['id']] = object_type

        logger.info('Loading statuses from Ftrack...')
        self.status_types_by_id = {}
        for status_type in self.session.query('select id from Status'):
            self.status_types_by_id[status_type['id']] = status_type

        logger.info('Loading types from Ftrack...')
        self.types_by_id = {}
        for t in self.session.query('select id from Type'):
            self.types_by_id[t['id']] = t

        self.result = dict(project_schemas=[], workflow_schemas=[], task_schemas=[])

        if self.args.type == "backup":
            self.save_schemas()
        elif self.args.type == "restore":
            self.load_schemas()

    def parse_arguments(self):
        """Parse arguments passed to us."""
        self.parser = argparse.ArgumentParser()

        self.parser.add_argument(
            'type',
            help=(
                'Backup all ftrack project schemas to a JSON'
                'file {0} in your current working directory.'.format(self.filename)
            ),
            choices=['backup', 'restore'],
        )

        self.parser.add_argument(
            '--dry_run', help='Do not commit data to Ftrack.', action='store_true'
        )

        self.parser.add_argument(
            '--filename',
            help='The alternative filename to use',
        )

        self.parser.add_argument(
            '--schema',
            help='Ignore all schemas except this, ID or name.',
        )

        self.parser.add_argument(
            '--destination',
            help='(Used with --schema) The name to use when restoring a single schema.',
        )

        self.args = self.parser.parse_args()

        if self.filename is None and self.args.schema:
            self.filename = 'project_schemas{}.json'.format(
                '_%s'.format(self.args.schema) if self.args.schema else ''
            )

    def get_add_workflow_schema(self, ft_workflow_schema):
        """Find workflow schema by ID, serialise and add if not there."""
        for workflow_schema in self.result['workflow_schemas']:
            if workflow_schema['id'] == ft_workflow_schema['id']:
                return workflow_schema['id']
        workflow_schema = {
            'id': ft_workflow_schema['id'],
            'name': ft_workflow_schema['name'],
            'statuses': [],
        }
        for ft_status in ft_workflow_schema['statuses']:
            s = {'name': ft_status['name']}
            for key in ['color', 'is_active', 'sort']:
                if key in ft_status:
                    s[key] = ft_status[key]
            workflow_schema['statuses'].append(s)
        self.result['workflow_schemas'].append(workflow_schema)
        return workflow_schema['id']

    def get_add_task_schema(self, ft_task_schema):
        """Find task schema by ID, serialise and add if not there."""
        for task_schema in self.result['task_schemas']:
            if task_schema['id'] == ft_task_schema['id']:
                return task_schema['id']
        task_schema = {
            'id': ft_task_schema['id'],
            'name': ft_task_schema['name'],
            'types': [],
        }
        for ft_type in sorted(ft_task_schema['types'], key=lambda i: i['sort']):
            _type = {
                'name': ft_type['name'],
            }
            for key in ['color', 'is_billable', 'sort']:
                if key in ft_type:
                    _type[key] = ft_type[key]
            task_schema['types'].append(_type)
        self.result['task_schemas'].append(task_schema)
        return task_schema['id']

    def save_object_types(self, ft_project_schema, project_schema):
        """Save object_types(Objects)."""
        logger.info((4 * ' ') + 'Backing up object_types(Objects)...')
        for ft_object_type in sorted(
            ft_project_schema['object_types'], key=lambda i: i['sort']
        ):
            logger.info(
                (8 * ' ')
                + 'Backing up object type {}...'.format(ft_object_type['name'])
            )
            object_type = {'name': ft_object_type['name']}
            for key in [
                'icon',
                'is_leaf',
                'is_schedulable',
                'is_statusable',
                'is_taskable',
                'is_time_reportable',
                'is_typeable',
                'sort',
            ]:
                if key in ft_object_type:
                    object_type[key] = ft_object_type[key]
            project_schema['object_types'].append(object_type)

    def save_object_type_schemas(self, ft_project_schema, project_schema):
        """Save object_type_schemas(Shots, Asset builds etc)."""
        logger.info(
            (4 * ' ') + 'Backing up object_type_schemas(Shots, Asset builds etc)...'
        )
        for ft_object_type_schema in ft_project_schema['object_type_schemas']:
            logger.info(
                (8 * ' ')
                + 'Backing up {} schema...'.format(
                    self.object_types_by_id[ft_object_type_schema['type_id']]['name']
                )
            )
            object_type_schema = {
                'type': self.object_types_by_id[ft_object_type_schema['type_id']][
                    'name'
                ],
                'statuses': [
                    self.status_types_by_id[x['status_id']]['name']
                    for x in sorted(
                        ft_object_type_schema['statuses'], key=lambda i: i['sort']
                    )
                ],
                'types': [
                    self.types_by_id[x['type_id']]['name']
                    for x in sorted(
                        ft_object_type_schema['types'], key=lambda i: i['sort']
                    )
                ],
            }
            project_schema['object_type_schemas'].append(object_type_schema)

    def save_task_templates(self, ft_project_schema, project_schema):
        """Save task_templates(Task templates)."""
        logger.info((4 * ' ') + 'Backing up task_templates(Task templates)...')
        for ft_task_template in ft_project_schema['task_templates']:
            logger.info(
                (8 * ' ')
                + 'Backing up task template {}...'.format(ft_task_template['name'])
            )
            task_template = {
                'name': ft_task_template['name'],
                'items': [
                    self.types_by_id[ft_item['task_type_id']]['name']
                    for ft_item in ft_task_template['items']
                ],
            }
            project_schema['task_templates'].append(task_template)

    def save_task_type_schema(self, ft_project_schema, project_schema):
        """Save task_type_schema (Tasks workflow, part of)."""
        logger.info(
            (4 * ' ') + 'Backing up task_type_schema (Tasks workflow, part of)...'
        )
        ft_task_type_schema = ft_project_schema['task_type_schema']
        project_schema['task_type_schema'] = self.get_add_task_schema(
            ft_task_type_schema
        )

    def save_task_workflow_schema(self, ft_project_schema, project_schema):
        """Save task_workflow_schema (Tasks workflow, part of)."""
        logger.info(
            (4 * ' ') + 'Backing up task_workflow_schema (Tasks workflow, part of)...'
        )
        ft_task_workflow_schema = ft_project_schema['task_workflow_schema']
        project_schema['task_workflow_schema'] = self.get_add_workflow_schema(
            ft_task_workflow_schema
        )

    def save_task_workflow_schema_overrides(self, ft_project_schema, project_schema):
        """Save task_workflow_schema_overrides (Tasks)."""
        logger.info((4 * ' ') + 'Backing up task_workflow_schema_overrides (Tasks)...')
        for ft_task_workflow_schema_override in ft_project_schema[
            'task_workflow_schema_overrides'
        ]:
            project_schema['task_workflow_schema_overrides'].append(
                {
                    'type': self.types_by_id[
                        ft_task_workflow_schema_override['type_id']
                    ]['name'],
                    'schema': self.get_add_workflow_schema(
                        ft_task_workflow_schema_override['workflow_schema']
                    ),
                }
            )

    def save_asset_version_workflow_schema(self, ft_project_schema, project_schema):
        """Save asset_version_workflow_schema(Versions)."""
        logger.info((4 * ' ') + 'Backing up asset_version_workflow_schema(Versions)...')
        ft_workflow_schema = ft_project_schema['asset_version_workflow_schema']
        project_schema['asset_version_workflow_schema'] = self.get_add_workflow_schema(
            ft_workflow_schema
        )

    def save_schemas(self):
        """Read workflow schemas from Ftrack and write to JSON at disk."""

        logger.info('Loading Workflow Schemas from Ftrack...')
        workflow_schemas_by_id = {}
        for workflow_schema in self.session.query('select id from WorkflowSchema'):
            workflow_schemas_by_id[workflow_schema['id']] = workflow_schema

        logger.info('Backing up Ftrack project schemas...')
        for ft_project_schema in self.session.query('select id from ProjectSchema'):
            if (
                self.args.schema
                and ft_project_schema['id'] != self.args.schema
                and ft_project_schema['name'] != self.args.schema
            ):
                continue
            logger.info('Backing up {}...'.format(ft_project_schema['name']))
            project_schema = {
                'name': ft_project_schema['name'],
                'object_types': [],
                'object_type_schemas': [],
                'task_templates': [],
                'task_type_schema': None,
                'task_workflow_schema': None,
                'task_workflow_schema_overrides': [],
                'asset_version_workflow_schema': [],
            }

            # Collect and serialize schema definitions
            for (key, fn) in list(
                {
                    'object_types': self.save_object_types,
                    'object_type_schemas': self.save_object_type_schemas,
                    'task_templates': self.save_task_templates,
                    'task_type_schema': self.save_task_type_schema,
                    'task_workflow_schema': self.save_task_workflow_schema,
                    'task_workflow_schema_overrides': self.save_task_workflow_schema_overrides,
                    'save_asset_version_workflow_schema': self.save_asset_version_workflow_schema,
                }.items()
            ):
                if key in ft_project_schema:
                    fn(ft_project_schema, project_schema)

            self.result['project_schemas'].append(project_schema)

        if len(self.result['project_schemas']) == 0:
            if self.args.schema:
                logger.warning(
                    'No schema with name/id "{}" were found!'.format(self.args.schema)
                )
            else:
                logger.warning('No schemas were found!')

        # Nothing written to disk yet, save it unless it is a dry run.
        if not self.args.dry_run:
            logger.info('Writing {}...'.format(self.args.filename))
            json.dump(self.result, open(self.args.filename, 'w'))
        else:
            logger.warning(
                'Dry run, not writing JSON {} to {}.'.format(
                    json.dumps(self.result, indent=3), self.filename
                )
            )

    def get_object_type(self, name):
        """Get Ftrack object type by name from pre-cached entries."""
        for ft_object_type in list(self.object_types_by_id.values()):
            if ft_object_type['name'].lower() == name.lower():
                return ft_object_type
        raise Exception(
            'An unknown object type {} were encountered during restore!'.format(name)
        )

    def get_status(self, name):
        """Get Ftrack status type by name from pre-cached entries."""
        for ft_status in list(self.status_types_by_id.values()):
            if ft_status['name'].lower() == name.lower():
                return ft_status
        raise Exception(
            'An unknown status {} were encountered while during restore!'.format(name)
        )

    def get_type(self, name):
        """Get Ftrack type by name from pre-cached entries."""
        for ft_type in list(self.types_by_id.values()):
            if ft_type['name'].lower() == name.lower():
                return ft_type
        raise Exception(
            'An unknown type {} were encountered while during restore!'.format(name)
        )

    def get_workflow_schema(self, prev_id):
        """Get workflow schema JSON from result."""
        for workflow_schema in self.result.get('workflow_schemas'):
            if workflow_schema['id'] == prev_id:
                return workflow_schema['entity']
        raise Exception(
            'The backup JSON is corrupt - cannot find a workflow schema having previous ID: {}...'.format(
                prev_id
            )
        )

    def get_task_schema(self, prev_id):
        """Get task schema JSON from result."""
        for task_schema in self.result.get('task_schemas'):
            if task_schema['id'] == prev_id:
                return task_schema['entity']
        raise Exception(
            'The backup JSON is corrupt - cannot find a task schema having previous ID: {}...'.format(
                prev_id
            )
        )

    def load_schemas(self):
        """Load workflow schemas from JSON on disk and update Ftrack."""

        self.result = json.load(open(self.args.filename, 'r'))

        logger.info('Creating workflow schemas...')
        ft_workflow_schemas = []
        for workflow_schema in self.result.get('workflow_schemas'):
            ft_workflow_schema = self.session.create(
                'WorkflowSchema', {'name': workflow_schema['name']}
            )
            workflow_schema['entity'] = ft_workflow_schema
            for status in workflow_schema['statuses']:
                self.session.create(
                    'WorkflowSchemaStatus',
                    {
                        'workflow_schema_id': ft_workflow_schema['id'],
                        'status_id': self.get_status(status['name'])['id'],
                    },
                )
            ft_workflow_schemas.append(ft_workflow_schema)

        logger.info('Creating task type schemas...')
        ft_task_type_schemas = []
        for task_schema in self.result.get('task_schemas'):
            ft_task_schema = self.session.create(
                'TaskTypeSchema', {'name': task_schema['name']}
            )
            task_schema['entity'] = ft_task_schema
            for _type in task_schema['types']:
                self.session.create(
                    'TaskTypeSchemaType',
                    {
                        'task_type_schema_id': ft_task_schema['id'],
                        'type_id': self.get_type(_type['name'])['id'],
                    },
                )
            ft_task_type_schemas.append(ft_task_schema)

        schema_found = False
        for project_schema in self.result['project_schemas']:
            if self.args.schema and project_schema['name'] != self.args.schema:
                continue
            schema_found = True
            new_name = (
                self.args.destination
                if self.args.schema is not None and self.args.destination is not None
                else project_schema['name']
            )
            ft_project_schema = self.session.create(
                'ProjectSchema',
                {
                    'name': new_name,
                    'task_workflow_schema_id': self.get_workflow_schema(
                        project_schema['task_workflow_schema']
                    )['id'],
                    'task_type_schema_id': self.get_task_schema(
                        project_schema['task_type_schema']
                    )['id'],
                    'asset_version_workflow_schema_id': self.get_workflow_schema(
                        project_schema['asset_version_workflow_schema']
                    )['id'],
                },
            )
            logger.info(
                (0 * ' ')
                + 'Created project schema {0}({1})...'.format(
                    new_name, project_schema['name']
                )
            )

            # Deserialize and store definitions for schema
            # Note that milestone and task already gets created with the schema
            logger.info((4 * ' ') + 'Restoring object_types(Objects)...')
            for object_type in project_schema['object_types']:
                if object_type['name'].lower() == 'task':
                    continue
                ft_object_type = self.get_object_type(object_type['name'])
                if object_type['name'].lower() != 'milestone':
                    project_schema_object_type = {
                        'project_schema_id': ft_project_schema['id'],
                        'object_type_id': self.get_object_type(object_type['name'])[
                            'id'
                        ],
                    }
                    for key in [
                        'icon',
                        'is_leaf',
                        'is_schedulable',
                        'is_statusable',
                        'is_taskable',
                        'is_time_reportable',
                        'is_typeable',
                        'sort',
                    ]:
                        if key in object_type:
                            project_schema_object_type[key] = object_type[key]
                    self.session.create(
                        'ProjectSchemaObjectType', project_schema_object_type
                    )
                    logger.info(
                        (8 * ' ')
                        + 'Created schema for object type {}, restoring schema for type...'.format(
                            object_type['name']
                        )
                    )
                else:
                    logger.info(
                        (8 * ' ')
                        + 'Restoring schema for type {}...'.format(object_type['name'])
                    )

                # Find the schema that corresponds to type
                for object_type_schema in project_schema['object_type_schemas']:
                    if object_type_schema['type'] != object_type['name']:
                        continue

                    # Create the schema
                    ft_object_type_schema = self.session.create(
                        'Schema',
                        {
                            'project_schema_id': ft_project_schema['id'],
                            'object_type_id': ft_object_type['id'],
                        },
                    )

                    logger.info(
                        (12 * ' ')
                        + 'Created schema for {0}, mapping statuses: {1} and types: {2}...'.format(
                            ft_object_type['name'],
                            object_type_schema['statuses'],
                            object_type_schema['types'],
                        )
                    )

                    # Restore its types
                    for type_name in object_type_schema['types']:
                        self.session.create(
                            'SchemaType',
                            {
                                'schema_id': ft_object_type_schema['id'],
                                'type_id': self.get_type(type_name)['id'],
                            },
                        )
                        logger.info((16 * ' ') + '+ Type: {}'.format(type_name))

                    # And statuses
                    for status_name in object_type_schema['statuses']:
                        self.session.create(
                            'SchemaStatus',
                            {
                                'schema_id': ft_object_type_schema['id'],
                                'status_id': self.get_status(status_name)['id'],
                            },
                        )
                        logger.info((16 * ' ') + '+ Status: {}'.format(status_name))

            # Restore overrides
            logger.info(
                (4 * ' ')
                + 'Restoring task_workflow_schema_overrides(Task workflow, part of)...'
            )
            for task_workflow_schema_override in project_schema[
                'task_workflow_schema_overrides'
            ]:
                ft_task_type = self.get_type(task_workflow_schema_override['type'])
                self.session.create(
                    'ProjectSchemaOverride',
                    {
                        'project_schema_id': ft_project_schema['id'],
                        'type_id': ft_task_type['id'],
                        'workflow_schema_id': self.get_workflow_schema(
                            task_workflow_schema_override['schema']
                        )['id'],
                    },
                )
                logger.info(
                    (8 * ' ')
                    + 'Created override for type {0}...'.format(ft_task_type['name'])
                )

            # Restore task templates and their types
            logger.info((4 * ' ') + 'Restoring task_templates(Task templates)...')
            for task_template in project_schema['task_templates']:
                ft_task_template = self.session.create(
                    'TaskTemplate',
                    {
                        'project_schema_id': ft_project_schema['id'],
                        'name': task_template['name'],
                    },
                )
                logger.info(
                    (8 * ' ')
                    + 'Created task template {0}, adding types: {1}...'.format(
                        ft_task_template['name'], task_template['items']
                    )
                )

                for task_type_name in task_template['items']:
                    self.session.create(
                        'TaskTemplateItem',
                        {
                            'template_id': ft_task_template['id'],
                            'task_type_id': self.get_type(task_type_name)['id'],
                        },
                    )
                    logger.info((12 * ' ') + '+ Task type: {}'.format(task_type_name))

        if not schema_found:
            if self.args.schema:
                logger.warning(
                    'No schema with name/id "{}" were found!'.format(self.args.schema)
                )
            else:
                logger.warning('No schemas were found/JSON empty!')

        # No changes has been made yet, commit to Ftrack unless dry run
        if not self.args.dry_run:
            logger.info('Committing Project Schemas to Ftrack...')
            try:
                self.session.commit()
            except Exception as error:
                logger.error(error, exc_info=True)
        else:
            logger.warning(
                'Dry run, NOT committing Project Schemas to Ftrack based on JSON {}...'.format(
                    json.dumps(self.result, indent=3)
                )
            )


if __name__ == '__main__':

    ManageProjectSchemas()
