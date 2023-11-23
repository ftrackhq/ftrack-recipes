# Timelog Edit Action for ftrack API

This is an example action for viewing, editing and deleting timelogs for Tasks. The example does not include any access restrictions, and is run with the permissions of the API user that runs the action, and available for every user. It is therefore not recommended for production use before adding approperiate access controls.

## Features

- **Discover Time Logs**: Enables the discovery of time logs for a specific task.
- **Edit Time Logs**: Allows users to edit comments and duration of time logs.
- **Delete Time Logs**: Provides an option to delete time logs.

## Requirements

- ftrack API access.
- Node.js environment.

## Installation

1. Clone or download the repository containing the Timelog Edit Action.
2. Navigate to the root directory of the project.
3. Run `npm install` to install necessary dependencies.

## Configuration

Set the following environment variables:

- `FTRACK_SERVER_URL`: URL of your ftrack server
- `FTRACK_API_USER`: Your ftrack API user
- `FTRACK_API_KEY`: Your ftrack API key

## Usage

1. Start the application using `node index.mjs`.
2. The action will automatically register with the ftrack event hub and will be available for use within the ftrack interface.

## Action Workflow

1. **Discovery**: The action is discoverable in the actions UI for task entities.
2. **Launch**: On launching the action, it checks if there are existing time logs for the selected task.
3. **Edit Form**: If time logs are present, a form is displayed to edit or delete the logs.
4. **Process Data**: On submitting the form, the action updates or deletes time logs as per the user's input.
