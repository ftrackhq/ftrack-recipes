"""
Demo ftrack action to mark jobs as failed

This action, enabled in any context, will mark running jobs as failed. A customizable
global variable defined how old a job needs to be to be failed. This acts as a grace
period for jobs that might be newly submitted.
"""
import arrow
import ftrack_api
from ftrack_action_handler.action import BaseAction

AGE_IN_MINUTES = 15


class MarkRunningJobsFailedAction(BaseAction):
    """
    Defines the base class for this action.
    """

    label = "Mark Running Jobs Failed"
    identifier = "ftrack.recipes.mark_running_jobs_failed"
    description = "Any jobs in the queue that are running should be marked failed."

    def discover(self, session, entities, event):
        """
        Method that responds to the discovery message.

        This will always return the action in any context so that it is globally
        available.
        """
        # Whatever the context, we want this action to be available.
        return {
            "items": [
                {
                    "label": self.label,
                    "description": self.description,
                    "actionIdentifier": self.identifier,
                }
            ]
        }

    def launch(self, session, entities, event):
        """
        Method that responds to messages to launch the action.

        This will load any running job outside the grace period and will
        mark them as failed in order to clean up the queue.
        """
        cutoff = (
            arrow.utcnow()
            .shift(minutes=AGE_IN_MINUTES * -1)
            .format("YYYY-MM-DD HH:mm:ss")
        )
        jobs = self.session.query(
            f'select status from Job where status is running and created_at < "{cutoff}"'
        ).all()

        if jobs:
            for job in jobs:
                job["status"] = "failed"

            try:
                self.session.commit()
            except Exception as exc:
                return {"success": False, "message": str(exc)}

            message = "Marked {0} {1} as failed!"
            job_count = len(jobs)
            if job_count > 1:
                message = message.format(job_count, "job")
            else:
                message = message.format(job_count, "jobs")
        else:
            message = "There were no long-running jobs."

        return {"success": True, "message": message}


def register(session):
    """Function required by connect to register the action."""
    if not isinstance(session, ftrack_api.Session):
        return

    action = MarkRunningJobsFailedAction(session)
    action.register()
