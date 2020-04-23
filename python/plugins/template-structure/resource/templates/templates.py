# :coding: utf-8
# :copyright: Copyright (c) 2014-2020 ftrack


import os
from lucidity import Template

separator = os.path.sep

project_reference = Template('project_reference', '{project.name}')
version_reference = Template('version_reference', separator.join([
    'publish',
    '{asset.name}'
    'version_{asset.version}'
]))


shot_template = Template(
    'shot_template', separator.join([
        '{@project_reference}',
        'sequences',
        '{sequence.name}_{shot.name}',
        '{task.type}',
        '{task.name}',
        '{@version_reference}'
    ]),
    template_resolver=dict([
        (project_reference.name, project_reference),
        (version_reference.name, version_reference)
    ])
)

asset_template = Template(
    'asset_template', separator.join([
        '{@project_reference}',
        'assets',
        '{assetbuild.type}',
        '{assetbuild.name}',
        '{task.type}',
        '{task.name}',
        '{@version_reference}'
    ]),
    template_resolver=dict([
        (project_reference.name, project_reference),
        (version_reference.name, version_reference)
    ])
)


def register():
    '''Register templates.'''

    return [
        project_reference,
        version_reference,
        shot_template,
        asset_template
    ]
