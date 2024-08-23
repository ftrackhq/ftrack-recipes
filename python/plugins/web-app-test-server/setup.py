# :coding: utf-8
# :copyright: Copyright (c) 2024 Backlight

import logging
import os
import subprocess
import sys
import shutil

from setuptools import Command, setup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

__version__ = '1.0.0'
PLUGIN_NAME = f'web-app-test-server-{__version__}'

ROOT_PATH = os.path.dirname(
    os.path.realpath(__file__)
)

STATIC_PATH = os.path.join(
    ROOT_PATH, 'resource', 'static'
)

BUILD_PATH = os.path.join(
    ROOT_PATH, 'build', PLUGIN_NAME
)

DEPENDENCIES_PATH = os.path.join(BUILD_PATH, 'dependencies')


if os.path.exists(BUILD_PATH):
    shutil.rmtree(BUILD_PATH)

os.makedirs(BUILD_PATH)
os.makedirs(DEPENDENCIES_PATH)


class BuildPlugin(Command):
    ''' Build plugin '''
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        ''' Run the build step '''
        npm_exec = shutil.which('npm')

        if npm_exec is None:
            logger.error(
                'Could not find npm, exiting. Make sure it is installed and '
                'available on the PATH, then re-run this script.'
            )
            exit()
        
        os.chdir(STATIC_PATH)

        web_apps_folders = [
            folder.path for folder in os.scandir() if folder.is_dir()
        ]

        logger.info('Building web apps...')

        for folder in web_apps_folders:
            os.chdir(os.path.join(STATIC_PATH, folder))
            try:
                subprocess.check_call([npm_exec, 'install'])
                subprocess.check_call([npm_exec, 'run', 'build'])
            except Exception as e:
                logger.exception('subprocess call failed.')
        
        os.chdir(ROOT_PATH)

        logger.info('Installing Python dependencies...')

        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', '.', '--target', DEPENDENCIES_PATH]
            )
        except Exception as e:
            logger.exception('subprocess call failed.')

        logger.info('Creating plugin folder...')

        shutil.copytree(
            os.path.join(ROOT_PATH, 'hook'),
            os.path.join(BUILD_PATH, 'hook')
        )

        for folder in web_apps_folders:
            shutil.copytree(
                os.path.join(STATIC_PATH, folder, 'dist'),
                os.path.join(BUILD_PATH, 'resource', 'static', folder)
            )
        
        shutil.copy(
            os.path.join(ROOT_PATH, 'resource', 'app.py'),
            os.path.join(BUILD_PATH, 'resource', 'app.py')
        )

        logger.info('Successfully built plugin.')


setup(
    name='web-app-test-server',
    version=__version__,
    description='Web server plugin for ftrack Connect',
    author='Backlight',
    install_requires=[
        'Flask',
        'waitress'
    ],
    cmdclass={
        'build_plugin': BuildPlugin
    }
)