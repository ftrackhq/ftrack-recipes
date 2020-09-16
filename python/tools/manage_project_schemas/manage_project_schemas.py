'''

py2/py3k compatible

Created on Aug 19, 2010

@author: henrik_norin, Ftrack
'''

import traceback
import sys
import json

import ftrack_api


def dump(o, indent=0):
    for key in sorted(o.keys()):
        print(((indent * 4 * 3) * ' ') + '%s: %s' % (key, o[key]))
    print('\n')
    sys.stdout.flush()


if __name__ == '__main__':

    session = ftrack_api.Session()

    show_help = True
    backup = restore = False
    verbose = False
    commit = True
    the_schema = None
    restore_to = None
    filename = 'project_schemas.json'
    filename_overridden = False
    for arg in sys.argv:
        if arg.lower() == '--verbose':
            verbose = True
        elif arg.lower() in ['backup']:
            backup = True
            show_help = False
        elif arg.lower() in ['restore']:
            restore = True
            show_help = False
        elif arg.lower().startswith('--filename='):
            filename = arg.split('=')[-1]
            filename_overridden = True
        elif arg.lower().startswith('--schema='):
            the_schema = arg.split('=')[-1]
        elif arg.lower().startswith('--restore='):
            restore_to = arg.split('=')[-1]
        elif arg.lower() == '--dry_run':
            commit = False
    if not filename_overridden and the_schema:
        filename = 'project_schemas{}.json'.format('_%s' % (the_schema) if the_schema else '')

    if show_help:
        print('Backup and restore Ftrack Project and Workflow Schemas')
        print('')
        print('Usage:')
        print('   manage_project_schemas.py <options>')
        print('')
        print(
            '         backup          Backup all ftrack project schemas to a JSON file {0} in your current working \
            directory.'.format(
                filename)
            )
        print(
            '         restore         Restore project schemas from JSON file {0} in your current working directory \
             to ftrack.'.format(
                filename)
            )
        print('')
        print('         --filename=<..> The alternative filename to use.')
        print('         --schema=<..>   Ignore all schemas except this, ID or name.')
        print('         --restore=<..>  (Used with --schema) The name to use when restoring a single schema.')
        print('         --verbose       Print Ftrack data.')
        print('         -h|--help       Show help.')
        print('')
        sys.exit(0)

    result = dict(project_schemas=[], workflow_schemas=[], task_schemas=[])

    print('Loading object types from Ftrack...')
    object_types_by_id = {}
    for object_type in session.query('select id from ObjectType'):
        # if verbose: dump(object_type)
        object_types_by_id[object_type['id']] = object_type

    print('Loading statuses from Ftrack...')
    status_types_by_id = {}
    for status_type in session.query('select id from Status'):
        # if verbose: dump(status_type)
        status_types_by_id[status_type['id']] = status_type

    print('Loading types from Ftrack...')
    types_by_id = {}
    for t in session.query('select id from Type'):
        # if verbose: dump(t)
        types_by_id[t['id']] = t

    if backup:

        print('Loading Workflow Schemas from Ftrack...')
        workflow_schemas_by_id = {}
        for workflow_schema in session.query('select id from WorkflowSchema'):
            if verbose: dump(workflow_schema)
            workflow_schemas_by_id[workflow_schema['id']] = workflow_schema


        def get_add_workflow_schema(result, ft_workflow_schema):
            for workflow_schema in result['workflow_schemas']:
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
            result['workflow_schemas'].append(workflow_schema)
            return workflow_schema['id']


        def get_add_task_schema(result, ft_task_schema):
            for task_schema in result['task_schemas']:
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
            result['task_schemas'].append(task_schema)
            return task_schema['id']


        print('Backing up Ftrack project schemas...' + ('(verbose)' if verbose else ''))
        for ft_project_schema in session.query('select id from ProjectSchema'):
            if the_schema and ft_project_schema['id'] != the_schema and ft_project_schema['name'] != the_schema:
                continue
            if verbose: dump(ft_project_schema)
            print('Backing up {}...'.format(ft_project_schema['name']))
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
            result['project_schemas'].append(project_schema)
            if 'object_types' in ft_project_schema:
                print((4 * ' ') + 'Backing up object_types(Objects)...')
                for ft_object_type in sorted(ft_project_schema['object_types'], key=lambda i: i['sort']):
                    print((8 * ' ') + 'Backing up object type {}...'.format(ft_object_type['name']))
                    if verbose: dump(ft_object_type, indent=2)
                    object_type = {
                        'name': ft_object_type['name']
                    }
                    for key in ['icon', 'is_leaf', 'is_schedulable', 'is_statusable', 'is_taskable',
                                'is_time_reportable', 'is_typeable', 'sort']:
                        if key in ft_object_type:
                            object_type[key] = ft_object_type[key]
                    project_schema['object_types'].append(object_type)
            if 'object_type_schemas' in ft_project_schema:
                print((4 * ' ') + 'Backing up object_type_schemas(Shots, Asset builds etc)...')
                for ft_object_type_schema in ft_project_schema['object_type_schemas']:
                    if verbose: dump(ft_object_type_schema, indent=2)
                    print((8 * ' ') + 'Backing up {} schema...'.format(
                        object_types_by_id[ft_object_type_schema['type_id']]['name']))
                    object_type_schema = {
                        'type': object_types_by_id[ft_object_type_schema['type_id']]['name'],
                        'statuses': [status_types_by_id[x['status_id']]['name'] for x in
                                     sorted(ft_object_type_schema['statuses'], key=lambda i: i['sort'])],
                        'types': [types_by_id[x['type_id']]['name'] for x in
                                  sorted(ft_object_type_schema['types'], key=lambda i: i['sort'])],
                    }
                    project_schema['object_type_schemas'].append(object_type_schema)
            if 'task_templates' in ft_project_schema:
                print((4 * ' ') + 'Backing up task_templates(Task templates)...')
                for ft_task_template in ft_project_schema['task_templates']:
                    print((8 * ' ') + 'Backing up task template {}...'.format(ft_task_template['name']))
                    task_template = {
                        'name': ft_task_template['name'],
                        'items': [types_by_id[ft_item['task_type_id']]['name'] for ft_item in ft_task_template['items']]
                    }
                    project_schema['task_templates'].append(task_template)

            if 'task_type_schema' in ft_project_schema:
                print((4 * ' ') + 'Backing up task_type_schema (Tasks workflow, part of)...')
                ft_task_type_schema = ft_project_schema['task_type_schema']
                if verbose: dump(ft_task_type_schema, indent=2)
                project_schema['task_type_schema'] = get_add_task_schema(result, ft_task_type_schema)

            if 'task_workflow_schema' in ft_project_schema:
                print((4 * ' ') + 'Backing up task_workflow_schema (Tasks workflow, part of)...')
                ft_task_workflow_schema = ft_project_schema['task_workflow_schema']
                if verbose: dump(task_workflow_schema, indent=2)
                project_schema['task_workflow_schema'] = get_add_workflow_schema(result, ft_task_workflow_schema)

            if 'task_workflow_schema_overrides' in ft_project_schema:
                print((4 * ' ') + 'Backing up task_workflow_schema_overrides (Tasks)...')
                for ft_task_workflow_schema_override in ft_project_schema['task_workflow_schema_overrides']:
                    if verbose: dump(ft_task_workflow_schema_override, indent=2)
                    project_schema['task_workflow_schema_overrides'].append({
                        'type': types_by_id[ft_task_workflow_schema_override['type_id']]['name'],
                        'schema': get_add_workflow_schema(result, ft_task_workflow_schema_override['workflow_schema'])
                    })

            if 'asset_version_workflow_schema' in ft_project_schema:
                print((4 * ' ') + 'Backing up asset_version_workflow_schema(Versions)...')
                ft_workflow_schema = ft_project_schema['asset_version_workflow_schema']
                if verbose: dump(ft_workflow_schema, indent=1)
                project_schema['asset_version_workflow_schema'] = get_add_workflow_schema(result, ft_workflow_schema)

        if verbose or True:
            print('\n')
            print('Backup JSON: {}'.format(json.dumps(result, indent=3)))

        if commit:
            print('Writing {}...'.format(filename))
            json.dump(result, open(filename, 'w'))

    if restore:

        def get_object_type(name):
            for ft_object_type in object_types_by_id.values():
                if ft_object_type['name'].lower() == name.lower():
                    return ft_object_type
            raise Exception('An unknown object type {} were encountered during restore!'.format(name))


        def get_status(name):
            for ft_status in status_types_by_id.values():
                if ft_status['name'].lower() == name.lower():
                    return ft_status
            raise Exception('An unknown status {} were encountered while during restore!'.format(name))


        def get_type(name):
            for ft_type in types_by_id.values():
                if ft_type['name'].lower() == name.lower():
                    return ft_type
            raise Exception('An unknown type {} were encountered while during restore!'.format(name))


        result = json.load(open(filename, 'r'))

        if verbose or True:
            print('\n')
            print('Restore JSON: {}'.format(json.dumps(result, indent=3)))

        print('Creating workflow schemas...')
        ft_workflow_schemas = []
        for workflow_schema in result.get('workflow_schemas'):
            ft_workflow_schema = session.create('WorkflowSchema', {
                'name': workflow_schema['name']
            })
            workflow_schema['entity'] = ft_workflow_schema
            if verbose: dump(ft_workflow_schema, indent=1)
            for status in workflow_schema['statuses']:
                ft_wfss = session.create('WorkflowSchemaStatus', {
                    'workflow_schema_id': ft_workflow_schema['id'],
                    'status_id': get_status(status['name'])['id']
                })
                if verbose: dump(ft_wfss, indent=1)
            ft_workflow_schemas.append(ft_workflow_schema)

        print('Creating task type schemas...')
        ft_task_type_schemas = []
        for task_schema in result.get('task_schemas'):
            ft_task_schema = session.create('TaskTypeSchema', {
                'name': task_schema['name']
            })
            if verbose: dump(ft_task_schema, indent=1)
            task_schema['entity'] = ft_task_schema
            for _type in task_schema['types']:
                ft_ttst = session.create('TaskTypeSchemaType', {
                    'task_type_schema_id': ft_task_schema['id'],
                    'type_id': get_type(_type['name'])['id']
                })
                if verbose: dump(ft_ttst, indent=1)
            ft_task_type_schemas.append(ft_task_schema)


        def get_workflow_schema(prev_id):
            for workflow_schema in result.get('workflow_schemas'):
                if workflow_schema['id'] == prev_id:
                    return workflow_schema['entity']
            raise Exception(
                'The backup JSON is corrupt - cannot find a workflow schema having previous ID: {}...'.format(prev_id))


        def get_task_schema(prev_id):
            for task_schema in result.get('task_schemas'):
                if task_schema['id'] == prev_id:
                    return task_schema['entity']
            raise Exception(
                'The backup JSON is corrupt - cannot find a task schema having previous ID: {}...'.format(prev_id))


        for project_schema in result['project_schemas']:
            if the_schema:
                if project_schema['name'] != the_schema:
                    continue
            new_name = restore_to if the_schema is not None and restore_to is not None else project_schema['name']
            ft_project_schema = session.create('ProjectSchema', {
                'name': new_name,
                'task_workflow_schema_id': get_workflow_schema(project_schema['task_workflow_schema'])['id'],
                'task_type_schema_id': get_task_schema(project_schema['task_type_schema'])['id'],
                'asset_version_workflow_schema_id':
                    get_workflow_schema(project_schema['asset_version_workflow_schema'])['id']
            })
            print((0 * ' ') + 'Created project schema {0}({1})...'.format(new_name, project_schema['name']))
            if verbose: dump(ft_project_schema, indent=1)

            print((4 * ' ') + 'Restoring object_types(Objects)...')
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
                    ft_psot = session.create('ProjectSchemaObjectType', project_schema_object_type)
                    print((8 * ' ') + 'Created schema for object type {}, restoring schema for type...'.format(
                        object_type['name']))
                    if verbose: dump(ft_psot, indent=1)
                else:
                    print((8 * ' ') + 'Restoring schema for type {}...'.format(
                        object_type['name']))

                # print((4 * ' ') + 'Restoring object_type_schemas(Shots, Asset builds, Milestone etc)...')
                for object_type_schema in project_schema['object_type_schemas']:
                    if object_type_schema['type'] != object_type['name']:
                        continue

                    ft_object_type_schema = session.create('Schema', {
                        'project_schema_id': ft_project_schema['id'],
                        'object_type_id': ft_object_type['id']
                    })

                    print((12 * ' ') + 'Created schema for {0}, mapping statuses: {1} and types: {2}...'.format(
                        ft_object_type['name'], object_type_schema['statuses'], object_type_schema['types']))
                    if verbose: dump(ft_object_type_schema, indent=2)

                    for type_name in object_type_schema['types']:
                        ft_st = session.create('SchemaType', {
                            'schema_id': ft_object_type_schema['id'],
                            'type_id': get_type(type_name)['id']
                        })
                        print((16 * ' ') + '+ Type: {}'.format(type_name))
                        if verbose: dump(ft_st, indent=3)

                    for status_name in object_type_schema['statuses']:
                        ft_ss = session.create('SchemaStatus', {
                            'schema_id': ft_object_type_schema['id'],
                            'status_id': get_status(status_name)['id']
                        })
                        print((16 * ' ') + '+ Status: {}'.format(status_name))
                        if verbose: dump(ft_ss, indent=3)

            print((4 * ' ') + 'Restoring task_workflow_schema_overrides(Task workflow, part of)...')
            for task_workflow_schema_override in project_schema['task_workflow_schema_overrides']:
                ft_task_type = get_type(task_workflow_schema_override['type'])
                ft_psso = session.create('ProjectSchemaOverride', {
                    'project_schema_id': ft_project_schema['id'],
                    'type_id': ft_task_type['id'],
                    'workflow_schema_id': get_workflow_schema(task_workflow_schema_override['schema'])['id'],
                })
                if verbose: dump(ft_psso, indent=2)
                print((8 * ' ') + 'Created override for type {0}...'.format(ft_task_type['name']))

            print((4 * ' ') + 'Restoring task_templates(Task templates)...')
            for task_template in project_schema['task_templates']:
                ft_task_template = session.create('TaskTemplate', {
                    'project_schema_id': ft_project_schema['id'],
                    'name': task_template['name']
                })
                print((8 * ' ') + 'Created task template {0}, adding types: {1}...'.format(ft_task_template['name'],
                                                                                           task_template['items']))

                if verbose: dump(ft_task_template, indent=2)
                for task_type_name in task_template['items']:
                    ft_ss = session.create('TaskTemplateItem', {
                        'template_id': ft_task_template['id'],
                        'task_type_id': get_type(task_type_name)['id']
                    })
                    print((12 * ' ') + '+ Task type: {}'.format(task_type_name))
                    if verbose: dump(ft_ss, indent=2)

        if commit:
            print('Committing Project Schemas to Ftrack...')
            try:
                session.commit()
            except:
                print('[WARNING] {}'.format(traceback.format_exc()))
        else:
            print('[WARNING] NOT committing Project Schemas to Ftrack (dry run)...')
