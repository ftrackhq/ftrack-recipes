# :coding: utf-8
# :copyright: Copyright (c) 2014-2020 ftrack

import os
import lucidity


# define path separator
sep = os.path.sep

class TemplateCollection(dict):
    ''' Template collection class to simplify tempalte composition.
    
        # https://gitlab.com/4degrees/lucidity/-/issues/32

    '''

    def add(self, key, pattern, **lucidityKwargs):
        kwargs = {'template_resolver': self}
        kwargs.update(**lucidityKwargs)
        template = lucidity.Template(key, pattern, **kwargs)
        self.__setitem__(key, template)

    def __repr__(self):
        return '<TemplateCollection of {0} templates.>'.format(len(self))

    def __str__(self):
        return str(dict(self))


templates = TemplateCollection()

# template fragments
templates.add('project', '{project.name}')
templates.add('task', sep.join(['{task.type}', '{task.name}']))
templates.add('version', sep.join(['publish',  '{asset.name}', 'version_{asset.version}']))

# asset templates
templates.add('assets', sep.join(['{@project}', 'assets', '{assetbuild.name}']))
templates.add('assets_task', sep.join(['{@assets}', '{@task}']))

# shot template
templates.add('shots', sep.join(['{@project}', 'sequences', '{sequence.name}_{shot.name}']))
templates.add('shots_task', sep.join(['{@shots}', '{@task}']))

# versions template, these are used during the publishing.
templates.add('shots_task_version', sep.join(['{@shots_task}', '{@version}']))
templates.add('assets_task_version', sep.join(['{@assets_task}', '{@version}']))


def register():
    '''Register templates.'''

    return templates.values()
