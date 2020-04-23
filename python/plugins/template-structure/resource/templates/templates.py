# :coding: utf-8
# :copyright: Copyright (c) 2014-2020 ftrack


import os
from lucidity import Template

separator = os.path.sep

# define project template reference
project_reference = Template('project_reference', '{project.name}')

# define version template reference
version_reference = Template('version_reference', separator.join([
    'publish',
    '{asset.name}'
    'version_{asset.version}'
]))

# define generic task template reference
task_reference = Template('shot_task_reference', separator.join([
    '{task.type}',
    '{task.name}',
    '{@version_reference}'
    ]),
    template_resolver=dict([
        (version_reference.name, version_reference)
    ])
    )

# define shot template reference
shot_template = Template(
    'shot_template', separator.join([
        '{@project_reference}',
        'sequences',
        '{sequence.name}_{shot.name}',
        '{@task_reference}'

    ]),
    template_resolver=dict([
        (project_reference.name, project_reference),
        (task_reference.name, task_reference)
    ])
)

# define asset template reference
asset_template = Template(
    'asset_template', separator.join([
        '{@project_reference}',
        'assets',
        '{assetbuild.type}',
        '{assetbuild.name}',
        '{@task_reference}'
    ]),
    template_resolver=dict([
        (project_reference.name, project_reference),
        (task_reference.name, task_reference)
    ])
)


def register():
    '''Register templates.'''

    return [
        project_reference,
        version_reference,
        task_reference,
        shot_template,
        asset_template
    ]
