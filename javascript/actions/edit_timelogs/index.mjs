// :copyright: Copyright (c) 2023 ftrack

import { Session } from "@ftrack/api";
const FTRACK_SERVER_URL = "";
const FTRACK_API_USER = "";
const FTRACK_API_KEY = "";

class TimelogEditAction {
  static label = "Timelogs";
  static identifier = "show.edit.timelogs";
  static description = "Show and edit timelogs";

  // Constructor to initialize the TimelogEditAction with a session
  constructor(session) {
    this.session = session;
  }

  // Method to register the action with the event hub
  register() {
    // Subscribe to the action discover topic - responsible for showing the action button
    this.session.eventHub.subscribe(
      `topic=ftrack.action.discover`,
      this.discover.bind(this),
    );

    // Subscribe to the action launch topic - responsible for showing the action form
    this.session.eventHub.subscribe(
      `topic=ftrack.action.launch`,
      this.launch.bind(this),
    );
  }

  // Method to handle the discovery of actions, when the Action should be available
  // This is where you would do any filtering, for different entity types, different users etc.
  // Note:
  // The example does not include any access restrictions, and is run with the permissions of the API user that runs the action, and available for every user.
  // It is therefore not recommended for production use before adding approperiate access controls.
  discover(event) {
    const data = event.data;
    const selection = data.selection || [];

    // Check if it's a single selection, and that it's an item
    if (selection.length !== 1 || selection[0].entityType !== "task") {
      return;
    }

    // Return action if selection is valid
    return {
      items: [
        {
          label: TimelogEditAction.label,
          description: TimelogEditAction.description,
          actionIdentifier: TimelogEditAction.identifier,
        },
      ],
    };
  }

  // Method to handle the launch of the action - what happens when you press the button?
  async launch(event) {
    try {
      const { data } = event;
      // The return value of the form is returned as data.values, so if there's a data.values the form has been submitted.
      if (data?.values) {
        await this.processFormData(data.values);
        return { success: true, message: "Time logs updated successfully" };
      }
      // If there was no form data, we create the form.
      // Extract the entity ID from the selection
      const entityId = data.selection[0]?.entityId;
      if (!entityId) {
        throw new Error("Entity ID not found");
      }

      // Query for timelogs associated with the entity
      const query = await this.session.query(
        `select id, comment, context_id, duration, name, start, user.first_name, user.last_name from Timelog where context_id is ${entityId}`,
        { decodeDatesAsIso: true },
      );
      // Handle cases where no timelogs are found
      if (!query.data.length) {
        return {
          success: true,
          message: "No time logs available on this task",
        };
      }

      // Format the timelog data into the form data
      const items = query.data.flatMap((data, index) =>
        this.formatTimelogItem(data, index),
      );
      // Return the form items
      return { items };
    } catch (error) {
      console.error("Error in launch:", error);
      return { success: false, message: `An error occurred: ${error.message}` };
    }
  }

  // Format the timelog data into the form data
  formatTimelogItem(data, index) {
    return [
      {
        value: `## Timelog number ${index} - ${data.user.first_name} ${data.user.last_name}##`,
        type: "label",
      },
      {
        label: "Comment",
        type: "text",
        value: data.comment,
        name: `${data.id}`,
      },
      {
        label: "Duration",
        type: "number",
        name: `${data.id}`,
        value: data.duration,
      },
      {
        label: "Delete",
        name: `${data.id}`,
        value: false,
        type: "boolean",
      },
    ];
  }

  // Method to process the values submitted from the form
  async processFormData(values) {
    // Identify timelogs marked for deletion, filtering objects where the last array item (Delete) is true.
    const deletions = Object.entries(values)
      .filter(([_, valueArray]) => valueArray[valueArray.length - 1] === true)
      .map(([key]) => key);

    // Delete the identified timelogs
    for (const id of deletions) {
      await this.session.delete("Timelog", [id]);
    }

    // Update remaining timelogs, filtering away the timelogs deleted timelogs.
    const updatedValues = Object.fromEntries(
      Object.entries(values).filter(([key]) => !deletions.includes(key)),
    );

    for (const [key, [comment, duration]] of Object.entries(updatedValues)) {
      await this.session.update("Timelog", [key], { comment, duration });
    }
  }
}

// Function to register the action with a session
function register(session) {
  // Create and register the action
  const action = new TimelogEditAction(session);
  action.register();
}

// Create a new session with the specified API details
const session = new Session(
  FTRACK_SERVER_URL,
  FTRACK_API_USER,
  FTRACK_API_KEY,
  {
    autoConnectEventHub: true,
    strictApi: true,
  },
);

// Register the action with the session
register(session);
