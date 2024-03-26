#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2018 ftrack

import logging
import ftrack_api
import datetime
from ftrack_action_handler.action import BaseAction


class CloneList(BaseAction):
    '''Cline list class.'''

    label = 'Clone List with Latest versions'
    identifier = 'com.ftrack.recipes.clone_list'
    description = 'Clone list and update with latest versions available'
    
    def validate_selection(self, entities):
        '''Return True if the selection is valid.

        Utility method to check *entities* validity.

        '''
        if not entities:
            return False

        if len(entities) > 1:
            # works on one at time only.
            return False
        
        entity_type, entity_id = entities[0]
        if entity_type == 'List':
            return True

        return False
    
    def discover(self, session, entities, event):
        '''Return True if the action can be discovered.

        Check if the current selection can discover this action.

        '''
        return self.validate_selection(entities)

    def launch(self, session, entities, event):
        '''Return result of running action.'''

        for entity_type, entity_id in entities:
            asset_list = session.get(entity_type, entity_id)
            latest_versions = set()
            versions = asset_list['items']
            for version in versions:
                latest_version  = session.query(f'AssetVersion where asset_id is {version["asset_id"]} and is_latest_version is True').one()
                latest_versions.add(latest_version)

            listname = datetime.datetime.now().strftime("%d/%m/%Y")
            new_list = session.create(
                'AssetVersionList', 
                {
                    'project_id':asset_list['project_id'], 
                    'name':listname, 
                    'category': asset_list['category'],
                    'items':list(latest_versions)
                }
            )
                
            print(new_list)
            session.commit()
            
        return {'success': True, 'message': f'Successfully generated list {listname}.'}
    
        
        
def register(api_object, **kw):
    '''Register hook with provided *api_object*.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(api_object, ftrack_api.session.Session):
        return

    action = CloneList(api_object)
    action.register()


if __name__ == '__main__':
    # To be run as standalone code.
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)

    # Wait for events
    logging.info('Registered actions and listening for events. Use Ctrl-C to abort.')
    session.event_hub.wait()
