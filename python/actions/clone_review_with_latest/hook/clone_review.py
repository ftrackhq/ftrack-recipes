#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2024 ftrack

import logging
import ftrack_api
import datetime
from ftrack_action_handler.action import BaseAction


class CloneReview(BaseAction):
    """Clone review class."""

    label = "Clone review with Latest versions"
    identifier = "com.ftrack.recipes.clone_review"
    description = "Clone review and update with latest versions available."

    def validate_selection(self, entities):
        """Return True if the selection is valid.

        Utility method to check *entities* validity.

        """
        if not entities:
            return False

        if len(entities) > 1:
            # works on one at time only.
            return False

        entity_type, entity_id = entities[0]
        if entity_type == "ReviewSession":
            return True

        return False

    def discover(self, session, entities, event):
        """Return True if the action can be discovered.

        Check if the current selection can discover this action.

        """
        return self.validate_selection(entities)

    def launch(self, session, entities, event):
        """Return result of running action."""

        entity_type, entity_id = entities[0]
        review_session = session.get(entity_type, entity_id)
        new_review_objects = []
        objects = review_session["review_session_objects"]
        for object in objects:
            latest_version = session.query(
                f'AssetVersion where asset_id is {object["asset_version"]["asset_id"]} and is_latest_version is True'
            ).one()
            new_session_object = session.create(
                "ReviewSessionObject", {
                    "asset_version": latest_version,
                    "version": f"Version {latest_version['version']}",
                    "name": latest_version["task"]["name"],
                    "version_id": latest_version["id"],
                    "description": object["description"],
                    "statuses": object["statuses"]
                }
            )
            new_review_objects.append(new_session_object)

        review_name = datetime.datetime.now().strftime("%d/%m/%Y")
        new_list = session.create(
            "ReviewSession",
            {
                "name": f"clone of {review_session['name']} @ {review_name}",
                "project_id": review_session["project_id"],
                "review_session_invitees": review_session["review_session_invitees"],
                "review_session_objects": new_review_objects,
                "settings": review_session["settings"],
                "description": review_session["description"]
            },
        )

        session.commit()

        return {
            "success": True,
            "message": f"Successfully generated review with name : {review_name}.",
        }


def register(api_object, **kw):
    """Register hook with provided *api_object*."""

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(api_object, ftrack_api.session.Session):
        return

    action = CloneReview(api_object)
    action.register()


if __name__ == "__main__":
    # To be run as standalone code.
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session(auto_connect_event_hub=True)
    register(session)

    # Wait for events
    logging.info("Registered actions and listening for events. Use Ctrl-C to abort.")
    session.event_hub.wait()
