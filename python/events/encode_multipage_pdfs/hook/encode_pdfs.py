# :coding: utf-8
# :copyright: Copyright (c) 2020 ftrack

import functools
import json
import logging
import os

import ftrack_api

logger = logging.getLogger('com.ftrack.recipes.web-playable-pdfs')


def callback(event, session):
    '''Supersedes the default Connect hook

    The hook callback accepts an *event*.

    event['data'] should contain:

        * versionId - The id of the version to make reviewable.
        * path - The path to the file to use as the component.

    Will raise :py:exc:`ValueError` if the provided path is not an accessible
    file.

    '''
    path = event['data']['path']
    file_type = os.path.splitext(path)[-1]
    if file_type != '.pdf':
        logger.info('File extension is not ".pdf". File path was "{0}"').format(path)
        return

    if not os.path.isfile(path):
        raise ValueError('"{0}" is not a valid filepath.'.format(path))

    # Clear the cache, just in case
    session.reset()
    versionId = event['data']['versionId']
    version = session.get('AssetVersion', versionId)

    # Keep the uploaded file available for client reviews
    job = version.encode_media(path, keep_original=True)
    source_component_id = json.loads(job['data'])['source_component_id']
    source_component = session.get('Component', source_component_id)
    source_component['metadata']['ftr_meta'] = '{"format": "pdf"}'
    source_component['name'] = 'ftrackreview-pdf'
    session.commit()
    # Prevent the default hook from running and making another ftrackreview-image
    event.stop()
    logger.info('make-reviewable hook completed.')


def subscribe(session):
    '''Subscribe to events.'''
    topic = 'ftrack.connect.publish.make-web-playable'
    logger.info('Subscribing to event topic: {0!r}'.format(topic))
    session.event_hub.subscribe(
        'topic="{0}" and source.user.username="{1}"'.format(topic, session.api_user),
        functools.partial(callback, session=session),
        priority=50,  # The default is 100, so we'll be the one bundled with Connect
    )


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''
    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.Session):
        logger.debug(
            'Not subscribing plugin as passed argument {0!r} is not an '
            'ftrack_api.Session instance.'.format(session)
        )
        return

    subscribe(session)
    logger.debug('Plugin registered')
