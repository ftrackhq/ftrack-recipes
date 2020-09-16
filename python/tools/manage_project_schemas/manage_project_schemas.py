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
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(
    "com.ftrack.recipes.tools.manage_project_schemas"
)

class ManageProjectSchemas(object):

    def __init__(self):

        self.session = ftrack_api.Session()

        self.filename = 'project_schemas.json'

        self.parse_arguments()

        self.result = dict(project_schemas=[], workflow_schemas=[], task_schemas=[])

        logger.info('Loading object types from Ftrack...')
        self.object_types_by_id = {}
        for object_type in self.session.query('select id from ObjectType'):
            # if self.args.verbose: self.dump(object_type)
            self.object_types_by_id[object_type['id']] = object_type

        logger.info('Loading statuses from Ftrack...')
        self.status_types_by_id = {}
        for status_type in self.session.query('select id from Status'):
            # if self.args.verbose: self.dump(status_type)
            self.status_types_by_id[status_type['id']] = status_type

        logger.info('Loading types from Ftrack...')
        self.types_by_id = {}
        for t in self.session.query('select id from Type'):
            # if self.args.verbose: self.dump(t)
            self.types_by_id[t['id']] = t

        if self.args.type == "backup":
            self.save_schemas()
        elif self.args.type == "restore":
            self.load_schemas()

    def dump(self, o, indent=0):
        for key in sorted(o.keys()):
            logger.info(((indent * 4 * 3) * ' ') + '%s: %s' % (key, o[key]))
        logger.info('\n')
        sys.stdout.flush()


    def parse_arguments(self):

        self.parser = argparse.ArgumentParser()

        self.parser.add_argument(
            'type',
            help='Backup all ftrack project schemas to a JSON file {0} in your current working \
                directory.'.format(self.filename),
            choices=['backup', 'restore']
        )

        self.parser.add_argument(
            '-v', '--verbose',
            help='Output Ftrack data.',
            action='store_true'
        )

        self.parser.add_argument(
            '--dry_run',
            help='Do not commit data to Ftrack.',
            action='store_true'
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
            self.filename = 'project_schemas{}.json'.format('_%s' % (self.args.schema) if self.args.schema else '')

    def save_schemas(self):
        logger.info('Loading Workflow Schemas from Ftrack...')
        workflow_schemas_by_id = {}
        for workflow_schema in self.session.query('select id from WorkflowSchema'):
            if self.args.verbose: self.dump(workflow_schema)
            workflow_schemas_by_id[workflow_schema['id']] = workflow_schema

        def get_add_workflow_schema(ft_workflow_schema):
            for workflow_schema in self.result['workflow_schemas']:
                if workflow_schema['id'] == ft_workflow_schema['id']:
                    return workflow_schema['id']
            workflow_schema = {
                'id': ft_workflow_schema['id'],
                'name': ft_workflow_schema['name'],
                'statuses': []
            }
            for ft_status in ft_workflow_schema['statuses']:
                s = {
                    'name': ft_status['name']
                }
                for key in ['color', 'is_active', 'sort']:
                    if key in ft_status:
                        s[key] = ft_status[key]
                workflow_schema['statuses'].append(s)
            self.result['workflow_schemas'].append(workflow_schema)
            return workflow_schema['id']


        def get_add_task_schema(ft_task_schema):
            for task_schema in self.result['task_schemas']:
                if task_schema['id'] == ft_task_schema['id']:
                    return task_schema['id']
            task_schema = {
                'id': ft_task_schema['id'],
                'name': ft_task_schema['name'],
                'types': []
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


        logger.info('Backing up Ftrack project schemas...' + ('(verbose)' if self.args.verbose else ''))
        for ft_project_schema in self.session.query('select id from ProjectSchema'):
            if self.args.schema and \
                    ft_project_schema['id'] != self.args.schema and \
                    ft_project_schema['name'] != self.args.schema:
                continue
            if self.args.verbose: self.dump(ft_project_schema)
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
            def save_object_types():
                logger.info((4 * ' ') + 'Backing up object_types(Objects)...')
                for ft_object_type in sorted(ft_project_schema['object_types'], key=lambda i: i['sort']):
                    logger.info((8 * ' ') + 'Backing up object type {}...'.format(ft_object_type['name']))
                    if self.args.verbose: self.dump(ft_object_type, indent=2)
                    object_type = {
                        'name': ft_object_type['name']
                    }
                    for key in ['icon', 'is_leaf', 'is_schedulable', 'is_statusable', 'is_taskable',
                                'is_time_reportable', 'is_typeable', 'sort']:
                        if key in ft_object_type:
                            object_type[key] = ft_object_type[key]
                    project_schema['object_types'].append(object_type)

            def save_object_type_schemas():
                logger.info((4 * ' ') + 'Backing up object_type_schemas(Shots, Asset builds etc)...')
                for ft_object_type_schema in ft_project_schema['object_type_schemas']:
                    if self.args.verbose: self.dump(ft_object_type_schema, indent=2)
                    logger.info((8 * ' ') + 'Backing up {} schema...'.format(
                        self.object_types_by_id[ft_object_type_schema['type_id']]['name']))
                    object_type_schema = {
                        'type': self.object_types_by_id[ft_object_type_schema['type_id']]['name'],
                        'statuses': [
                            self.status_types_by_id[x['status_id']]['name'] for x in
                                     sorted(ft_object_type_schema['statuses'], key=lambda i: i['sort'])
                        ],
                        'types': [
                            self.types_by_id[x['type_id']]['name'] for x in
                                  sorted(ft_object_type_schema['types'], key=lambda i: i['sort'])
                        ],
                    }
                    project_schema['object_type_schemas'].append(object_type_schema)

            def save_task_templates():
                logger.info((4 * ' ') + 'Backing up task_templates(Task templates)...')
                for ft_task_template in ft_project_schema['task_templates']:
                    logger.info((8 * ' ') + 'Backing up task template {}...'.format(ft_task_template['name']))
                    task_template = {
                        'name': ft_task_template['name'],
                        'items': [
                            self.types_by_id[ft_item['task_type_id']]['name'] for ft_item in ft_task_template['items']
                        ]
                    }
                    project_schema['task_templates'].append(task_template)

            def save_task_type_schema():
                logger.info((4 * ' ') + 'Backing up task_type_schema (Tasks workflow, part of)...')
                ft_task_type_schema = ft_project_schema['task_type_schema']
                if self.args.verbose: self.dump(ft_task_type_schema, indent=2)
                project_schema['task_type_schema'] = get_add_task_schema(ft_task_type_schema)

            def save_task_workflow_schema():
                logger.info((4 * ' ') + 'Backing up task_workflow_schema (Tasks workflow, part of)...')
                ft_task_workflow_schema = ft_project_schema['task_workflow_schema']
                if self.args.verbose: self.dump(ft_task_workflow_schema, indent=2)
                project_schema['task_workflow_schema'] = get_add_workflow_schema(ft_task_workflow_schema)

            def save_task_workflow_schema_overrides():
                logger.info((4 * ' ') + 'Backing up task_workflow_schema_overrides (Tasks)...')
                for ft_task_workflow_schema_override in ft_project_schema['task_workflow_schema_overrides']:
                    if self.args.verbose: self.dump(ft_task_workflow_schema_override, indent=2)
                    project_schema['task_workflow_schema_overrides'].append({
                        'type': self.types_by_id[ft_task_workflow_schema_override['type_id']]['name'],
                        'schema': get_add_workflow_schema(ft_task_workflow_schema_override['workflow_schema'])
                    })

            def save_asset_version_workflow_schema():
                logger.info((4 * ' ') + 'Backing up asset_version_workflow_schema(Versions)...')
                ft_workflow_schema = ft_project_schema['asset_version_workflow_schema']
                if self.args.verbose: self.dump(ft_workflow_schema, indent=1)
                project_schema['asset_version_workflow_schema'] = get_add_workflow_schema(ft_workflow_schema)

            for (key, f) in {
                'object_types':save_object_types,
                'object_type_schemas':save_object_type_schemas,
                'task_templates':save_task_templates,
                'task_type_schema':save_task_type_schema,
                'task_workflow_schema':save_task_workflow_schema,
                'task_workflow_schema_overrides':save_task_workflow_schema_overrides,
                'save_asset_version_workflow_schema':save_asset_version_workflow_schema
            }.items():
                if key in ft_project_schema:
                    f()

            self.result['project_schemas'].append(project_schema)

        if self.args.verbose:
            logger.info('\n')
            logger.info('Backup JSON: {}'.format(json.dumps(self.result, indent=3)))

        if not self.args.dry_run:
            logger.info('Writing {}...'.format(self.args.filename))
            json.dump(self.result, open(self.args.filename, 'w'))
        else:
            logger.warning('Dry run, not writing JSON to {}.'.format(self.filename))

    def load_schemas(self):

        def get_object_type(name):
            for ft_object_type in self.object_types_by_id.values():
                if ft_object_type['name'].lower() == name.lower():
                    return ft_object_type
            raise Exception('An unknown object type {} were encountered during restore!'.format(name))


        def get_status(name):
            for ft_status in self.status_types_by_id.values():
                if ft_status['name'].lower() == name.lower():
                    return ft_status
            raise Exception('An unknown status {} were encountered while during restore!'.format(name))


        def get_type(name):
            for ft_type in self.types_by_id.values():
                if ft_type['name'].lower() == name.lower():
                    return ft_type
            raise Exception('An unknown type {} were encountered while during restore!'.format(name))


        result = json.load(open(self.args.filename, 'r'))

        if self.args.verbose:
            logger.info('\n')
            logger.info('Restore JSON: {}'.format(json.dumps(result, indent=3)))

        logger.info('Creating workflow schemas...')
        ft_workflow_schemas = []
        for workflow_schema in result.get('workflow_schemas'):
            ft_workflow_schema = self.session.create('WorkflowSchema', {
                'name': workflow_schema['name']
            })
            workflow_schema['entity'] = ft_workflow_schema
            if self.args.verbose: self.dump(ft_workflow_schema, indent=1)
            for status in workflow_schema['statuses']:
                ft_wfss = self.session.create('WorkflowSchemaStatus', {
                    'workflow_schema_id': ft_workflow_schema['id'],
                    'status_id': get_status(status['name'])['id']
                })
                if self.args.verbose: self.dump(ft_wfss, indent=1)
            ft_workflow_schemas.append(ft_workflow_schema)

        logger.info('Creating task type schemas...')
        ft_task_type_schemas = []
        for task_schema in result.get('task_schemas'):
            ft_task_schema = self.session.create('TaskTypeSchema', {
                'name': task_schema['name']
            })
            if self.args.verbose: self.dump(ft_task_schema, indent=1)
            task_schema['entity'] = ft_task_schema
            for _type in task_schema['types']:
                ft_ttst = self.session.create('TaskTypeSchemaType', {
                    'task_type_schema_id': ft_task_schema['id'],
                    'type_id': get_type(_type['name'])['id']
                })
                if self.args.verbose: self.dump(ft_ttst, indent=1)
            ft_task_type_schemas.append(ft_task_schema)


        def get_workflow_schema(prev_id):
            for workflow_schema in result.get('workflow_schemas'):
                if workflow_schema['id'] == prev_id:
                    return workflow_schema['entity']
            raise Exception(
                'The backup JSON is corrupt - cannot find a workflow schema having previous ID: {}...'.format(
                    prev_id
                ))


        def get_task_schema(prev_id):
            for task_schema in result.get('task_schemas'):
                if task_schema['id'] == prev_id:
                    return task_schema['entity']
            raise Exception(
                'The backup JSON is corrupt - cannot find a task schema having previous ID: {}...'.format(
                    prev_id
                ))


        for project_schema in result['project_schemas']:
            if self.args.schema:
                if project_schema['name'] != self.args.schema:
                    continue
            new_name = self.args.destination if self.args.schema is not None and \
                    self.args.destination is not None else project_schema['name']
            ft_project_schema = self.session.create('ProjectSchema', {
                'name': new_name,
                'task_workflow_schema_id': get_workflow_schema(project_schema['task_workflow_schema'])['id'],
                'task_type_schema_id': get_task_schema(project_schema['task_type_schema'])['id'],
                'asset_version_workflow_schema_id':
                    get_workflow_schema(project_schema['asset_version_workflow_schema'])['id']
            })
            logger.info((0 * ' ') + 'Created project schema {0}({1})...'.format(new_name, project_schema['name']))
            if self.args.verbose: self.dump(ft_project_schema, indent=1)

            # Deserialize and store definitions for schema
            logger.info((4 * ' ') + 'Restoring object_types(Objects)...')
            for object_type in project_schema['object_types']:
                if object_type['name'].lower() == 'task':
                    continue
                ft_object_type = get_object_type(object_type['name'])
                if object_type['name'].lower() != 'milestone':
                    project_schema_object_type = {
                        'project_schema_id': ft_project_schema['id'],
                        'object_type_id': get_object_type(object_type['name'])['id']
                    }
                    for key in ['icon', 'is_leaf', 'is_schedulable', 'is_statusable', 'is_taskable',
                                'is_time_reportable', 'is_typeable', 'sort']:
                        if key in object_type:
                            project_schema_object_type[key] = object_type[key]
                    ft_psot = self.session.create('ProjectSchemaObjectType', project_schema_object_type)
                    logger.info((8 * ' ') + 'Created schema for object type {}, restoring schema for type...'.format(
                        object_type['name']))
                    if self.args.verbose: self.dump(ft_psot, indent=1)
                else:
                    logger.info((8 * ' ') + 'Restoring schema for type {}...'.format(
                        object_type['name']))

                for object_type_schema in project_schema['object_type_schemas']:
                    if object_type_schema['type'] != object_type['name']:
                        continue

                    ft_object_type_schema = self.session.create('Schema', {
                        'project_schema_id': ft_project_schema['id'],
                        'object_type_id': ft_object_type['id']
                    })

                    logger.info((12 * ' ') + 'Created schema for {0}, mapping statuses: {1} and types: {2}...'.format(
                        ft_object_type['name'], object_type_schema['statuses'], object_type_schema['types']))
                    if self.args.verbose: self.dump(ft_object_type_schema, indent=2)

                    for type_name in object_type_schema['types']:
                        ft_st = self.session.create('SchemaType', {
                            'schema_id': ft_object_type_schema['id'],
                            'type_id': get_type(type_name)['id']
                        })
                        logger.info((16 * ' ') + '+ Type: {}'.format(type_name))
                        if self.args.verbose: self.dump(ft_st, indent=3)

                    for status_name in object_type_schema['statuses']:
                        ft_ss = self.session.create('SchemaStatus', {
                            'schema_id': ft_object_type_schema['id'],
                            'status_id': get_status(status_name)['id']
                        })
                        logger.info((16 * ' ') + '+ Status: {}'.format(status_name))
                        if self.args.verbose: self.dump(ft_ss, indent=3)

            logger.info((4 * ' ') + 'Restoring task_workflow_schema_overrides(Task workflow, part of)...')
            for task_workflow_schema_override in project_schema['task_workflow_schema_overrides']:
                ft_task_type = get_type(task_workflow_schema_override['type'])
                ft_psso = self.session.create('ProjectSchemaOverride', {
                    'project_schema_id': ft_project_schema['id'],
                    'type_id': ft_task_type['id'],
                    'workflow_schema_id': get_workflow_schema(task_workflow_schema_override['schema'])['id'],
                })
                if self.args.verbose: self.dump(ft_psso, indent=2)
                logger.info((8 * ' ') + 'Created override for type {0}...'.format(ft_task_type['name']))

            logger.info((4 * ' ') + 'Restoring task_templates(Task templates)...')
            for task_template in project_schema['task_templates']:
                ft_task_template = self.session.create('TaskTemplate', {
                    'project_schema_id': ft_project_schema['id'],
                    'name': task_template['name']
                })
                logger.info((8 * ' ') + 'Created task template {0}, adding types: {1}...'.format(
                    ft_task_template['name'],
                    task_template['items'])
                )

                if self.args.verbose: self.dump(ft_task_template, indent=2)
                for task_type_name in task_template['items']:
                    ft_ss = self.session.create('TaskTemplateItem', {
                        'template_id': ft_task_template['id'],
                        'task_type_id': get_type(task_type_name)['id']
                    })
                    logger.info((12 * ' ') + '+ Task type: {}'.format(task_type_name))
                    if self.args.verbose: self.dump(ft_ss, indent=2)

        if not self.args.dry_run:
            logger.info('Committing Project Schemas to Ftrack...')
            try:
                self.session.commit()
            except Exception as error:
                self.logger.error(error, exc_info=True)
        else:
            logger.info('[WARNING] NOT committing Project Schemas to Ftrack (dry run)...')



if __name__ == '__main__':

    ManageProjectSchemas()
