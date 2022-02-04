#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

"""
Demo ftrack actions to enable or disable selected users

This action will allow you to select multiple users and enable or disable them en
masse.
"""
import ftrack_api
from ftrack_action_handler.action import BaseAction


class EnableUsersAction(BaseAction):
    """
    Defines the action that enables users.
    """

    label = "Set Users' Active State"
    variant = "Enable Users"
    identifier = "ftrack.recipes.enable_users"
    description = "Any selected users will be enabled"

    # We set activate to True because we want to enable users.
    # True will be the final state of user's is_active attribute.
    activate = True

    def _get_users(self, entities):
        return self.session.query(
            f"User where is_active = {not self.activate} and (id = '"
            + "' or id = '".join([user[1] for user in entities])
            + "')"
        )

    def discover(self, session, entities, event):
        """
        Method that responds to the discovery message.

        Make sure that there are users selected and in the required state.
        """
        # We only need to fetch a single user, we don't care how big the selection
        # is. By doing this, we're optimizing for less data transfer and query time.
        user = self._get_users(entities).first()
        if user:
            return True

        return False

    def launch(self, session, entities, event):
        """
        Method that responds to messages to launch the action.

        This will change the active state of the selected users.
        """
        users = self._get_users(entities)
        user_count = len(users)
        if user_count > 0:
            for user in users:
                user["is_active"] = self.activate

            try:
                self.session.commit()
            except Exception as exc:
                return {"success": False, "message": str(exc)}

        return {"success": True, "message": self.get_success_message(user_count)}

    def get_success_message(self, user_count):
        """
        Given the activation/deactivation state of the object, return an
        appropriate message indicating the success of the operation.
        """
        if self.activate:
            action = "Enabled"
        else:
            action = "Disabled"

        if user_count != 1:
            return f"{action} {user_count} users."
        return f"{action} {user_count} user."


class DisableUsersAction(EnableUsersAction):
    """
    Defines the action that disables users.
    """

    label = "Set Users' Active State"
    variant = "Disable Users"
    identifier = "ftrack.recipes.disable_users"
    description = "Any selected users will be disabled"

    # We set activate to False because we want to disable users.
    # False will be the final state of user's is_active attribute.
    activate = False


def register(session):
    """Function required by connect to register the action."""
    if not isinstance(session, ftrack_api.Session):
        return

    action = EnableUsersAction(session)
    action.register()

    action = DisableUsersAction(session)
    action.register()
