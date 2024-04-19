#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2021 ftrack

import datetime
import logging

import ftrack_api
from ftrack_action_handler.action import BaseAction


class OffsetMilestonesTimeSelection(BaseAction):
    label = 'Milestone Mover'
    identifier = 'ftrack.recipes.offset-milestones-time-selection'
    description = 'offset milestones time selection'

    def launch(self, session, entities, event):
        
        offset_days = event['data']['values']['offset']
        
        if not offset_days:
            return False
    
        self.logger.info('Offsetting by {} days'.format(offset_days))

        for entity_type, entity_id in entities:
            milestone = session.get(entity_type, entity_id)
            end_date = milestone['end_date']
        
            if not end_date:
                continue

            milestone['end_date'] = milestone['end_date'].shift(days=int(offset_days))   

        try:
            session.commit()
        except Exception as error:
            return  {'success': False, 'message': str(error)}

        return  {
            'success': True, 
            'message': 'Selected ({}) Milestone/s have been offset by {} days.'.format(
                len(entities),
                offset_days
            )
        }

    def discover(self, session, entities, event):
        if not entities:
            return False

        for entity_type, entity_id in entities:
            if entity_type == 'TypedContext':
                return True

        return False

    def interface(self, session, entities, event):
        # If "value" is present, the ui has been raised and the value been set.
        # hence no need to re raise the ui.

        if 'values' in event['data']:
            return None

        return [{
            'label': 'day Offset',
            'type': 'number',
            'name': 'offset',
            'empty_text': 1
        }]


def register(session):
    if not isinstance(session, ftrack_api.session.Session):
        return
    
    action = OffsetMilestonesTimeSelection(session)
    action.register()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)
    logging.info(
        'Registered actions and listening for event. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()
