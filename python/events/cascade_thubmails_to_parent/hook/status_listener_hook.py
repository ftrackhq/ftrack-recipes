# :coding: utf-8
# :copyright: Copyright (c) 2014-2022 ftrack


import logging
import ftrack_api
import functools


logger = logging.getLogger('com.ftrack.recipes.cascade_thumbnails_to_parent')


def cascade_thumbnail(session, event):
    '''Handle *event* and cascade thumbnail changes on versions.'''

    for entity in event['data'].get('entities', []):
        asset_version = None
        entity_id = None

        # Handle new or updated versions.
        if (
            entity.get('entityType') == 'assetversion' and
            entity.get('action') in ('add', 'update') and
            entity.get('keys', None) and
            'thumbid' in entity.get('keys', [])
        ):
            entity_id = entity['entityId']

        # Handle encoded versions.
        if (
            entity.get('action') in ('encoded',) and
            entity.get('entityType') == 'assetversion'
        ):
            entity_id = entity['entityId']
        

        # If entity was found, try to get it.
        if entity_id:

            # Get asset version and preload data for performance and to avoid
            # caching issues.
            asset_version = session.query(
                'select thumbnail_id, asset, asset.parent, task '
                'from AssetVersion where id is {0}'.format(
                    entity['entityId']
                )
            ).first()
            logger.info(f'using asset version : {asset_version["version"]}')

        if asset_version and asset_version['thumbnail_id']:
            # Update parent and related task if the thumbnail is set.
            parent = asset_version['asset']['parent']
            task = asset_version['task']
            parent['thumbnail_id'] = asset_version['thumbnail_id']
            logger.info(f'updating parent : {parent["name"]}')


            if task:
                logger.info(f'updating task: {task["name"]}')
                task['thumbnail_id'] = asset_version['thumbnail_id']

    session.commit()


def register(session, **kw):
    '''Register event listener.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an incompatible API
    # and return without doing anything.
    if not isinstance(session, ftrack_api.Session):
        return

    # Register the event handler
    handle_event = functools.partial(cascade_thumbnail, session)
    session.event_hub.subscribe('topic=ftrack.update', handle_event)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Remember, in version version 2.0 of the ftrack-python-api the default
    # behavior will change from True to False.
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)
    logging.info('Registered actions and listening for events. Use Ctrl-C to abort.')
    session.event_hub.wait()

